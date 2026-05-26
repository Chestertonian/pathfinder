"""
commands/flee.py — FleeCommand
"""

import random
from events import emit_event


class FleeCommand:
    def execute(self, character, conn, args, session):

        with conn.cursor() as cur:
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

            to_location, direction = random.choice(exits)

            cur.execute(
                """
                DELETE FROM active_combats
                WHERE attacker_type = 'character' AND attacker_id = %s
                """,
                (character.id,),
            )
            cur.execute(
                """
                DELETE FROM active_combats
                WHERE defender_type = 'character' AND defender_id = %s
                """,
                (character.id,),
            )
            cur.execute(
                "UPDATE characters SET location_id = %s WHERE id = %s",
                (to_location, character.id),
            )

        conn.commit()

        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} flees to the {direction}!",
        )

        character.location_id = to_location
        session.send(f"You flee to the {direction}!\n")  # CHANGED
        return None