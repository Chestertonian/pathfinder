def should_deliver(msg, character):
    # Direct messages
    if msg.recipient_character_id == character.id:
        return True

    # Room-based events
    if msg.location_id == character.location_id:
        return True

    # Global chat
    if msg.channel == "global":
        return True

    # Future: guild / staff / combat channels
    if msg.channel and character_has_access(character, msg.channel):
        return True

    return False

def character_has_access(character, channel):
    return True