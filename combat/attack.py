"""
commands/attack.py — AttackCommand

Usage:
    attack <npc name>

Initiates combat by inserting a row into active_combats.
If the NPC is already in combat, joins the existing combat (split XP later).
The NPC will only counter-attack its original attacker.
"""

from events import emit_event
from output import print_info


class AttackCommand:
    def execute(self, character, conn, args, session):
        if not args:
            return "Attack what?"

        search = " ".join(args).lower()

        with conn.cursor() as cur:

            # Find the NPC in the current room
            cur.execute(
                """
                SELECT ni.id, nt.name
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.location_id = %s
                  AND ni.is_alive = TRUE
                  AND LOWER(nt.name) LIKE %s
                ORDER BY ni.id ASC
                LIMIT 1
                """,
                (character.location_id, f"%{search}%"),
            )
            row = cur.fetchone()

            if row is None:
                return "You don't see that here."

            npc_id, npc_name = row

            # Check if this character is already fighting this NPC
            cur.execute(
                """
                SELECT id FROM active_combats
                WHERE attacker_type = 'character'
                  AND attacker_id   = %s
                  AND defender_type = 'npc'
                  AND defender_id   = %s
                """,
                (character.id, npc_id),
            )
            if cur.fetchone():
                return f"You are already fighting {npc_name}."

            # Check if NPC already has a counter-attacker (original attacker)
            # If not, this player becomes the one the NPC fights back against
            cur.execute(
                """
                SELECT id FROM active_combats
                WHERE attacker_type = 'npc'
                  AND attacker_id   = %s
                  AND defender_type = 'character'
                """,
                (npc_id,),
            )
            npc_already_retaliating = cur.fetchone() is not None

            # Register player attacking NPC
            cur.execute(
                """
                INSERT INTO active_combats
                    (attacker_type, attacker_id, defender_type, defender_id, location_id)
                VALUES
                    ('character', %s, 'npc', %s, %s)
                """,
                (character.id, npc_id, character.location_id),
            )

            # If NPC isn't already fighting back, register its retaliation
            if not npc_already_retaliating:
                cur.execute(
                    """
                    INSERT INTO active_combats
                        (attacker_type, attacker_id, defender_type, defender_id, location_id)
                    VALUES
                        ('npc', %s, 'character', %s, %s)
                    """,
                    (npc_id, character.id, character.location_id),
                )

        conn.commit()

        # Room event
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} attacks {npc_name}!",
            color="red3",
            use_border=False,
        )

        print_info(f"You attack {npc_name}!")

        return None
