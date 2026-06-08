# commands/equipment.py

from db import get_connection
from events import emit_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_item_slot(conn, item_template_id, item_type):
    """
    Returns the slot string for an item, or None if not equippable.
    Weapons always return 'weapon'.
    Armor returns whatever slot is defined in armor_templates.
    """
    with conn.cursor() as cur:
        if item_type == 'weapon':
            return 'weapon'
        elif item_type == 'armor':
            cur.execute(
                "SELECT slot FROM armor_templates WHERE item_template_id = %s",
                (item_template_id,)
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
        cur.execute("""
            SELECT ii.id, ii.item_template_id, it.type, it.name
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = FALSE
              AND LOWER(it.name) LIKE LOWER(%s)
            LIMIT 1
        """, (character.id, f"%{item_name}%"))
        return cur.fetchone()


def _get_equipped_item(conn, character, item_name):
    """
    Finds an equipped item on the character by name.
    Returns (instance_id, template_id, item_type, item_name, equipped_slot) or None.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ii.id, ii.item_template_id, it.type, it.name, ii.equipped_slot
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = TRUE
              AND LOWER(it.name) LIKE LOWER(%s)
            LIMIT 1
        """, (character.id, f"%{item_name}%"))
        return cur.fetchone()


def _get_slot_occupant(conn, character, slot):
    """
    Returns (instance_id, item_name) if something is already in that slot, else None.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ii.id, it.name
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped_slot = %s
        """, (character.id, slot))
        return cur.fetchone()


def _check_race_allowed(conn, item_template_id, character_race):
    """
    Returns True if the character's race can wear this item.
    NULL allowed_races means anyone can wear it.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT allowed_races FROM armor_templates WHERE item_template_id = %s",
            (item_template_id,)
        )
        row = cur.fetchone()
        if not row:
            return True  # weapon or unrestricted
        allowed = row[0]
        if allowed is None:
            return True
        return character_race in allowed


def _do_equip(conn, character, instance_id, slot):
    """Marks an item instance as equipped in the given slot."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE item_instances
            SET equipped = TRUE, equipped_slot = %s
            WHERE id = %s
        """, (slot, instance_id))


def _do_unequip(conn, character, instance_id):
    """Marks an item instance as unequipped."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE item_instances
            SET equipped = FALSE, equipped_slot = NULL
            WHERE id = %s
        """, (instance_id,))


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

        # Get slot
        slot = _get_item_slot(conn, template_id, item_type)
        if not slot:
            return f"You can't equip {name}.\n"

        # Race check
        if not _check_race_allowed(conn, template_id, character.race):
            return f"Your race cannot wear {name}.\n"

        # Offhand weapon rule: only if primary weapon slot is empty
        if item_type == 'weapon':
            primary = _get_slot_occupant(conn, character, 'weapon')
            if primary:
                # Try offhand
                offhand = _get_slot_occupant(conn, character, 'offhand')
                if offhand:
                    return (
                        f"You already have {primary[1]} wielded and "
                        f"{offhand[1]} in your offhand.\n"
                    )
                slot = 'offhand'

        # Conflict check
        occupant = _get_slot_occupant(conn, character, slot)
        if occupant:
            return (
                f"You're already wearing {occupant[1]} on your {slot}. "
                f"Remove it first.\n"
            )

        _do_equip(conn, character, instance_id, slot)
        conn.commit()

        verb = "wield" if slot in ('weapon', 'offhand') else "wear"
        emit_event(conn, event_type="room", location_id=character.location_id,
                   sender_id=character.id,
                   message=f"{character.name} equips {name}.")
        return f"You {verb} {name}.\n"

    def _equip_all(self, character, conn, session):
        """Attempt to equip every unequipped armor/weapon in inventory."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ii.id, ii.item_template_id, it.type, it.name
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id = %s
                  AND ii.equipped = FALSE
                  AND it.type IN ('weapon', 'armor')
                ORDER BY ii.id
            """, (character.id,))
            items = cur.fetchall()

        if not items:
            return "You have nothing to equip.\n"

        lines = []
        for instance_id, template_id, item_type, name in items:
            slot = _get_item_slot(conn, template_id, item_type)
            if not slot:
                continue
            if not _check_race_allowed(conn, template_id, character.race):
                lines.append(f"  {name}: your race cannot wear this.")
                continue
            if item_type == 'weapon':
                primary = _get_slot_occupant(conn, character, 'weapon')
                if primary:
                    offhand = _get_slot_occupant(conn, character, 'offhand')
                    if offhand:
                        lines.append(f"  {name}: no free weapon slots.")
                        continue
                    slot = 'offhand'
            occupant = _get_slot_occupant(conn, character, slot)
            if occupant:
                lines.append(f"  {name}: {slot} already occupied by {occupant[1]}.")
                continue
            _do_equip(conn, character, instance_id, slot)
            verb = "wielded" if slot in ('weapon', 'offhand') else "worn"
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

        emit_event(conn, event_type="room", location_id=character.location_id,
                   sender_id=character.id,
                   message=f"{character.name} removes {name}.")
        return f"You remove {name}.\n"


class UnequipCommand:
    """unequip — remove everything currently equipped"""

    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ii.id, it.name
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id = %s
                  AND ii.equipped = TRUE
            """, (character.id,))
            items = cur.fetchall()

        if not items:
            return "You aren't wearing anything.\n"

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE item_instances
                SET equipped = FALSE, equipped_slot = NULL
                WHERE owner_type = 'character'
                  AND owner_id = %s
                  AND equipped = TRUE
            """, (character.id,))
        conn.commit()

        names = ", ".join(row[1] for row in items)
        return f"You remove {names}.\n"


class EqCommand:
    """eq — show all equipment slots"""

    SLOT_ORDER = [
        'head', 'neck', 'back', 'chest', 'arms',
        'legs', 'feet', 'ring', 'weapon', 'offhand'
    ]

    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ii.equipped_slot, it.name
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'character'
                  AND ii.owner_id = %s
                  AND ii.equipped = TRUE
            """, (character.id,))
            rows = cur.fetchall()

        equipped = {slot: name for slot, name in rows}

        lines = [f"Equipment for {character.name}:", ""]
        for slot in self.SLOT_ORDER:
            label = slot.capitalize().ljust(8)
            item = equipped.get(slot, "<empty>")
            lines.append(f"  [{label}]  {item}")

        return "\n".join(lines) + "\n"