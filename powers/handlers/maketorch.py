"""
powers/handlers/maketorch.py — Make Torch

Usage:
    maketorch

Creates a torch and places it directly into the player's inventory.
No input materials required. Usable anywhere.

Future: potential SP scaling or crafting skill interaction.
"""

from events import emit_event
from output import to_ansi


def execute(character, target, args, conn, session) -> None:

    # No target required for this power
    if args and len(args) > 0:
        # ignore extra args rather than erroring
        pass

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
            (
                8,
                "character",
                character.id,
                False,
                1,
            ),
        )

        item_instance_id = cur.fetchone()[0]

    emit_event(
        conn,
        event_type="system_message",
        sender_id=character.id,
        recipient_character_id=character.id,
        message=to_ansi(
            "[yellow]You shape raw materials into a torch.[/yellow]"
        ),
    )

    session.send(
        to_ansi(
            "[yellow]You create a torch and place it in your inventory.[/yellow]\n"
        )
    )

    return item_instance_id