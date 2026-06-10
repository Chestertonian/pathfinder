"""
commands/powers.py — Power dispatcher

Handles all player power invocations.

Flow:
    1. Look up power in power_templates
    2. Check character has access (class/race/background)
    3. Check cooldown
    4. Check SP
    5. Resolve target if needed
    6. Initiate combat for offensive powers
    7. Delegate to handler
    8. Deduct SP, set cooldown

To add a new power:
    1. Insert a row into power_templates
    2. Write a handler in powers/handlers/<name>.py
    3. Register it in POWER_HANDLERS below
"""

from datetime import datetime, timezone

from db import get_connection
from events import emit_event
import powers.handlers.salute as salute_handler
import powers.handlers.slip as slip_handler
import powers.handlers.pray as pray_handler
import powers.handlers.maketorch as maketorch_handler
import powers.handlers.hawkwares as hawkwares_handler
import powers.handlers.beautician as beautician_handler
import powers.handlers.flourish as flourish_handler
import powers.handlers.ordernumber as ordernumber_handler
import powers.handlers.dyecast as dyecast_handler
import powers.handlers.tailor as tailor_handler
import powers.handlers.makeparchment as makeparchment_handler
import powers.handlers.slash as slash_handler


POWER_HANDLERS = {
    "salute":        salute_handler,
    "slip":          slip_handler,
    "pray":          pray_handler,
    "maketorch":     maketorch_handler,
    "hawkwares":     hawkwares_handler,
    "beautician":    beautician_handler,
    "flourish":      flourish_handler,
    "tailor":        tailor_handler,
    "dyecast":       dyecast_handler,
    "ordernumber":   ordernumber_handler,
    "makeparchment": makeparchment_handler,
    "slash":         slash_handler,
}


