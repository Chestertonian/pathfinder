"""
commands/items.py — GetCommand, DropCommand, InventoryCommand
"""

from events import emit_event


class GetCommand:
    def execute(self, character, conn, args, session):
        if not args:
            return "Get what?"

        search = " ".join(args).lower()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ii.id, it.name, it.is_takeable
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'location'
                  AND ii.owner_id   = %s
                  AND LOWER(it.name) LIKE %s
                ORDER BY ii.id ASC
                LIMIT 1
                """,
                (character.location_id, f"%{search}%"),
            )
            row = cur.fetchone()

            if row is None:
                return "You don't see that here."

            instance_id, item_name, is_takeable = row

            if not is_takeable:
                return "You can't get that."

            cur.execute(
                """
                UPDATE item_instances
                SET owner_type = 'character',
                    owner_id   = %s
                WHERE id = %s
                """,
                (character.id, instance_id),
            )

        conn.commit()

        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} picks up {item_name}.",
            color="grey54",
            use_border=False,
        )

        session.send(f"You pick up {item_name}.\n")  # CHANGED
        return None


class DropCommand:
    def execute(self, character, conn, args, session):
        if not args:
            return "Drop what?"

        search = " ".join(args).lower()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ii.id, it.name, it.is_droppable
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id   = %s
                  AND LOWER(it.name) LIKE %s
                ORDER BY ii.id ASC
                LIMIT 1
                """,
                (character.id, f"%{search}%"),
            )
            row = cur.fetchone()

            if row is None:
                return "You don't have that."

            instance_id, item_name, is_droppable = row

            if not is_droppable:
                return "You can't drop that."

            cur.execute(
                """
                UPDATE item_instances
                SET owner_type = 'location',
                    owner_id   = %s,
                    equipped   = FALSE
                WHERE id = %s
                """,
                (character.location_id, instance_id),
            )

        conn.commit()

        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} drops {item_name}.",
            color="grey54",
            use_border=False,
        )

        session.send(f"You drop {item_name}.\n")  # CHANGED
        return None


class InventoryCommand:
    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT it.name, it.type, it.weight, ii.equipped
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id   = %s
                ORDER BY it.type ASC, it.name ASC
                """,
                (character.id,),
            )
            rows = cur.fetchall()

        lines = []
        lines.append("-" * 40)  # CHANGED: was rule()
        lines.append("")

        if not rows:
            lines.append("  You are carrying nothing.")
        else:
            for name, item_type, weight, equipped in rows:
                # CHANGED: plain string formatting instead of multi-part console.print
                equip_str = "  [equipped]" if equipped else ""
                lines.append(f"  {name:<30} {item_type:<12} {weight} lb{equip_str}")

        lines.append("")
        lines.append("-" * 40)

        session.send("\n".join(lines) + "\n")
        return None