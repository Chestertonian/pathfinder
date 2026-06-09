"""
commands/items.py — GetCommand, DropCommand, InventoryCommand
"""

from events import emit_event
from output import to_ansi, colorize, _get_item_color


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
                  AND ii.owner_id = %s
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

            color = _get_item_color(conn, instance_id)

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
            message=f"{character.name} picks up {colorize(item_name, color)}.",
            use_border=False,
        )

        session.send(f"You pick up {colorize(item_name, color)}.\n")
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
                  AND ii.owner_id = %s
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

            color = _get_item_color(conn, instance_id)

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
            message=f"{character.name} drops {colorize(item_name, color)}.",
            use_border=False,
        )

        session.send(f"You drop {colorize(item_name, color)}.\n")
        return None

class InventoryCommand:
    SLOT_ORDER = [
        'weapon', 'offhand', 'head', 'neck', 'back',
        'chest', 'arms', 'ring', 'legs', 'feet'
    ]

    COIN_TEMPLATE_IDS = {4, 5, 6, 7}

    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    it.name,
                    it.type,
                    it.weight,
                    ii.equipped,
                    ii.equipped_slot,
                    ii.quantity,
                    ii.item_template_id,
                    ii.id
                FROM item_instances ii
                JOIN item_templates it
                    ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id = %s
                ORDER BY it.type ASC, it.name ASC
            """, (character.id,))

            rows = cur.fetchall()

        equipped_items = {}
        carried_items = []
        clothing_items = []
        coin_items = []

        for (
            name,
            item_type,
            weight,
            equipped,
            equipped_slot,
            quantity,
            template_id,
            instance_id
        ) in rows:

            if template_id in self.COIN_TEMPLATE_IDS:
                coin_items.append((name, quantity))
                continue

            color = _get_item_color(conn, instance_id)

            if item_type == 'clothing' and equipped:
                clothing_items.append((name, color))
                continue

            if equipped and equipped_slot:
                equipped_items[equipped_slot] = {
                    "name": name,
                    "color": color,
                    "weight": weight,
                    "quantity": quantity
                }
                continue

            carried_items.append({
                "name": name,
                "color": color,
                "weight": weight,
                "quantity": quantity
            })

        lines = []
        lines.append("-" * 40)
        lines.append("")

        # Equipped
        if equipped_items:
            lines.append("  Equipped:")

            for slot in self.SLOT_ORDER:
                item = equipped_items.get(slot)
                if not item:
                    continue

                lines.append(
                    f"    [{slot.capitalize():<8}]  "
                    f"{colorize(item['name'], item['color'])}"
                )

            lines.append("")

        # Carrying
        if carried_items:
            lines.append("  Carrying:")

            for item in carried_items:
                qty_str = (
                    f" (x{item['quantity']})"
                    if item['quantity'] > 1
                    else ""
                )

                lines.append(
                    f"    {colorize(item['name'], item['color'])}"
                    f"{qty_str}"
                )

            lines.append("")

        elif not equipped_items and not clothing_items and not coin_items:
            lines.append("  You are carrying nothing.")
            lines.append("")

        # Coins
        if coin_items:
            lines.append("  Coins:")

            for name, quantity in coin_items:
                label = name if quantity == 1 else f"{name}s"
                lines.append(f"    {quantity} {label}")

            lines.append("")

        # Clothing (now fully instance-based color)
        if clothing_items:
            lines.append("  Wearing:")

            for name, color in clothing_items:
                lines.append(f"    {colorize(name, color)}")

            lines.append("")

        lines.append("-" * 40)

        session.send("\n".join(lines) + "\n")
        return None