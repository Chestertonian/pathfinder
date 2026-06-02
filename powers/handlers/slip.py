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
    session.send(f"DEBUG args: {args}\n")
    # target is guaranteed by dispatcher (target_required=TRUE)
    # but just in case:
    if target is None:
        session.send("Slip a note to whom?\n")
        return

    if target["type"] != "player":
        session.send("You can only slip notes to other players.\n")
        return

    # Everything after the target name is the message
    # We reconstruct it from the raw args via the target name
    # Actually we need the message — see note below
    if not hasattr(character, '_power_args') or not character._power_args:
        session.send("Slip what message?\n")
        return

    # Strip the target name from args to get the message
    message = character._power_raw_message
    if not message:
        session.send("Slip what message?\n")
        return

    # Deliver anonymously to target only
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

    # Confirm to sender, no room event
    session.send(
        to_ansi(
            f"[magenta]You slip a note to {target['name'].capitalize()}.[/magenta]\n"
        )
    )