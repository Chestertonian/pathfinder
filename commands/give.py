# commands/give.py

from events import emit_event
from commands.economy import (
    COIN_TEMPLATES, COIN_VALUES,
    _get_coin_instance, _add_coins_to_character,
    _remove_coins_from_character, recalculate_copper,
    _format_wealth
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_online_character_in_room(conn, character_id, location_id, target_name):
    """
    Finds a logged-in character in the same room by name.
    Returns (id, name) or None.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name
            FROM characters
            WHERE LOWER(name) LIKE LOWER(%s)
              AND location_id = %s
              AND is_logged_in = TRUE
              AND id != %s
            LIMIT 1
        """, (f"%{target_name}%", location_id, character_id))
        return cur.fetchone()


def _get_item_in_inventory(conn, character_id, item_name):
    """
    Finds an unequipped, non-coin item in inventory by name.
    Returns (instance_id, template_id, name, quantity) or None.
    """
    coin_ids = list(COIN_TEMPLATES.values())
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ii.id, ii.item_template_id, it.name, ii.quantity
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = FALSE
              AND ii.item_template_id != ALL(%s)
              AND LOWER(it.name) LIKE LOWER(%s)
            LIMIT 1
        """, (character_id, coin_ids, f"%{item_name}%"))
        return cur.fetchone()


def _get_equipped_check(conn, character_id, item_name):
    """
    Returns True if the character has a matching item that is equipped.
    Used to give a better error message.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = TRUE
              AND LOWER(it.name) LIKE LOWER(%s)
            LIMIT 1
        """, (character_id, f"%{item_name}%"))
        return cur.fetchone() is not None


def _give_item(conn, instance_id, template_id, quantity, amount, recipient_id):
    """
    Transfers `amount` of an item stack to recipient.
    If amount >= quantity, moves the whole instance.
    Otherwise splits the stack.
    """
    with conn.cursor() as cur:
        if amount >= quantity:
            # Move whole instance
            cur.execute("""
                UPDATE item_instances
                SET owner_type = 'character', owner_id = %s
                WHERE id = %s
            """, (recipient_id, instance_id))
        else:
            # Split stack — reduce sender's quantity
            cur.execute("""
                UPDATE item_instances
                SET quantity = quantity - %s
                WHERE id = %s
            """, (amount, instance_id))
            # Give recipient a new instance
            cur.execute("""
                INSERT INTO item_instances
                    (item_template_id, owner_type, owner_id, equipped, quantity)
                VALUES (%s, 'character', %s, FALSE, %s)
            """, (template_id, recipient_id, amount))


def _try_parse_coin(args):
    """
    Tries to parse args tail as '<amount> <denomination>'.
    Returns (amount, denomination) or (None, None).
    """
    if len(args) < 2:
        return None, None
    try:
        amount = int(args[-2])
    except ValueError:
        return None, None
    denomination = args[-1].lower().rstrip('s')
    if denomination not in COIN_TEMPLATES:
        return None, None
    if amount <= 0:
        return None, None
    return amount, denomination


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class GiveCommand:
    """
    give <player> <amount> <denomination>  — give coins
    give <player> <item>                   — give single item
    give <player> <amount> <item>          — give quantity of stacked item
    """

    def execute(self, character, conn, args, session):
        if len(args) < 2:
            session.send("Usage: give <player> <item or amount denomination>\n")
            return

        # First arg is always the target player name
        target_name = args[0]
        rest = args[1:]

        # Find recipient
        recipient = _get_online_character_in_room(
            conn, character.id, character.location_id, target_name
        )
        if not recipient:
            session.send(f"'{target_name}' is not here.\n")
            return

        recipient_id, recipient_name = recipient

        # Try coin parse first: last two args are '<amount> <denomination>'
        coin_amount, denomination = _try_parse_coin(rest)
        if coin_amount is not None:
            self._give_coins(
                character, conn, session,
                recipient_id, recipient_name,
                coin_amount, denomination
            )
            return

        # Item parse: try '<amount> <item name>' or just '<item name>'
        item_amount = 1
        item_name_parts = rest

        if len(rest) >= 2:
            try:
                item_amount = int(rest[0])
                item_name_parts = rest[1:]
            except ValueError:
                item_amount = 1
                item_name_parts = rest

        item_name = " ".join(item_name_parts)
        self._give_item(
            character, conn, session,
            recipient_id, recipient_name,
            item_name, item_amount
        )

    def _give_coins(self, character, conn, session,
                    recipient_id, recipient_name, amount, denomination):

        # Check sender has enough
        row = _get_coin_instance(conn, character.id, COIN_TEMPLATES[denomination])
        held = row[1] if row else 0
        if held < amount:
            label = denomination + ('s' if amount != 1 else '')
            session.send(f"You don't have {amount} {label} to give.\n")
            return

        copper_value = amount * COIN_VALUES[denomination]

        # Transfer
        _remove_coins_from_character(conn, character.id, denomination, amount)
        _add_coins_to_character(conn, recipient_id, denomination, amount)
        recalculate_copper(conn, character.id)
        recalculate_copper(conn, recipient_id)

        label = denomination + ('s' if amount != 1 else '')

        emit_event(conn, event_type="room",
                   location_id=character.location_id,
                   sender_id=character.id,
                   message=f"{character.name} gives {recipient_name} {amount} {label}.")

        session.send(
            f"You give {recipient_name} {amount} {label} "
            f"({_format_wealth(copper_value)}).\n"
        )

        emit_event(conn, event_type="system",
                   location_id=character.location_id,
                   sender_id=recipient_id,
                   message=f"{character.name} gives you {amount} {label} "
                           f"({_format_wealth(copper_value)}).\n")

        conn.commit()

    def _give_item(self, character, conn, session,
                   recipient_id, recipient_name, item_name, amount):

        # Check if item is equipped
        if _get_equipped_check(conn, character.id, item_name):
            session.send("You are wearing that.\n")
            return

        row = _get_item_in_inventory(conn, character.id, item_name)
        if not row:
            session.send(f"You don't have '{item_name}'.\n")
            return

        instance_id, template_id, name, quantity = row

        if amount > quantity:
            session.send(
                f"You only have {quantity} {name}"
                f"{'s' if quantity != 1 else ''}.\n"
            )
            return

        _give_item(conn, instance_id, template_id, quantity, amount, recipient_id)

        qty_str = f"{amount} " if amount > 1 else ""

        emit_event(conn, event_type="room",
                   location_id=character.location_id,
                   sender_id=character.id,
                   message=f"{character.name} gives {recipient_name} {qty_str}{name}.")

        session.send(f"You give {recipient_name} {qty_str}{name}.\n")

        emit_event(conn, event_type="system",
                   location_id=character.location_id,
                   sender_id=recipient_id,
                   message=f"{character.name} gives you {qty_str}{name}.\n")

        conn.commit()