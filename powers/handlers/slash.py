"""
powers/handlers/slash.py — Slash

Fighter power. A powerful strike dealing 1d10 + (level/3) damage.
4 second windup before damage resolves.

No miss — always hits.
Target: NPC or player.
"""

import threading
import random

from events import emit_event
from db import get_connection
from combat.death import resolve_death


def execute(character, target, args, conn, session) -> None:

    if target is None:
        session.send("Slash whom?\n")
        return

    target_name = target["name"].capitalize()
    actor_name  = character.name.capitalize()

    # --- Windup messages ---

    # Room sees preparation
    emit_event(
        conn,
        event_type="combat",
        sender_id=character.id,
        location_id=character.location_id,
        message=f"{actor_name} prepares to slash {target_name}.",
    )

    # Attacker sees personal version
    session.send(f"You prepare to slash {target_name}.\n")

    # Target sees personal version (players only)
    if target["type"] == "player":
        emit_event(
            conn,
            event_type="system",
            sender_id=target["id"],
            message=f"{actor_name} prepares to slash you.",
        )

    
    # --- Schedule resolution after 4 seconds ---
    t = threading.Timer(
        4.0,
        _resolve_slash,
        args=(character.id, target["type"], target["id"], character.location_id),
    )
    t.daemon = True
    t.start()


def _resolve_slash(character_id: int, target_type: str, target_id: int, location_id: int) -> None:
    """
    Fires 4 seconds after windup.
    Loads fresh state from DB — character and target may have moved or died.
    """
    with get_connection() as conn:

        # Reload attacker
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, level, location_id FROM characters WHERE id = %s",
                (character_id,)
            )
            row = cur.fetchone()

        if row is None:
            return  # attacker logged off

        actor_name, actor_level, actor_location = row

        # Verify attacker is still in same room
        if actor_location != location_id:
            return  # attacker left the room

        # Reload target and verify still alive and in same room
        if target_type == "npc":
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT nt.name, ni.hp, ni.location_id, nt.defense
                    FROM npc_instances ni
                    JOIN npc_templates nt ON nt.id = ni.npc_template_id
                    WHERE ni.id = %s AND ni.is_alive = TRUE
                    """,
                    (target_id,)
                )
                row = cur.fetchone()

            if row is None:
                return  # target already dead

            target_name, target_hp, target_location, armor = row

        else:  # player
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT name, hp, location_id
                    FROM characters
                    WHERE id = %s AND is_logged_in = TRUE
                    """,
                    (target_id,)
                )
                row = cur.fetchone()

            if row is None:
                return  # target logged off

            target_name, target_hp, target_location = row
            armor = 0  # could load equipped armor here later

        # Target must still be in same room
        if target_location != location_id:
            return

        # --- Calculate damage ---
        damage = random.randint(1, 10) + (actor_level // 3)
        damage = max(1, damage - armor)
        new_hp = max(0, target_hp - damage)

        # --- Apply damage ---
        if target_type == "npc":
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE npc_instances SET hp = %s WHERE id = %s",
                    (new_hp, target_id)
                )
        else:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE characters SET hp = %s WHERE id = %s",
                    (new_hp, target_id)
                )

        conn.commit()

        target_name_cap = target_name.capitalize()
        actor_name_cap  = actor_name.capitalize()

        # --- Room sees the hit ---
        emit_event(
            conn,
            event_type="combat",
            sender_id=character_id,
            location_id=location_id,
            message=f"{actor_name_cap} slashes into {target_name_cap} for {damage}!",
        )

        # --- Attacker personal message ---
        # Use system event to reach the attacker
        emit_event(
            conn,
            event_type="system",
            sender_id=character_id,
            message=f"You slash into {target_name_cap} for {damage} damage!",
        )

        # --- Target personal message (players only) ---
        if target_type == "player":
            emit_event(
                conn,
                event_type="system",
                sender_id=target_id,
                message=f"{actor_name_cap} slashes into you for {damage} damage!",
            )

        if new_hp <= 0:
            emit_event(
                conn,
                event_type="combat",
                sender_id=character_id,
                location_id=location_id,
                message=f"{target_name.capitalize()} has been slain.",
            )
            resolve_death(
                conn,
                dead_type=target_type,
                dead_id=target_id,
                killer_type="character",
                killer_id=character_id,
                location_id=location_id,
            )