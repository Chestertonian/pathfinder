"""
combat/scheduler.py — Global combat scheduler

One thread. Ticks every 3 seconds. Processes all active combats in DB.

Multiparty model:
    Each row in active_combats is one directional attack relationship.
    Player A vs NPC A = two rows (A→NPC, NPC→A)
    Player B joins  = one row  (B→NPC)
    NPC only retaliates against its original attacker.

Ability hooks:
    Each class ability lives in combat/abilities/<name>.py
    and exposes a single use(attacker, defender, conn) function.
    The scheduler calls attacker_ability(attacker, defender, conn)
    once per tick — returns None for now (no abilities implemented).

Start at boot:
    from combat.scheduler import CombatScheduler
    scheduler = CombatScheduler()
    scheduler.start()
"""

import threading
import traceback

from db import get_connection
from events import emit_event
from combat.resolver import roll_d20, calculate_damage, stat_modifier

COMBAT_TICK = 3  # seconds


class CombatScheduler:

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._tick_loop,
            daemon=True,
            name="combat-scheduler",
        )

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=COMBAT_TICK + 1)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _tick_loop(self):
        while not self._stop_event.is_set():
            try:
                self._process_all_combats()
            except Exception:
                traceback.print_exc()
            self._stop_event.wait(timeout=COMBAT_TICK)

    # ------------------------------------------------------------------
    # Process all active combats
    # ------------------------------------------------------------------

    def _process_all_combats(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, attacker_type, attacker_id,
                           defender_type, defender_id, location_id
                    FROM active_combats
                    """
                )
                combats = cur.fetchall()

            for row in combats:
                combat_id, att_type, att_id, def_type, def_id, location_id = row
                try:
                    self._process_one(
                        conn, combat_id,
                        att_type, att_id,
                        def_type, def_id,
                        location_id,
                    )
                except Exception:
                    traceback.print_exc()

            conn.commit()

    # ------------------------------------------------------------------
    # Process one combat row (one directional attack)
    # ------------------------------------------------------------------

    def _process_one(
        self, conn,
        combat_id,
        att_type, att_id,
        def_type, def_id,
        location_id,
    ):
        attacker = _load_combatant(conn, att_type, att_id)
        defender = _load_combatant(conn, def_type, def_id)

        # Either combatant missing or already dead — clean up
        if attacker is None or defender is None:
            _delete_combat(conn, combat_id)
            return

        if attacker["hp"] <= 0 or defender["hp"] <= 0:
            _delete_combat(conn, combat_id)
            return

        # --- Resolve attack ---
        damage, died = self._resolve_attack(conn, location_id, attacker, defender)

        if died:
            self._handle_death(
                conn,
                def_type, def_id,
                att_type, att_id,
                location_id,
                combat_id,
            )

    # ------------------------------------------------------------------
    # Resolve one attack, return (damage, defender_died)
    # ------------------------------------------------------------------

    def _resolve_attack(self, conn, location_id, attacker, defender) -> tuple[int, bool]:
        acc_mod = stat_modifier(attacker["dexterity"])
        _, tier = roll_d20(acc_mod, skill_mod=0)

        damage = calculate_damage(
            damage_min=attacker["damage_min"],
            damage_max=attacker["damage_max"],
            stat_mod=stat_modifier(attacker["strength"]),
            level=attacker["level"],
            tier=tier,
            armor=defender["armor"],
        )

        new_hp = max(0, defender["hp"] - damage)
        _set_hp(conn, defender["type"], defender["id"], new_hp)

        if damage == 0:
            message = f"{attacker['name']} misses {defender['name']}."
        else:
            message = f"{attacker['name']} hits {defender['name']} for {damage} damage."

        # sender_id: only set if attacker is a character (room events need it)
        sender_id = (
            attacker["id"] if attacker["type"] == "character"
            else defender["id"] if defender["type"] == "character"
            else None
        )

        emit_event(
            conn,
            event_type="combat",
            sender_id=sender_id,
            location_id=location_id,
            message=message,
            color="red3",
            use_border=False,
        )
        

        # --- Ability hook (placeholder) ---
        # When abilities are implemented, import and call here:
        # ability_result = use_ability(attacker, defender, conn)

        return damage, new_hp <= 0

    # ------------------------------------------------------------------
    # Handle death
    # ------------------------------------------------------------------

    def _handle_death(
        self, conn,
        dead_type, dead_id,
        killer_type, killer_id,
        location_id,
        combat_id,
    ):
        dead = _load_combatant(conn, dead_type, dead_id)
        name = dead["name"] if dead else "Someone"

        emit_event(
            conn,
            event_type="combat",
            sender_id=killer_id if killer_type == "character" else None,
            location_id=location_id,
            message=f"{name} has been slain.",
            color="bold red3",
            use_border=False,
        )

        if dead_type == "character":
            self._handle_player_death(conn, dead_id, location_id)
        else:
            self._handle_npc_death(conn, dead_id, location_id)
            
            if killer_type == "character":
                self._award_xp(conn, killer_id, dead_id, location_id)


        # Remove ALL combat rows involving this entity
        _delete_combats_for(conn, dead_type, dead_id)

    def _handle_player_death(self, conn, character_id, location_id):
        with conn.cursor() as cur:
            # Drop all items at death location
            cur.execute(
                """
                UPDATE item_instances
                SET owner_type = 'location',
                    owner_id   = %s,
                    equipped   = FALSE
                WHERE owner_type = 'character'
                  AND owner_id   = %s
                """,
                (location_id, character_id),
            )

            # Find nearest settlement to respawn at
            cur.execute(
                """
                SELECT id FROM locations
                WHERE is_settlement = TRUE
                ORDER BY id ASC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            respawn_id = row[0] if row else 1

            cur.execute(
                """
                UPDATE characters
                SET location_id = %s,
                    hp = 1
                WHERE id = %s
                """,
                (respawn_id, character_id),
            )

        emit_event(
            conn,
            event_type="global",
            sender_id=character_id,
            message=f"Someone died!",
            color="bold red3",
            use_border=True,
        )

    def _handle_npc_death(self, conn, npc_id, location_id):
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE npc_instances
                SET is_alive = FALSE, hp = 0, updated_at = NOW()
                WHERE id = %s
                """,
                (npc_id,),
            )

            # Drop NPC inventory at location
            cur.execute(
                """
                UPDATE item_instances
                SET owner_type = 'location',
                    owner_id   = %s,
                    equipped   = FALSE
                WHERE owner_type = 'npc'
                  AND owner_id   = %s
                """,
                (location_id, npc_id),
            )
    def _award_xp(self, conn, character_id: int, npc_id: int, location_id: int):
        """Award XP to a character for killing an NPC. Level up if threshold met."""

        # Get XP reward from the template
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nt.xp
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.id = %s
                """,
                (npc_id,),
            )
            row = cur.fetchone()

        if row is None or row[0] == 0:
            return

        xp_reward = row[0]

        with conn.cursor() as cur:
            # Fetch current xp and level
            cur.execute(
                "SELECT xp, level FROM characters WHERE id = %s",
                (character_id,),
            )
            row = cur.fetchone()

        if row is None:
            return

        current_xp, current_level = row
        new_xp = current_xp + xp_reward

        # Check for level up
        new_level = current_level
        while new_xp >= _xp_required(new_level):
            new_xp -= _xp_required(new_level)
            new_level += 1

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE characters SET xp = %s, level = %s WHERE id = %s",
                (new_xp, new_level, character_id),
            )

        # Notify player of XP gain
        emit_event(
            conn,
            event_type="system",
            sender_id=character_id,
            message=f"You gain {xp_reward} XP.",
        )

        # Notify player of level up
        if new_level > current_level:
                # Apply stat gains for each level gained
                for _ in range(new_level - current_level):
                    _apply_level_up_gains(conn, character_id)

                emit_event(
                    conn,
                    event_type="system",
                    sender_id=character_id,
                    message=f"You have reached level {new_level}!",
                )


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------

