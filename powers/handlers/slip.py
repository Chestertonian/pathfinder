"""
powers/handlers/slip.py — Slip

Usage:
    slip <player> <message>

Slips an anonymous note to a target player in the room.
The room sees nothing. The target receives the message anonymously.
Thief only. Target must be in the same room.

Future: skill check to reveal sender identity.
"""

from events import emit_event
from output import to_ansi


def execute(character, target, args, conn, session) -> None:

    if target is None:
        session.send("Slip a note to whom?\n")
        return

    if target["type"] != "player":
        session.send("You can only slip notes to other players.\n")
        return

    # args[0] is the target name, everything after is the message
    message = " ".join(args[1:]).strip()

    if not message:
        session.send("Usage: slip <name> <message>\n")
        return

    emit_event(
        conn,
        event_type="tell",
        sender_id=character.id,
        recipient_character_id=target["id"],
        message=to_ansi(
            f"[magenta]Someone slips you a folded note. "
            f"It reads: \"{message}\"[/magenta]"
        ),
    )

    session.send(
        to_ansi(
            f"[magenta]You slip a note to "
            f"{target['name'].capitalize()}.[/magenta]\n"
        )
    )