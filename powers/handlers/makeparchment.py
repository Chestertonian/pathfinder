"""
powers/handlers/makeparchment.py — Make Parchment

Usage:
    makeparchment

Creates a blank piece of parchment and places it in the player's inventory.
Can be written on using the scribe command.
"""

from events import emit_event
from output import to_ansi


def execute(character, target, args, conn, session) -> None:

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO item_instances (
                item_template_id,
                owner_type,
                owner_id,
                equipped,
                quantity
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (20, "character", character.id, False, 1),
        )
        item_instance_id = cur.fetchone()[0]

    session.send(
        to_ansi(
            "[yellow]You fold and press a sheet of parchment. It is ready to be scribed on.[/yellow]\n"
        )
    )

    emit_event(
        conn,
        event_type="room",
        sender_id=character.id,
        location_id=character.location_id,
        message=f"{character.name} folds and presses a sheet of parchment.",
    )

    return item_instance_id