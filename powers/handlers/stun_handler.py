"""
powers/handlers/headbutt.py — Headbutt

Usage:
    headbutt
    headbutt <target>

Dwarf racial power. Stuns the target, causing them to miss their
next attack. Works on NPCs and players.

Future: proper stun/status effect system hook.
"""

import random
from events import emit_event
from output import to_ansi


def execute(character, target, args, conn, session) -> None:

    if target is None:
        session.send("Headbutt whom?\n")
        return

    name = character.name.capitalize()
    target_name = target["name"].capitalize()

    # --- Room sees it ---
    emit_event(
        conn,
        event_type="combat",
        sender_id=character.id,
        location_id=character.location_id,
        message=to_ansi(
            f"[red]{name} lowers their head and slams into "
            f"{target_name} with a stunning headbutt![/red]"
        ),
    )

    # --- Attacker feedback ---
    session.send(
        to_ansi(
            f"[red]You lower your head and slam into {target_name} "
            f"with a stunning headbutt![/red]\n"
        )
    )

    # --- Target feedback ---
    if target["type"] == "player":
        emit_event(
            conn,
            event_type="system",
            sender_id=target["id"],
            message=to_ansi(
                f"[bright_red]{name} slams their head into yours. "
                f"Your vision swims — you stagger![/bright_red]"
            ),
        )

    # --- Stun effect ---
    # For NPCs: delete their next attack row temporarily
    # This is a placeholder until a proper status system exists
    if target["type"] == "npc":
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM active_combats
                WHERE attacker_type = 'npc'
                  AND attacker_id = %s
                  AND defender_type = 'character'
                  AND defender_id = %s
                """,
                (target["id"], character.id),
            )
        # Re-insert with a delay by updating started_at forward
        # so the scheduler skips it for one tick
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO active_combats
                    (attacker_type, attacker_id, defender_type,
                     defender_id, location_id, started_at)
                VALUES
                    ('npc', %s, 'character', %s, %s,
                     NOW() + INTERVAL '3 seconds')
                ON CONFLICT DO NOTHING
                """,
                (target["id"], character.id, character.location_id),
            )