# powers/handlers/tailor.py

TAILOR_ROOM_ID = 250


def execute(character, target, args, conn, session):
    if character.location_id != TAILOR_ROOM_ID:
        session.send("You need to be at a tailor's shop to create clothing.\n")
        return

    if not args:
        session.send("Usage: tailor <item name>\n  e.g. tailor ugly pink hat\n")
        return

    item_name = " ".join(args)

    session.send("Enter description (one line):\n> ")
    description = session.recv().strip()

    if not description:
        session.send("Cancelled — no description entered.\n")
        return

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO item_templates
                (name, type, description, weight, value, is_takeable, is_droppable)
            VALUES (%s, 'clothing', %s, 1, 0, TRUE, TRUE)
            RETURNING id
        """, (item_name, description))
        template_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO clothing_templates
                (item_template_id, order_number, color)
            VALUES (%s, 8, NULL)
        """, (template_id,))

        cur.execute("""
            INSERT INTO item_instances
                (item_template_id, owner_type, owner_id, equipped, quantity)
            VALUES (%s, 'character', %s, FALSE, 1)
        """, (template_id, character.id))

    conn.commit()
    session.send(f"You craft {item_name} and add it to your inventory.\n")