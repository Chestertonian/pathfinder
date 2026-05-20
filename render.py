#
# render.py
#
# Converts structured events into display strings.
#

from models import Character


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

    # ------------------------------------------------------------
    # GLOBAL
    # ------------------------------------------------------------

    if event.event_type == "global":
        return event.message

    # ------------------------------------------------------------
    # ROOM
    # ------------------------------------------------------------

    if event.event_type == "room":
        return event.message

    # ------------------------------------------------------------
    # TELL
    # ------------------------------------------------------------

    if event.event_type == "tell":
        return f"[cyan]{event.message}[/]"

    # ------------------------------------------------------------
    # CHANNEL
    # ------------------------------------------------------------

    if event.event_type == "channel":
        channel = (event.channel or "chat").upper()
        return f"[cyan]{sender_name} <{channel.lower()}> {event.message} [/cyan]"

    # ------------------------------------------------------------
    # DEFAULT
    # ------------------------------------------------------------

    return event.message