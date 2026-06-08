# commands/economy.py

from db import get_connection
from events import emit_event

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BANK_ROOM_ID = 249

COIN_TEMPLATES = {
    "copper": 4,
    "silver": 5,
    "gold": 6,
    "sovereign": 7,
}

COIN_VALUES = {
    "copper": 1,
    "silver": 10,
    "gold": 100,
    "sovereign": 1000,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def recalculate_copper(conn, character_id):
    """
    Sums all coin instances the character is carrying and updates
    characters.copper. Call this after any operation that moves coins.
    """
    with conn.cursor() as cur:
        total = 0
        for denomination, template_id in COIN_TEMPLATES.items():
            cur.execute(
                """
                SELECT COALESCE(SUM(quantity), 0)
                FROM item_instances
                WHERE owner_type = 'character'
                  AND owner_id = %s
                  AND item_template_id = %s
            """,
                (character_id, template_id),
            )
            qty = cur.fetchone()[0]
            total += qty * COIN_VALUES[denomination]

        cur.execute(
            """
            UPDATE characters SET copper = %s WHERE id = %s
        """,
            (total, character_id),
        )


def _get_coin_instance(conn, character_id, template_id):
    """
    Returns (instance_id, quantity) for a denomination the character
    is carrying, or None if they have none.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, quantity
            FROM item_instances
            WHERE owner_type = 'character'
              AND owner_id = %s
              AND item_template_id = %s
            LIMIT 1
        """,
            (character_id, template_id),
        )
        return cur.fetchone()


def _add_coins_to_character(conn, character_id, denomination, amount):
    """
    Adds `amount` coins of `denomination` to a character's inventory,
    merging into an existing stack if one exists.
    """
    template_id = COIN_TEMPLATES[denomination]
    existing = _get_coin_instance(conn, character_id, template_id)

    with conn.cursor() as cur:
        if existing:
            cur.execute(
                """
                UPDATE item_instances
                SET quantity = quantity + %s
                WHERE id = %s
            """,
                (amount, existing[0]),
            )
        else:
            cur.execute(
                """
                INSERT INTO item_instances
                    (item_template_id, owner_type, owner_id, equipped, quantity)
                VALUES (%s, 'character', %s, FALSE, %s)
            """,
                (template_id, character_id, amount),
            )


def _remove_coins_from_character(conn, character_id, denomination, amount):
    """
    Removes `amount` coins of `denomination` from a character's inventory.
    Deletes the instance row if quantity reaches 0.
    Returns False if they don't have enough, True on success.
    """
    template_id = COIN_TEMPLATES[denomination]
    existing = _get_coin_instance(conn, character_id, template_id)

    if not existing or existing[1] < amount:
        return False

    with conn.cursor() as cur:
        new_qty = existing[1] - amount
        if new_qty == 0:
            cur.execute("DELETE FROM item_instances WHERE id = %s", (existing[0],))
        else:
            cur.execute(
                """
                UPDATE item_instances SET quantity = %s WHERE id = %s
            """,
                (new_qty, existing[0]),
            )
    return True


def _parse_args(args):
    """
    Parses 'amount denomination' from args list.
    Returns (amount, denomination) or (None, None) on failure.
    """
    if len(args) != 2:
        return None, None
    try:
        amount = int(args[0])
    except ValueError:
        return None, None
    denomination = args[1].lower().rstrip("s")  # allow 'coppers', 'sovereigns' etc.
    if denomination not in COIN_TEMPLATES:
        return None, None
    if amount <= 0:
        return None, None
    return amount, denomination


def _format_wealth(copper_total):
    """
    Formats a copper integer into a readable string.
    e.g. 1234 copper → '1 sovereign, 2 gold, 3 silver, 4 copper'
    """
    if copper_total == 0:
        return "nothing"

    parts = []
    remainder = copper_total

    for denomination in ("sovereign", "gold", "silver", "copper"):
        value = COIN_VALUES[denomination]
        qty = remainder // value
        remainder %= value
        if qty > 0:
            label = denomination if qty == 1 else denomination + "s"
            parts.append(f"{qty} {label}")

    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class WealthCommand:
    """wealth — show carried coins and bank balance"""

    def execute(self, character, conn, args, session):
        # Carried coins — read directly from instances for accuracy
        with conn.cursor() as cur:
            carried_total = 0
            lines = []
            for denomination in ("sovereign", "gold", "silver", "copper"):
                template_id = COIN_TEMPLATES[denomination]
                cur.execute(
                    """
                    SELECT COALESCE(SUM(quantity), 0)
                    FROM item_instances
                    WHERE owner_type = 'character'
                      AND owner_id = %s
                      AND item_template_id = %s
                """,
                    (character.id, template_id),
                )
                qty = cur.fetchone()[0]
                if qty > 0:
                    label = denomination if qty == 1 else denomination + "s"
                    lines.append(f"  {qty} {label}")
                carried_total += qty * COIN_VALUES[denomination]

            # Bank balance
            cur.execute(
                "SELECT bank_copper FROM characters WHERE id = %s", (character.id,)
            )
            bank_copper = cur.fetchone()[0]

        carried_str = "\n".join(lines) if lines else "  nothing"
        bank_str = _format_wealth(bank_copper)

        return (
            f"Coins on hand:\n{carried_str}\n"
            f"  ({_format_wealth(carried_total)} total)\n\n"
            f"Bank balance: {bank_str}\n"
        )


class DepositCommand:
    """deposit <amount> <denomination> — deposit coins at a bank"""

    def execute(self, character, conn, args, session):
        if character.location_id != BANK_ROOM_ID:
            return "You need to be at a bank to deposit coins.\n"

        amount, denomination = _parse_args(args)
        if amount is None:
            return "Usage: deposit <amount> <denomination>\n  e.g. deposit 50 gold\n"

        copper_value = amount * COIN_VALUES[denomination]

        success = _remove_coins_from_character(conn, character.id, denomination, amount)
        if not success:
            label = denomination + ("s" if amount != 1 else "")
            return f"You don't have {amount} {label} to deposit.\n"

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE characters
                SET bank_copper = bank_copper + %s
                WHERE id = %s
            """,
                (copper_value, character.id),
            )

        recalculate_copper(conn, character.id)
        conn.commit()

        label = denomination + ("s" if amount != 1 else "")
        return f"You deposit {amount} {label} into your account.\n"


class WithdrawCommand:
    """withdraw <amount> <denomination> — withdraw coins from bank"""

    def execute(self, character, conn, args, session):
        if character.location_id != BANK_ROOM_ID:
            return "You need to be at a bank to withdraw coins.\n"

        amount, denomination = _parse_args(args)
        if amount is None:
            return (
                "Usage: withdraw <amount> <denomination>\n  e.g. withdraw 5 sovereign\n"
            )

        copper_cost = amount * COIN_VALUES[denomination]

        with conn.cursor() as cur:
            cur.execute(
                "SELECT bank_copper FROM characters WHERE id = %s", (character.id,)
            )
            bank_copper = cur.fetchone()[0]

        if bank_copper < copper_cost:
            return (
                f"You don't have enough in your account.\n"
                f"  Needed: {_format_wealth(copper_cost)}\n"
                f"  Balance: {_format_wealth(bank_copper)}\n"
            )

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE characters
                SET bank_copper = bank_copper - %s
                WHERE id = %s
            """,
                (copper_cost, character.id),
            )

        _add_coins_to_character(conn, character.id, denomination, amount)
        recalculate_copper(conn, character.id)
        conn.commit()

        label = denomination + ("s" if amount != 1 else "")
        return f"You withdraw {amount} {label} from your account.\n"
