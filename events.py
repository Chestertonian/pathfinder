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

from typing import Optional

from event_types import Event
from events_mapper import row_to_event

from db import get_connection



# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

def emit_event(
    conn,
    *,
    event_type: str,
    message: str,

    sender_id: Optional[int] = None,
    recipient_character_id: Optional[int] = None,

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
    if event_type == "room" and sender_id is None:
        raise ValueError("Room events must have sender_id")
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
                recipient_character_id,
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
                use_border,
                created_at
            FROM broadcast_messages
            WHERE id > %s
            ORDER BY id ASC
            """,
            (last_id,),
        )

        rows = cur.fetchall()

    visible = []

    for row in rows:
        event = row_to_event(row)

        if should_deliver(character, event):
            visible.append(event)

    return visible


def should_deliver(character, event: Event) -> bool:
    from events_mapper import row_to_event
    if event.event_type == "room" and event.sender_id is None:
        raise ValueError("[WARN] Room event missing sender_id.")
    if event.event_type == "combat" and event.sender_id is None and event.location_id is None:
        raise ValueError("Combat events must have at least a location_id")

    # -------------------------------------------------------
    # Global events (always visible)
    # -------------------------------------------------------
    if event.event_type == "global":
        return True

    # -------------------------------------------------------
    # Room events
    # -------------------------------------------------------
    if event.event_type in ("room", "combat"):
        if event.event_type == "room" and event.sender_id == character.id:
            return False
        if event.location_id != character.location_id:
            return False
        # ADDED: skip events from before the player entered this room
        if (
            character.room_entered_at
            and event.created_at
            and event.created_at < character.room_entered_at
        ):
            return False
        return True

    # -------------------------------------------------------
    # Tell events (private messaging)
    # -------------------------------------------------------
    if event.event_type == "tell":
        # ONLY deliver if you're the recipient
        return event.recipient_character_id == character.id

    # -------------------------------------------------------
    # Channel chat
    # -------------------------------------------------------
    if event.event_type == "channel":
        return True

    # -------------------------------------------------------
    # System messages
    # -------------------------------------------------------    
    if event.event_type == "system":
        return event.sender_id == character.id

    
    return False