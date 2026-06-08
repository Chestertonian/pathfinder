"""
powers/handlers/hawkwares.py — Hawkwares

Usage:
    hawkwares <message>

Broadcasts a merchant announcement to the world.
"""

from events import emit_event
from output import to_ansi

WIDTH = 78  


def _center(text, width=WIDTH):
    text = str(text)
    pad = max(0, (width - len(text)) // 2)
    return " " * pad + text


def _wrap(message, width=WIDTH):
    words = message.split()
    lines = []
    current = ""

    for w in words:
        if len(current) + len(w) + 1 > width:
            lines.append(current)
            current = w
        else:
            current = (current + " " + w).strip()

    if current:
        lines.append(current)

    return lines


def execute(character, target, args, conn, session) -> None:

    message = " ".join(args).strip() if args else ""

    if not message:
        session.send("Usage: hawkwares <message>\n")
        return None

    header = f"{character.name} the Merchant Announces to the World"

    body_lines = _wrap(message)

    lines = []

    # top border (green)
    lines.append(to_ansi("[green]" + "-" * WIDTH + "[/green]"))

    # header (red)
    lines.append(to_ansi("[red]" + _center(f"--- {header} ---") + "[/red]"))

    # body (yellow)
    for line in body_lines:
        lines.append(to_ansi("[yellow]" + _center(line) + "[/yellow]"))

    # bottom border (green)
    lines.append(to_ansi("[green]" + "-" * WIDTH + "[/green]"))

    final_message = "\n".join(lines)

    emit_event(
        conn,
        event_type="hawk",
        sender_id=character.id,
        recipient_character_id=None,
        message=final_message,
    )

    session.send(
        to_ansi("[yellow]Your announcement echoes forth across the realm.[/yellow]\n")
    )

    return None