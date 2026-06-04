# room_scripts/merchant_guild.py

import json
from events import emit_event

def on_enter(character, room, conn, session):
    print(f"[debug] on_enter fired, char_class = {character.char_class!r}")
    if character.char_class == 'immigrant':
        session.send("A sign reads: 'Traders and merchants welcome. Type JOIN to register.'")

def on_command(character, room, verb, args, conn, session) -> bool:
    if verb != "join":
        return False

    if character.char_class is not None:
        session.send(f"You are already a member of the {character.char_class.capitalize()}s Guild.")
        return True

    with conn.cursor() as cur:
        # 1. Set the class
        cur.execute(
            "UPDATE characters SET class = 'merchant' WHERE id = %s",
            (character.id,)
        )

        # 2. Write to audit log
        cur.execute("""
            INSERT INTO audit_log (character_id, action, entity_type, location_id, details)
            VALUES (%s, 'guild_join', 'guild', %s, %s)
        """, (
            character.id,
            room.id,
            json.dumps({"guild": "merchant"})
        ))

    conn.commit()

    # 3. Update the in-memory character so the rest of the session reflects it
    character.char_class = "merchant"

    # 4. Tell the player
    session.send("You register with the Merchants Guild. The guildmaster stamps your papers.")

    # 5. Tell the room
    emit_event(conn, event_type="room", location_id=room.id,
               sender_id=character.id,
               message=f"{character.name} joins the Merchants Guild.")

    return True