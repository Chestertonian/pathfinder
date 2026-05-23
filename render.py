#
# render.py
#
# Converts structured events into display strings.
#

from models import Character
from commands.proclaim import render_proclaim



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
        use_border = getattr(event, "use_border", False)
        color = getattr(event, "color", "white")
        return render_proclaim(event.message, color, use_border)

    if event.event_type == "room":
        return event.message

    if event.event_type == "tell":
        return f"(tell) {event.message}"          # CHANGED: stripped [cyan] tags

    if event.event_type == "channel":
        channel = (event.channel or "chat").capitalize()
        return f"{sender_name} <{channel}> {event.message}"  # CHANGED: stripped tags

    return event.message