"""
threads/regen.py — Regen + world maintenance tick

Fires every 20 seconds.

Handles:
  - HP regeneration (out of combat only)
  - EP regeneration (always, rate varies)
  - SP regeneration (out of combat only)
  - NPC respawning (dead NPCs with a home room)
  - Stale combat cleanup (ghost combats from crashes)

Start once from server.py at boot:
    from threads.regen import start_regen_thread
    start_regen_thread(get_connection)
"""

import threading
import traceback
from db import get_connection

REGEN_TICK        = 20    # seconds between ticks

# Regen amounts per tick
HP_REGEN_COMBAT      = 2  # in combat
HP_REGEN_NORMAL      = 2  # out of combat, not in settlement
HP_REGEN_SETTLEMENT  = 5  # in settlement

EP_REGEN_COMBAT      = 2  # in combat
EP_REGEN_NORMAL      = 8  # default
EP_REGEN_SETTLEMENT  = 15 # in settlement

SP_REGEN_COMBAT      = 2  # in combat
SP_REGEN_NORMAL      = 3  # out of combat
SP_REGEN_SETTLEMENT  = 8  # in settlement

NPC_RESPAWN_SECONDS  = 120  # how long before a dead NPC respawns
STALE_COMBAT_SECONDS = 300   # how long before a combat is cleaned up


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def _regen_loop(conn_factory):
    while True:
        try:
            with conn_factory() as conn:
                _regen_players(conn)
                _respawn_npcs(conn)
                _cleanup_stale_combats(conn)
                conn.commit()
        except Exception:
            traceback.print_exc()

        threading.Event().wait(timeout=REGEN_TICK)


# ---------------------------------------------------------------------------
# Player regen
# ---------------------------------------------------------------------------

def _regen_players(conn):
    """
    Regen HP, EP, SP for all logged-in players.
    Rates depend on whether they're in combat and whether they're
    in a settlement.
    """
    with conn.cursor() as cur:

        # Get all logged-in players with their location flags
        # and whether they're currently in combat
        cur.execute(
            """
            SELECT
                c.id,
                c.hp, c.hp_max,
                c.power, c.power_max,
                c.endurance, c.endurance_max,
                l.is_settlement,
                EXISTS (
                    SELECT 1 FROM active_combats
                    WHERE (attacker_type = 'character' AND attacker_id = c.id)
                       OR (defender_type = 'character' AND defender_id = c.id)
                ) AS in_combat
            FROM characters c
            JOIN locations l ON l.id = c.location_id
            WHERE c.is_logged_in = TRUE
            """
        )
        players = cur.fetchall()

        for row in players:
            (
                char_id,
                hp, hp_max,
                sp, sp_max,
                ep, ep_max,
                is_settlement,
                in_combat,
            ) = row

            new_hp = hp
            new_sp = sp
            new_ep = ep

            # --- HP ---
            if in_combat:
                gain = HP_REGEN_COMBAT
            elif is_settlement:
                gain = HP_REGEN_SETTLEMENT                 
            else: 
                gain=HP_REGEN_NORMAL
            new_hp = min(hp_max, hp + gain)

            # --- SP ---
            if in_combat:
                gain = SP_REGEN_COMBAT
            elif is_settlement:
                gain = SP_REGEN_SETTLEMENT
            else:
                gain = SP_REGEN_NORMAL
            new_ep = min(sp_max, sp + gain)

            # --- EP ---
            if in_combat:
                gain = EP_REGEN_COMBAT
            elif is_settlement:
                gain = EP_REGEN_SETTLEMENT
            else:
                gain = EP_REGEN_NORMAL
            new_ep = min(ep_max, ep + gain)

            # Only write if something changed
            if new_hp != hp or new_sp != sp or new_ep != ep:
                cur.execute(
                    """
                    UPDATE characters
                    SET hp = %s, power = %s, endurance = %s
                    WHERE id = %s
                    """,
                    (new_hp, new_sp, new_ep, char_id),
                )


# ---------------------------------------------------------------------------
# NPC respawning
# ---------------------------------------------------------------------------

def _respawn_npcs(conn):
    """
    Respawn dead NPCs that have a home room and have been dead long enough.
    Respawn time is defined per npc_template (respawn_seconds column).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ni.id, ni.home_room_id, nt.hp_max, nt.respawn_seconds
            FROM npc_instances ni
            JOIN npc_templates nt ON nt.id = ni.npc_template_id
            WHERE ni.is_alive = FALSE
              AND ni.home_room_id IS NOT NULL
              AND NOW() - ni.updated_at > (nt.respawn_seconds || ' seconds')::interval
            """
        )
        dead_npcs = cur.fetchall()

        for npc_id, home_room_id, hp_max, _ in dead_npcs:
            cur.execute(
                """
                UPDATE npc_instances
                SET is_alive    = TRUE,
                    hp          = %s,
                    location_id = %s,
                    updated_at  = NOW()
                WHERE id = %s
                """,
                (hp_max, home_room_id, npc_id),
            )

# ---------------------------------------------------------------------------
# Stale combat cleanup
# ---------------------------------------------------------------------------

def _cleanup_stale_combats(conn):
    """
    Remove combat rows that haven't been updated in a while.
    These are ghost combats left over from crashes or disconnects.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM active_combats
            WHERE NOW() - started_at > INTERVAL '%s seconds'
            """,
            (STALE_COMBAT_SECONDS,),
        )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def start_regen_thread(conn_factory):
    """
    Start the regen thread. Call once from server.py at boot.
    """
    t = threading.Thread(
        target=_regen_loop,
        args=(conn_factory,),
        daemon=True,
        name="regen-thread",
    )
    t.start()
    return t