def _load_combatant(conn, entity_type: str, entity_id: int) -> dict | None:
    with conn.cursor() as cur:
        if entity_type == "character":
            cur.execute(
                """
                SELECT c.id, c.name, c.hp, c.level,
                       c.strength, c.dexterity,
                       COALESCE(SUM(at.defense), 0)    AS armor,
                       COALESCE(MAX(wt.damage_min), 1) AS damage_min,
                       COALESCE(MAX(wt.damage_max), 4) AS damage_max
                FROM characters c
                LEFT JOIN item_instances ii
                    ON ii.owner_type = 'character'
                   AND ii.owner_id   = c.id
                   AND ii.equipped   = TRUE
                LEFT JOIN item_templates it  ON it.id  = ii.item_template_id
                LEFT JOIN armor_templates at ON at.item_template_id = it.id
                LEFT JOIN weapon_templates wt ON wt.item_template_id = it.id
                WHERE c.id = %s
                GROUP BY c.id
                """,
                (entity_id,),
            )
        else:  # npc
            cur.execute(
                """
                SELECT ni.id, nt.name, ni.hp, 1 AS level,
                       10 AS strength, 10 AS dexterity,
                       nt.defense   AS armor,
                       nt.damage_min,
                       nt.damage_max
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.id = %s
                  AND ni.is_alive = TRUE
                """,
                (entity_id,),
            )

        row = cur.fetchone()

    if row is None:
        return None

    id_, name, hp, level, strength, dexterity, armor, damage_min, damage_max = row

    return {
        "type":       entity_type,
        "id":         id_,
        "name":       name,
        "hp":         hp,
        "level":      level,
        "strength":   strength,
        "dexterity":  dexterity,
        "armor":      armor,
        "damage_min": damage_min,
        "damage_max": damage_max,
    }


