"""
commands/spawnitem.py — SpawnItemCommand (staff only)

Usage:
    spawnitem <name>

Searches item_templates by name (partial match) and spawns the first
match as a new item_instance in the staff member's current room.
"""

from output import print_info


class SpawnItemCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You are not permitted to do that."

        if not args:
            return "Spawn what?"

        search = " ".join(args).lower()

        with conn.cursor() as cur:
            # Find the first matching template
            cur.execute(
                """
                SELECT id, name
                FROM item_templates
                WHERE LOWER(name) LIKE %s
                ORDER BY id ASC
                LIMIT 1
                """,
                (f"%{search}%",),
            )
            row = cur.fetchone()

            if row is None:
                return f"No item template matching '{search}'."

            template_id, item_name = row

            # Spawn an instance in the staff member's current room
            cur.execute(
                """
                INSERT INTO item_instances (item_template_id, owner_type, owner_id)
                VALUES (%s, 'location', %s)
                RETURNING id
                """,
                (template_id, character.location_id),
            )
            instance_id = cur.fetchone()[0]

        conn.commit()

        print_info(f"Spawned {item_name} (instance #{instance_id}) in this room.")

        return None