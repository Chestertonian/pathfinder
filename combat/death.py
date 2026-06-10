"""
combat/death.py — Shared death resolution

Called by both the combat scheduler and power handlers
when a combatant reaches 0 HP.
"""

from events import emit_event

def resolve_death(
    conn,
    dead_type: str,
    dead_id: int,
    killer_type: str,
    killer_id: int,
    location_id: int,
) -> None:
    """
    Full death resolution for any combatant.
    Handles NPC and player death, XP award, cleanup.
    """
    if dead_type == "character":
        _handle_player_death(conn, dead_id, location_id, killer_type, killer_id)
    else:
        _handle_npc_death(conn, dead_id, location_id)
        if killer_type == "character":
            _award_xp(conn, killer_id, dead_id, location_id)

    # Remove all combat rows involving the dead entity
    _delete_combats_for(conn, dead_type, dead_id)


def _handle_player_death(conn, character_id, location_id, killer_type, killer_id):
    from combat.scheduler import _render_personal_death, _render_death_announcement

    with conn.cursor() as cur:
        cur.execute("SELECT name FROM characters WHERE id = %s", (character_id,))
        row = cur.fetchone()
        victim_name = row[0].capitalize() if row else "Someone"

    # Get killer name
    if killer_type == "npc":
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nt.name FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.id = %s
                """,
                (killer_id,)
            )
            row = cur.fetchone()
        killer_name = row[0].capitalize() if row else "Something"
    else:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM characters WHERE id = %s", (killer_id,))
            row = cur.fetchone()
        killer_name = row[0].capitalize() if row else "Someone"

    with conn.cursor() as cur:
        # Drop items
        cur.execute(
            """
            UPDATE item_instances
            SET owner_type = 'location', owner_id = %s, equipped = FALSE
            WHERE owner_type = 'character' AND owner_id = %s
            """,
            (location_id, character_id),
        )

        # Send to Plane of the Dead
        cur.execute(
            """
            UPDATE characters
            SET location_id = 246, hp = 1,
                room_entered_at = NOW(), pending_look = TRUE
            WHERE id = %s
            """,
            (character_id,),
        )

    emit_event(
        conn,
        event_type="system",
        sender_id=character_id,
        message=_render_personal_death(killer_name),
    )

    emit_event(
        conn,
        event_type="global",
        sender_id=character_id,
        message=_render_death_announcement(killer_name, victim_name),
        color="red",
        use_border=False,
    )


def _handle_npc_death(conn, npc_id, location_id):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE npc_instances SET is_alive = FALSE, hp = 0, updated_at = NOW() WHERE id = %s",
            (npc_id,),
        )
        cur.execute(
            """
            UPDATE item_instances
            SET owner_type = 'location', owner_id = %s, equipped = FALSE
            WHERE owner_type = 'npc' AND owner_id = %s
            """,
            (location_id, npc_id),
        )


def _delete_combats_for(conn, entity_type: str, entity_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM active_combats
            WHERE (attacker_type = %s AND attacker_id = %s)
               OR (defender_type = %s AND defender_id = %s)
            """,
            (entity_type, entity_id, entity_type, entity_id),
        )
        
    
    
def _award_xp(conn, character_id: int, npc_id: int, location_id: int):
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

    hp_gain = max(1, 8 + mod(con) + (mod(str_) / 2))
    sp_gain = max(1, 4 + mod(int_) + (mod(wis) / 2))
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
        
        
# ------------------------------------------------------------------
# Render helpers
# ------------------------------------------------------------------


def _render_personal_death(killer_name: str) -> str:
    lines = [
        "",
        "  The world grows dim around you.",
        "",
        "  A cold silence falls.",
        "",
        f"  You have been slain by {killer_name}.",
        "",
        "  You find yourself in a strange, still place...",
        "",
    ]
    return "\n".join(lines)


def _render_death_announcement(killer_name: str, victim_name: str) -> str:
    width = 50
    border = "* " * (width // 2)
    message = f"{victim_name} has fallen, slain by {killer_name}."
    padded = message.center(width)

    return "\n".join([
        "",
        border,
        padded,
        border,
        "",
    ])


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



