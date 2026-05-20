# events.py
#
# Central event system.
#
# Commands and game systems should not print directly to players.
# Instead, they emit structured events here.
#
# Flow:
#   command -> emit_event() -> DB row
#   poller  -> get_visible_events() -> render_event()
#
# This becomes the backbone for:
#   - room messages
#   - tells
#   - channels
#   - combat spam filtering
#   - system announcements
#

from dataclasses import dataclass
from typing import Optional

from db import get_connection


# ---------------------------------------------------------------------------
# Event object
# ---------------------------------------------------------------------------

@dataclass
class Event:
    id: int
    event_type: str

    sender_id: Optional[int]
    recipient_id: Optional[int]

    location_id: Optional[int]
    channel: Optional[str]

    message: str
    color: str
    use_border: bool


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

def emit_event(
    conn,
    *,
    event_type: str,
    message: str,

    sender_id: Optional[int] = None,
    recipient_id: Optional[int] = None,

    location_id: Optional[int] = None,
    channel: Optional[str] = None,

    color: str = "white",
    use_border: bool = False,
) -> None:
    """
    Create a new event row.

    event_type examples:
        room
        tell
        channel
        global
        system
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO broadcast_messages
            (
                event_type,
                character_id,
                recipient_character_id,
                location_id,
                channel,
                message,
                color,
                use_border
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_type,
                sender_id,
                recipient_id,
                location_id,
                channel,
                message,
                color,
                use_border,
            ),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

def get_visible_events(
    conn,
    *,
    last_id: int,
    character,
):
    """
    Return all events visible to this character.

    Visibility rules live HERE.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                event_type,
                character_id,
                recipient_character_id,
                location_id,
                channel,
                message,
                color,
                use_border
            FROM broadcast_messages
            WHERE id > %s
            ORDER BY id ASC
            """,
            (last_id,),
        )

        rows = cur.fetchall()

    visible = []

    for row in rows:
        event = Event(
            id=row[0],
            event_type=row[1],
            sender_id=row[2],
            recipient_id=row[3],
            location_id=row[4],
            channel=row[5],
            message=row[6],
            color=row[7],
            use_border=row[8],
        )

        if should_deliver(character, event):
            visible.append(event)

    return visible


def should_deliver(character, event: Event) -> bool:

    # -------------------------------------------------------
    # Global events (always visible)
    # -------------------------------------------------------
    if event.event_type == "global":
        return True

    # -------------------------------------------------------
    # Room events (NO SELF-ECHO, EVER)
    # -------------------------------------------------------
    if event.event_type == "room":
        return (
            event.location_id == character.location_id
            and event.sender_id != character.id
        )

    # -------------------------------------------------------
    # Tell events (private messaging)
    # -------------------------------------------------------
    if event.event_type == "tell":
        return (
            event.recipient_id == character.id
            or event.sender_id == character.id
        )

    # -------------------------------------------------------
    # Channel chat
    # -------------------------------------------------------
    if event.event_type == "channel":
        return True

    return False