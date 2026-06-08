# powers/handlers/ordernumber.py


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
    if len(args) < 2:
        session.send("Usage: ordernumber <item> <1-15>\n")
        return

    try:
        order = int(args[-1])
    except ValueError:
        session.send("Usage: ordernumber <item> <1-15>\n")
        return

    if not 1 <= order <= 15:
        session.send("Order number must be between 1 and 15.\n")
        return

    item_name = " ".join(args[:-1])
    row = _get_clothing_in_inventory(conn, character.id, item_name)
    if not row:
        session.send(f"You don't have '{item_name}' in your inventory.\n")
        return

    instance_id, template_id, name = row

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE clothing_templates
            SET order_number = %s
            WHERE item_template_id = %s
        """, (order, template_id))

    conn.commit()
    session.send(f"{name} will now display at position {order}.\n")