# commands/equipment.py

from db import get_connection
from events import emit_event
from output import to_ansi

CLOTHING_LIMIT = 9


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_clothing_template(conn, item_template_id):
    """
    Returns (order_number, color) if this item is clothing, else None.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT order_number, color
            FROM clothing_templates
            WHERE item_template_id = %s
        """,
            (item_template_id,),
        )
        return cur.fetchone()


def _count_equipped_clothing(conn, character_id):
    """
    Returns how many clothing items the character currently has equipped.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM item_instances ii
            JOIN clothing_templates ct ON ct.item_template_id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = TRUE
        """,
            (character_id,),
        )
        return cur.fetchone()[0]


def _get_equipped_clothing(conn, character_id):
    """
    Returns all equipped clothing ordered by order_number.
    Returns list of (instance_id, name, order_number, color).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ii.id, it.name, ct.order_number, ct.color
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            JOIN clothing_templates ct ON ct.item_template_id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = TRUE
            ORDER BY ct.order_number ASC
        """,
            (character_id,),
        )
        return cur.fetchall()


def _get_item_slot(conn, item_template_id, item_type):
    """
    Returns the slot string for an item, or None if not equippable.
    Weapons always return 'weapon'.
    Armor returns whatever slot is defined in armor_templates.
    """
    with conn.cursor() as cur:
        if item_type == "weapon":
            return "weapon"
        elif item_type == "armor":
            cur.execute(
                "SELECT slot FROM armor_templates WHERE item_template_id = %s",
                (item_template_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
        return None


def _get_inventory_item(conn, character, item_name):
    """
    Finds an unequipped item in the character's inventory by name.
    Returns (instance_id, template_id, item_type, item_name) or None.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ii.id, ii.item_template_id, it.type, it.name
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = FALSE
              AND LOWER(it.name) LIKE LOWER(%s)
            LIMIT 1
        """,
            (character.id, f"%{item_name}%"),
        )
        return cur.fetchone()


def _get_equipped_item(conn, character, item_name):
    """
    Finds an equipped item on the character by name.
    Returns (instance_id, template_id, item_type, item_name, equipped_slot) or None.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ii.id, ii.item_template_id, it.type, it.name, ii.equipped_slot
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = TRUE
              AND LOWER(it.name) LIKE LOWER(%s)
            LIMIT 1
        """,
            (character.id, f"%{item_name}%"),
        )
        return cur.fetchone()


def _get_slot_occupant(conn, character, slot):
    """
    Returns (instance_id, item_name) if something is already in that slot, else None.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ii.id, it.name
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped_slot = %s
        """,
            (character.id, slot),
        )
        return cur.fetchone()


def _check_race_allowed(conn, item_template_id, character_race):
    """
    Returns True if the character's race can wear this item.
    NULL allowed_races means anyone can wear it.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT allowed_races FROM armor_templates WHERE item_template_id = %s",
            (item_template_id,),
        )
        row = cur.fetchone()
        if not row:
            return True  # weapon or unrestricted
        allowed = row[0]
        if allowed is None:
            return True
        return character_race in allowed


def _do_equip(conn, character, instance_id, slot=None):
    """Marks an item instance as equipped, with optional slot."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE item_instances
            SET equipped = TRUE, equipped_slot = %s
            WHERE id = %s
        """,
            (slot, instance_id),
        )


def _do_unequip(conn, character, instance_id):
    """Marks an item instance as unequipped."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE item_instances
            SET equipped = FALSE, equipped_slot = NULL
            WHERE id = %s
        """,
            (instance_id,),
        )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class EquipCommand:
    """
    equip <item>  — equip a single item from inventory
    equip         — equip all armor/weapons from inventory
    """

    def execute(self, character, conn, args, session):
        if not args:
            return self._equip_all(character, conn, session)
        return self._equip_one(character, conn, " ".join(args), session)

    def _equip_one(self, character, conn, item_name, session):
        row = _get_inventory_item(conn, character, item_name)
        if not row:
            return f"You don't have '{item_name}' in your inventory.\n"

        instance_id, template_id, item_type, name = row

        # Clothing path
        if item_type == "clothing":
            clothing = _get_clothing_template(conn, template_id)
            if not clothing:
                return f"You can't wear {name}.\n"
            count = _count_equipped_clothing(conn, character.id)
            if count >= CLOTHING_LIMIT:
                return f"You're already wearing as much as you can manage.\n"
            _do_equip(conn, character, instance_id, slot=None)
            conn.commit()
            emit_event(
                conn,
                event_type="room",
                location_id=character.location_id,
                sender_id=character.id,
                message=f"{character.name} puts on {name}.",
            )
            return f"You put on {name}.\n"

        # Armor/weapon path
        slot = _get_item_slot(conn, template_id, item_type)
        if not slot:
            return f"You can't equip {name}.\n"

        if not _check_race_allowed(conn, template_id, character.race):
            return f"Your race cannot wear {name}.\n"

        if item_type == "weapon":
            primary = _get_slot_occupant(conn, character, "weapon")
            if primary:
                offhand = _get_slot_occupant(conn, character, "offhand")
                if offhand:
                    return (
                        f"You already have {primary[1]} wielded and "
                        f"{offhand[1]} in your offhand.\n"
                    )
                slot = "offhand"

        occupant = _get_slot_occupant(conn, character, slot)
        if occupant:
            return (
                f"You're already wearing {occupant[1]} on your {slot}. "
                f"Remove it first.\n"
            )

        _do_equip(conn, character, instance_id, slot)
        conn.commit()

        verb = "wield" if slot in ("weapon", "offhand") else "wear"
        emit_event(
            conn,
            event_type="room",
            location_id=character.location_id,
            sender_id=character.id,
            message=f"{character.name} equips {name}.",
        )
        return f"You {verb} {name}.\n"

    def _equip_all(self, character, conn, session):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ii.id, ii.item_template_id, it.type, it.name
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                AND ii.owner_id = %s
                AND ii.equipped = FALSE
                AND it.type IN ('weapon', 'armor', 'clothing')
                ORDER BY ii.id
            """,
                (character.id,),
            )
            items = cur.fetchall()

        if not items:
            return "You have nothing to equip.\n"

        clothing_count = _count_equipped_clothing(conn, character.id)
        lines = []

        for instance_id, template_id, item_type, name in items:
            if item_type == "clothing":
                clothing = _get_clothing_template(conn, template_id)
                if not clothing:
                    continue
                if clothing_count >= CLOTHING_LIMIT:
                    lines.append(f"  {name}: too many clothing items worn.")
                    continue
                _do_equip(conn, character, instance_id, slot=None)
                clothing_count += 1
                lines.append(f"  {name}: worn.")
                continue

            slot = _get_item_slot(conn, template_id, item_type)
            if not slot:
                continue
            if not _check_race_allowed(conn, template_id, character.race):
                lines.append(f"  {name}: your race cannot wear this.")
                continue
            if item_type == "weapon":
                primary = _get_slot_occupant(conn, character, "weapon")
                if primary:
                    offhand = _get_slot_occupant(conn, character, "offhand")
                    if offhand:
                        lines.append(f"  {name}: no free weapon slots.")
                        continue
                    slot = "offhand"
            occupant = _get_slot_occupant(conn, character, slot)
            if occupant:
                lines.append(f"  {name}: {slot} already occupied by {occupant[1]}.")
                continue
            _do_equip(conn, character, instance_id, slot)
            verb = "wielded" if slot in ("weapon", "offhand") else "worn"
            lines.append(f"  {name}: {verb}.")

        conn.commit()
        return "Equipping inventory:\n" + "\n".join(lines) + "\n"


