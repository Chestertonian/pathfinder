# room_scripts/merchant_guild.py

import json
from events import emit_event
from output import to_ansi

WIDTH = 78

def on_command(character, room, verb, args, conn, session) -> bool:
    if verb != "join":
        return False

    if character.char_class is not None and character.char_class.strip().capitalize() != "Immigrant":
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

    
    message = "\n".join([
        to_ansi("[green]" + "-" * WIDTH + "[/green]"),
        to_ansi("[red]" + center("Hear ye! Hear ye!") + "[/red]"),
        to_ansi("[yellow]" + center("Trumpets sound across the city...") + "[/yellow]"),
        to_ansi("[yellow]" + center(f"{character.name} joins the Merchants Guild!") + "[/yellow]"),
        to_ansi("[green]" + "-" * WIDTH + "[/green]"),
    ])

    emit_event(
        conn,
        event_type="global",
        message=message
    )

    return True

def center(text, width=WIDTH):
    text = str(text)
    pad = max(0, (width - len(text)) // 2)
    return " " * pad + text

