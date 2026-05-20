def render(msg, lookup_character):
    if msg.event_type == "chat":
        sender = lookup_character(msg.character_id)
        return f"[yellow] {sender.name.capitalize()} <chat> {msg.message} [/yellow]"

    if msg.event_type == "tell":
        sender = lookup_character(msg.character_id)
        return f"[cyan]{msg.message}[/cyan]"

    if msg.event_type == "room":
        return msg.message

    if msg.event_type == "system":
        return f"*[red] {msg.message} [/red]*"

    return msg.message