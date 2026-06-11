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
    
    if event.event_type == "personal_message":
        return (to_ansi(event.message))

    if event.event_type == "channel":
        channel = (event.channel or "chat")
        color = event.color or "cyan"

        # Emotes are prefixed with [ChannelName] and have no speaker tag
        if event.message.startswith(f"<{channel}>"):
            return to_ansi(f"[{color}]{event.message}[/{color}]")

        # Normal speech
        return to_ansi(
            f"[{color}]{sender_name} <{channel}> {event.message}[/{color}]"
        )

    if event.event_type == "combat":
        return (f"{event.message}\n")
    
    if event.event_type == "guild":
        return to_ansi(f"[bright_yellow]{event.message}[/bright_yellow]")

    return event.message + "\n"