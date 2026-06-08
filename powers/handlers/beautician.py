"""
powers/handlers/beautician.py — Beautician

Merchant power.

Usage:
    beautician <target> <description>

Allows a merchant to refine a character's public description
only while inside a Beautician location.
"""

from output import to_ansi
from events import emit_event

BEAUTICIANS = {248}


def execute(character, target, args, conn, session) -> None:

    # args expected: [target_name, ...description]
    if not args or len(args) < 2:
        session.send("Usage: beautician <character> <description>\n")
        return None

    location_id = getattr(character, "location_id", None)

    if location_id not in BEAUTICIANS:
        session.send("This power can only be used in a Beautician's shop.\n")
        return None

    target_name = args[0].lower()
    new_description = " ".join(args[1:]).strip()

    if not new_description:
        session.send("You must provide a description.\n")
        return None

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT id, name
            FROM characters
            WHERE lower(name) = %s
            """,
            (target_name,),
        )

        row = cur.fetchone()

        if not row:
            session.send("No such character is present.\n")
            return None

        target_id, real_name = row

        cur.execute(
            """
            UPDATE characters
            SET description = %s
            WHERE id = %s
            """,
            (new_description, target_id),
        )

    session.send(
        to_ansi(
            f"[yellow]You refine the appearance of {real_name.capitalize()}.[/yellow]\n"
        )
    )
    
    room_message = to_ansi(f"[cyan]With deft skill, {character.name} changes the appearance of {real_name.capitalize()}. [/cyan]")
    
    emit_event(
        conn,
        event_type="room",
        sender_id=character.id,
        location_id=character.location_id,
        message=room_message,
    )

    return None