class PowerCommand:
    def __init__(self, power_name: str):
        self.power_name = power_name

    def execute(self, character, conn, args, session) -> str | None:

        # --- 1. Load power template ---
        power = _get_power(conn, self.power_name)
        if power is None:
            return f"Unknown power '{self.power_name}'."

        # --- 2. Check access ---
        LOCATION_POWER_OVERRIDES = {
            246: ["pray"],
        }
        allowed_in_location = LOCATION_POWER_OVERRIDES.get(character.location_id, [])
        if self.power_name not in allowed_in_location:
            if not _has_access(character, power):
                return "You don't know how to do that."

        # --- 3. Check cooldown ---
        remaining = _cooldown_remaining(conn, character.id, self.power_name)
        if remaining > 0:
            return f"You must wait before using {self.power_name} again."

        # --- 4. Check SP ---
        if character.power < power["sp_cost"]:
            return f"You don't have enough energy to do that."

        # --- 5. Resolve target ---
        target = None
        if power["target_type"] != "none":
            if args:
                target = _resolve_target(
                    conn, character, power["target_type"], args[:1], session
                )
                if target is None:
                    return None

            elif power["target_combat_auto"]:
                target = _resolve_combat_target(conn, character)
                if target is None:
                    if power["target_required"]:
                        session.send("You aren't in combat. Who is your target?\n")
                        return None

            elif power["target_required"]:
                session.send(f"{power['display_name']} requires a target.\n")
                return None

        # --- 6. Initiate combat for offensive powers ---
        if power["effect_type"] == "damage" and target is not None:
            _ensure_combat(conn, character, target)

        # --- 7. Delegate to handler ---
        handler = POWER_HANDLERS.get(self.power_name)
        if handler is None:
            return f"No handler implemented for '{self.power_name}'."

        handler.execute(character, target, args, conn, session)

        # --- 8. Deduct SP and set cooldown ---
        if power["sp_cost"] > 0:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE characters
                    SET power = GREATEST(0, power - %s)
                    WHERE id = %s
                    """,
                    (power["sp_cost"], character.id),
                )

        if power["cooldown_seconds"] > 0:
            _set_cooldown(conn, character.id, self.power_name,
                          power["cooldown_seconds"])

        conn.commit()
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_combat(conn, character, target) -> None:
    """
    Insert active_combats rows if not already fighting this target.
    Called automatically for all damage-type powers.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM active_combats
            WHERE attacker_type = 'character'
              AND attacker_id = %s
              AND defender_type = %s
              AND defender_id = %s
            """,
            (character.id, target["type"], target["id"]),
        )
        already_fighting = cur.fetchone() is not None

    if already_fighting:
        return

    with conn.cursor() as cur:
        # Player → target
        cur.execute(
            """
            INSERT INTO active_combats
                (attacker_type, attacker_id, defender_type, defender_id, location_id)
            VALUES ('character', %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (character.id, target["type"], target["id"], character.location_id),
        )

        # Target → player (only if not already retaliating)
        cur.execute(
            """
            SELECT id FROM active_combats
            WHERE attacker_type = %s
              AND attacker_id = %s
              AND defender_type = 'character'
            """,
            (target["type"], target["id"]),
        )
        if cur.fetchone() is None:
            cur.execute(
                """
                INSERT INTO active_combats
                    (attacker_type, attacker_id, defender_type, defender_id, location_id)
                VALUES (%s, %s, 'character', %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (target["type"], target["id"], character.id, character.location_id),
            )

    conn.commit()


def _get_power(conn, name: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT name, display_name, sp_cost, cooldown_seconds,
                   target_type, source_type, source_value, effect_type,
                   target_required, target_combat_auto
            FROM power_templates
            WHERE name = %s
            """,
            (name,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "name":               row[0],
        "display_name":       row[1],
        "sp_cost":            row[2],
        "cooldown_seconds":   row[3],
        "target_type":        row[4],
        "source_type":        row[5],
        "source_value":       row[6],
        "effect_type":        row[7],
        "target_required":    row[8],
        "target_combat_auto": row[9],
    }


def _has_access(character, power: dict) -> bool:
    source_type  = power["source_type"]
    source_value = power["source_value"].lower()

    if source_type == "class":
        return (character.char_class or "").lower() == source_value

    if source_type == "race":
        return (character.race or "").lower() == source_value

    if source_type == "background":
        return (character.background or "").lower() == source_value

    return False


def _cooldown_remaining(conn, character_id: int, power_name: str) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT expires_at FROM character_cooldowns
            WHERE character_id = %s AND power_name = %s
            """,
            (character_id, power_name),
        )
        row = cur.fetchone()

    if row is None:
        return 0.0

    expires_at = row[0]
    now = datetime.now(timezone.utc)

    if expires_at <= now:
        return 0.0

    return (expires_at - now).total_seconds()


def _set_cooldown(conn, character_id: int, power_name: str,
                  cooldown_seconds: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO character_cooldowns (character_id, power_name, expires_at)
            VALUES (%s, %s, NOW() + INTERVAL '%s seconds')
            ON CONFLICT (character_id, power_name)
            DO UPDATE SET expires_at = NOW() + INTERVAL '%s seconds'
            """,
            (character_id, power_name, cooldown_seconds, cooldown_seconds),
        )


def _resolve_target(conn, character, target_type: str,
                    args: list, session) -> dict | None:
    if not args:
        session.send("Who or what is your target?\n")
        return None

    search = " ".join(args).lower()

    if target_type in ("player", "any"):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name FROM characters
                WHERE location_id = %s
                  AND is_logged_in = TRUE
                  AND id != %s
                  AND LOWER(name) LIKE %s
                """,
                (character.location_id, character.id, f"%{search}%"),
            )
            row = cur.fetchone()
        if row:
            return {"type": "player", "id": row[0], "name": row[1]}

    if target_type in ("npc", "any"):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ni.id, nt.name
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.location_id = %s
                  AND ni.is_alive = TRUE
                  AND LOWER(nt.name) LIKE %s
                """,
                (character.location_id, f"%{search}%"),
            )
            row = cur.fetchone()
        if row:
            return {"type": "npc", "id": row[0], "name": row[1]}

    session.send(f"You don't see '{search}' here.\n")
    return None


def _resolve_combat_target(conn, character) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ac.defender_type, ac.defender_id,
                   COALESCE(nt.name, c.name) as name
            FROM active_combats ac
            LEFT JOIN npc_instances ni
                ON ac.defender_type = 'npc' AND ni.id = ac.defender_id
            LEFT JOIN npc_templates nt
                ON nt.id = ni.npc_template_id
            LEFT JOIN characters c
                ON ac.defender_type = 'character' AND c.id = ac.defender_id
            WHERE ac.attacker_type = 'character'
              AND ac.attacker_id = %s
            LIMIT 1
            """,
            (character.id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "type": row[0],
        "id":   row[1],
        "name": row[2],
    }