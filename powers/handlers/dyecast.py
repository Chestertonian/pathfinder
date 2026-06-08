# powers/handlers/dyecast.py

from output import to_ansi

TAILOR_ROOM_ID = 250

VALID_COLORS = {
    'black', 'red', 'green', 'yellow', 'blue', 'magenta',
    'cyan', 'white', 'bright_black', 'bright_red', 'bright_green',
    'bright_yellow', 'bright_blue', 'bright_magenta', 'bright_cyan',
    'bright_white'
}


def _get_clothing_in_inventory(conn, character_id, item_name):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ii.id, ii.item_template_id, it.name
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            JOIN clothing_templates ct ON ct.item_template_id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND LOWER(it.name) LIKE LOWER(%s)
            LIMIT 1
        """, (character_id, f"%{item_name}%"))
        return cur.fetchone()


def execute(character, target, args, conn, session):
    if character.location_id != TAILOR_ROOM_ID:
        session.send("You need to be at a tailor's shop to dye clothing.\n")
        return

    if len(args) < 2:
        session.send("Usage: dyecast <item> <color>\n")
        return

    color = args[-1].lower()
    item_name = " ".join(args[:-1])

    if color not in VALID_COLORS:
        valid = ", ".join(sorted(VALID_COLORS))
        session.send(f"'{color}' is not a valid color.\nValid colors: {valid}\n")
        return

    row = _get_clothing_in_inventory(conn, character.id, item_name)
    if not row:
        session.send(f"You don't have '{item_name}' in your inventory.\n")
        return

    instance_id, template_id, name = row

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE clothing_templates
            SET color = %s
            WHERE item_template_id = %s
        """, (color, template_id))

    conn.commit()
    colored_name = to_ansi(f"[{color}]{name}[/{color}]")
    session.send(f"{name} is now dyed {color}. It appears as: {colored_name}\n")