"""
commands/flourish.py — Flourish

Usage:
    flourish

A rogue displays weapon skill and flair. Purely cosmetic / roleplay.
No mechanical effect.
"""

from events import emit_event
from output import to_ansi


def execute(character, target, args, conn, session) -> None:

    # Optional variation hooks could be added later (weapon type, stance, etc.) Support unarmed...

    room_message = to_ansi(
        f"[yellow]{character.name} spins their weapon in a fluid, practiced flourish.[/yellow]"
    )

    self_message = to_ansi(
        "[yellow]You perform a clean, controlled flourish with practiced ease.[/yellow]\n"
    )

    emit_event(
        conn,
        event_type="room",
        sender_id=character.id,
        location_id=character.location_id,
        message=room_message,
    )

    session.send(self_message)

    return None