class RemoveCommand:
    """remove <item> — unequip a specific item by name"""

    def execute(self, character, conn, args, session):
        if not args:
            return "Remove what?\n"

        item_name = " ".join(args)
        row = _get_equipped_item(conn, character, item_name)
        if not row:
            return f"You aren't wearing '{item_name}'.\n"

        instance_id, template_id, item_type, name, slot = row
        _do_unequip(conn, character, instance_id)
        conn.commit()

        emit_event(
            conn,
            event_type="room",
            location_id=character.location_id,
            sender_id=character.id,
            message=f"{character.name} removes {name}.",
        )
        return f"You remove {name}.\n"


class UnequipCommand:
    """unequip — remove everything currently equipped"""

    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ii.id, it.name
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id = %s
                  AND ii.equipped = TRUE
            """,
                (character.id,),
            )
            items = cur.fetchall()

        if not items:
            return "You aren't wearing anything.\n"

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE item_instances
                SET equipped = FALSE, equipped_slot = NULL
                WHERE owner_type = 'character'
                  AND owner_id = %s
                  AND equipped = TRUE
            """,
                (character.id,),
            )
        conn.commit()

        names = ", ".join(row[1] for row in items)
        return f"You remove {names}.\n"


class EqCommand:
    """eq — show all equipment slots and worn clothing"""

    SLOT_ORDER = [
        'weapon', 'offhand', 'head', 'neck', 'back',
        'chest', 'arms', 'legs', 'feet', 'ring'
    ]

    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            # Armor/weapons
            cur.execute("""
                SELECT ii.equipped_slot, it.name
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id = %s
                  AND ii.equipped = TRUE
                  AND ii.equipped_slot IS NOT NULL
            """, (character.id,))
            armor_rows = cur.fetchall()

        equipped = {slot: name for slot, name in armor_rows}
        clothing = _get_equipped_clothing(conn, character.id)

        lines = [f"Equipment for {character.name}:", ""]

        # Armor/weapon slots
        for slot in self.SLOT_ORDER:
            label = slot.capitalize().ljust(8)
            item = equipped.get(slot, "<empty>")
            lines.append(f"  [{label}]  {item}")

        # Clothing section
        if clothing:
            lines.append("")
            lines.append("  Wearing:")
            for _, name, order_number, color in clothing:
                if color:
                    line = to_ansi(f"[{color}]    {name}[/{color}]")
                else:
                    line = f"    {name}"
                lines.append(line)

        return "\n".join(lines) + "\n"
    

def get_item_color(conn, item_template_id):
    """
    Returns the color for an item template, or None.
    Checks clothing_templates first, armor_templates next (when you add color there).
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT color FROM clothing_templates
            WHERE item_template_id = %s
        """, (item_template_id,))
        row = cur.fetchone()
        if row:
            return row[0]
    return None