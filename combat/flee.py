"""
commands/flee.py — FleeCommand

Picks a random exit from the current room, moves the player there,
and removes them from all active combats.

The NPC remains aggressive (its combat rows stay in active_combats
so aggro logic can use them later).
"""

import random

from events import emit_event
from output import print_info


class FleeCommand:
    def execute(self, character, conn, args):

        with conn.cursor() as cur:

            # Check if the character is actually in combat
            cur.execute(
                """
                SELECT id FROM active_combats
                WHERE (attacker_type = 'character' AND attacker_id = %s)
                   OR (defender_type = 'character' AND defender_id = %s)
                LIMIT 1
                """,
                (character.id, character.id),
            )
            if cur.fetchone() is None:
                return "You aren't in combat."

            # Get all available exits from the current room
            cur.execute(
                """
                SELECT to_location, direction
                FROM exits
                WHERE from_location = %s
                  AND is_locked = FALSE
                """,
                (character.location_id,),
            )
            exits = cur.fetchall()

            if not exits:
                return "You can't flee — there's nowhere to go!"

            # Pick a random exit
            to_location, direction = random.choice(exits)

            # Remove player from all active combats (both attacker and defender rows)
            cur.execute(
                """
                DELETE FROM active_combats
                WHERE attacker_type = 'character' AND attacker_id = %s
                """,
                (character.id,),
            )

            # NPC counter-attack rows stay — NPC remains aggressive
            # (defender rows where character is the defender are left intact
            #  for future aggro system to use)
            cur.execute(
                """
                DELETE FROM active_combats
                WHERE defender_type = 'character' AND defender_id = %s
                """,
                (character.id,),
            )

            # Move the player
            cur.execute(
                "UPDATE characters SET location_id = %s WHERE id = %s",
                (to_location, character.id),
            )

        conn.commit()

        # Tell the old room the player fled
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} flees to the {direction}!",
            color="red",
            use_border=False,
        )

        # Update character's location in memory
        character.location_id = to_location

        print_info(f"You flee to the {direction}!")

        return None
