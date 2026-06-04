# room_scripts/merchant_guild.py

import json
from events import emit_event

def on_command(character, room, verb, args, conn, session) -> bool:
    if verb != "join":
        return False

    if character.char_class is not None and character.char_class != "immigrant":
        session.send(f"You are already a member of the {character.char_class.capitalize()}s Guild.\n")
        return True

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE characters SET class = 'merchant' WHERE id = %s",
            (character.id,)
        )
        cur.execute("""
            INSERT INTO audit_log (character_id, action, entity_type, location_id, details)
            VALUES (%s, 'guild_join', 'guild', %s, %s)
        """, (
            character.id,
            room.id,
            json.dumps({"guild": "merchant"})
        ))

    conn.commit()

    character.char_class = "merchant"

    session.send("You register with the Merchants Guild. The guildmaster stamps your papers.\n")

    emit_event(conn, event_type="room", location_id=room.id,
               sender_id=character.id,
               message=f"{character.name} joins the Merchants Guild.")

    return True