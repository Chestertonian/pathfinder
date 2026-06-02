#
# render.py
#
# Converts structured events into display strings.
#

from models import Character
from commands.proclaim import render_proclaim, to_ansi


def render_event(conn, event):
    """
    Turns an event into a string for display.

    IMPORTANT:
    - NO filtering logic here
    - ONLY formatting
    """

    sender_id = getattr(event, "sender_id", None) or getattr(event, "character_id", None)

    sender_name = "Someone"

    if sender_id:
        sender = Character.get_by_id(conn, sender_id)
        if sender:
            sender_name = sender.name.capitalize()

    if event.event_type == "global":
        style = getattr(event, "style", "plain_centered")
        color = getattr(event, "color", "white")
        print(f"[render] style={style!r} color={color!r}")
        return render_proclaim(event.message, color, style)

    if event.event_type == "room":
        return event.message + "\n"

    if event.event_type == "tell":
        return to_ansi(f"[cyan](tell) {event.message}[/cyan]\n")

    if event.event_type == "channel":
        channel = (event.channel or "chat").capitalize()
        return to_ansi(f"[yellow]{sender_name} <{channel}> {event.message}[/yellow]\n")

    if event.event_type == "combat":
        return (f"{event.message}\n")

    return event.message + "\n"