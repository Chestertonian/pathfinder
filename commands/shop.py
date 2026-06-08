# commands/shop.py

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

def _get_shop(conn, location_id):
    """
    Returns (shop_id, buys_types) if a shop exists at this location, else None.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, buys_types
            FROM shops
            WHERE location_id = %s
            LIMIT 1
        """, (location_id,))
        return cur.fetchone()


def _get_shop_inventory(conn, location_id):
    """
    Returns all in-stock items for sale at this location.
    Excludes items with stock = 0.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT si.id, it.name, it.type, si.price, si.stock
            FROM shop_inventories si
            JOIN item_templates it ON it.id = si.item_template_id
            WHERE si.location_id = %s
              AND (si.stock IS NULL OR si.stock > 0)
            ORDER BY it.type ASC, it.name ASC
        """, (location_id,))
        return cur.fetchall()


def _get_shop_item(conn, location_id, item_name):
    """
    Finds a specific in-stock item for sale by name.
    Returns (shop_id, template_id, name, price, stock) or None.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT si.id, si.item_template_id, it.name, si.price, si.stock
            FROM shop_inventories si
            JOIN item_templates it ON it.id = si.item_template_id
            WHERE si.location_id = %s
              AND (si.stock IS NULL OR si.stock > 0)
              AND LOWER(it.name) LIKE LOWER(%s)
            LIMIT 1
        """, (location_id, f"%{item_name}%"))
        return cur.fetchone()


def _carried_copper_total(conn, character_id):
    """
    Returns total copper value of all coins the character is carrying.
    """
    total = 0
    for denomination, template_id in COIN_TEMPLATES.items():
        row = _get_coin_instance(conn, character_id, template_id)
        if row:
            total += row[1] * COIN_VALUES[denomination]
    return total


def _deduct_cost(conn, character_id, cost_copper):
    """
    Deducts cost_copper from a character's carried coins.
    Consumes largest denominations first, mints change if needed.
    Assumes affordability has already been checked.
    """
    held = {}
    for denomination in ('sovereign', 'gold', 'silver', 'copper'):
        row = _get_coin_instance(conn, character_id, COIN_TEMPLATES[denomination])
        held[denomination] = row[1] if row else 0

    pool = 0
    for denomination in ('sovereign', 'gold', 'silver', 'copper'):
        if held[denomination] > 0:
            pool += held[denomination] * COIN_VALUES[denomination]
            _remove_coins_from_character(
                conn, character_id, denomination, held[denomination]
            )

    pool -= cost_copper

    for denomination in ('sovereign', 'gold', 'silver', 'copper'):
        value = COIN_VALUES[denomination]
        qty = pool // value
        pool %= value
        if qty > 0:
            _add_coins_to_character(conn, character_id, denomination, qty)


def _sellable_item(conn, character_id, item_name):
    """
    Finds an unequipped, non-coin item in inventory by name.
    Returns (instance_id, template_id, name, type, value) or None.
    """
    coin_ids = list(COIN_TEMPLATES.values())
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ii.id, ii.item_template_id, it.name, it.type, it.value
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


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

class ListCommand:
    """list — show items for sale at current location"""

    def execute(self, character, conn, args, session):
        shop = _get_shop(conn, character.location_id)
        if not shop:
            return "There is nothing for sale here.\n"

        rows = _get_shop_inventory(conn, character.location_id)
        if not rows:
            return "There is nothing for sale here.\n"

        lines = ["-" * 40, ""]
        for shop_id, name, item_type, price, stock in rows:
            price_str = _format_wealth(price)
            stock_str = f"  ({stock} left)" if stock is not None else ""
            lines.append(f"  {name:<28} {price_str}{stock_str}")
        lines.append("")
        lines.append("-" * 40)

        return "\n".join(lines) + "\n"


class BuyCommand:
    """buy <item> — purchase an item from the shop"""

    def execute(self, character, conn, args, session):
        if not args:
            return "Buy what?\n"

        shop = _get_shop(conn, character.location_id)
        if not shop:
            return "There is nothing for sale here.\n"

        item_name = " ".join(args)
        row = _get_shop_item(conn, character.location_id, item_name)
        if not row:
            return f"'{item_name}' is not available here.\n"

        shop_id, template_id, name, price, stock = row

        carried = _carried_copper_total(conn, character.id)
        if carried < price:
            return (
                f"You can't afford {name}.\n"
                f"  Cost:     {_format_wealth(price)}\n"
                f"  On hand:  {_format_wealth(carried)}\n"
            )

        _deduct_cost(conn, character.id, price)

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO item_instances
                    (item_template_id, owner_type, owner_id, equipped, quantity)
                VALUES (%s, 'character', %s, FALSE, 1)
            """, (template_id, character.id))

            if stock is not None:
                cur.execute("""
                    UPDATE shop_inventories
                    SET stock = stock - 1
                    WHERE id = %s
                """, (shop_id,))

        recalculate_copper(conn, character.id)
        conn.commit()

        return f"You buy {name} for {_format_wealth(price)}.\n"


class SellCommand:
    """sell <item> — sell an item to the shop"""

    def execute(self, character, conn, args, session):
        if not args:
            return "Sell what?\n"

        shop = _get_shop(conn, character.location_id)
        if not shop:
            return "You can't sell anything here.\n"

        shop_id, buys_types = shop

        # Shop buys nothing
        if not buys_types:
            return "This shop doesn't buy anything.\n"

        item_name = " ".join(args)
        row = _sellable_item(conn, character.id, item_name)
        if not row:
            return f"You don't have '{item_name}' to sell.\n"

        instance_id, template_id, name, item_type, value = row

        # Type check
        if item_type not in buys_types:
            return f"This shop doesn't buy {item_type}s.\n"

        if value == 0:
            return f"{name} is worthless — they will not buy that.\n"

        sell_price = max(1, value // 2)

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM item_instances WHERE id = %s", (instance_id,)
            )

        _add_coins_to_character(conn, character.id, 'copper', sell_price)
        recalculate_copper(conn, character.id)
        conn.commit()

        return f"You sell {name} for {_format_wealth(sell_price)}.\n"