def _set_hp(conn, entity_type: str, entity_id: int, new_hp: int):
    with conn.cursor() as cur:
        if entity_type == "character":
            cur.execute(
                "UPDATE characters SET hp = %s WHERE id = %s",
                (new_hp, entity_id),
            )
        else:
            cur.execute(
                "UPDATE npc_instances SET hp = %s WHERE id = %s",
                (new_hp, entity_id),
            )


def _delete_combat(conn, combat_id: int):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM active_combats WHERE id = %s",
            (combat_id,),
        )


def _delete_combats_for(conn, entity_type: str, entity_id: int):
    """Remove all combat rows involving this entity (on death or flee)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM active_combats
            WHERE (attacker_type = %s AND attacker_id = %s)
               OR (defender_type = %s AND defender_id = %s)
            """,
            (entity_type, entity_id, entity_type, entity_id),
        )
        
def _xp_required(level: int) -> int:
    """
    XP needed to level up from this level.
    Exponential curve — gets steep fast at high levels.

    Examples:
        level 1  →  100 XP
        level 2  →  250 XP
        level 5  →  1250 XP
        level 10 →  5000 XP
    """
    BASE = 1000
    K    = 2.3
    return int(BASE * (level ** K))


def _apply_level_up_gains(conn, character_id: int) -> None:
    """
    Apply HP, SP, and EP gains on level up.

    HP = base 8 + CON mod + 1/2 STR mod (minimum 1)
    SP = base 8 + INT mod + 1/2 WIS mod (minimum 1)
    EP = flat 10
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT constitution, intelligence, strength, wisdom,
                   hp_max, power_max, endurance_max
            FROM characters
            WHERE id = %s
            """,
            (character_id,),
        )
        row = cur.fetchone()

    if row is None:
        return

    con, int_, str_, wis, hp_max, sp_max, ep_max = row

    def mod(stat):
        return (stat - 10) // 2

    hp_gain = max(1, 8 + mod(con) + (mod(str_)/2))
    sp_gain = max(1, 4 + mod(int_) + (mod(wis)/2))
    ep_gain = 10

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE characters
            SET hp_max        = hp_max + %s,
                hp            = hp + %s,
                power_max     = power_max + %s,
                power         = power + %s,
                endurance_max = endurance_max + %s,
                endurance     = endurance + %s
            WHERE id = %s
            """,
            (
                hp_gain, hp_gain,
                sp_gain, sp_gain,
                ep_gain, ep_gain,
                character_id,
            ),
        )