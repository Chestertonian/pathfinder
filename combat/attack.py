"""
commands/attack.py — AttackCommand
"""

from events import emit_event
from targeting import parse_target, resolve_npc_targets


class AttackCommand:
    def execute(self, character, conn, args, session):
        if not args:
            return "Attack what?"

        # --- Safe room check (settlements allow PvP, safe non-settlements don't) ---
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_safe, is_settlement FROM locations WHERE id = %s",
                (character.location_id,),
            )
            row = cur.fetchone()

        if row:
            is_safe, is_settlement = row
            if is_safe and not is_settlement:
                return "You cannot attack here."

        # --- Try NPC first ---
        parsed  = parse_target(args)
        targets = resolve_npc_targets(parsed, character.location_id, conn)

        if targets:
            npc_id, npc_name = targets[0]

            with conn.cursor() as cur:
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

                cur.execute(
                    """
                    INSERT INTO active_combats
                        (attacker_type, attacker_id, defender_type, defender_id, location_id)
                    VALUES ('character', %s, 'npc', %s, %s)
                    """,
                    (character.id, npc_id, character.location_id),
                )

                if not npc_already_retaliating:
                    cur.execute(
                        """
                        INSERT INTO active_combats
                            (attacker_type, attacker_id, defender_type, defender_id, location_id)
                        VALUES ('npc', %s, 'character', %s, %s)
                        """,
                        (npc_id, character.id, character.location_id),
                    )

            conn.commit()

            emit_event(
                conn,
                event_type="combat",
                sender_id=character.id,
                location_id=character.location_id,
                message=f"{character.name.capitalize()} attacks {npc_name}!",
            )

            session.send(f"You attack {npc_name}!\n")
            return None

        # --- Try player ---
        search = " ".join(args).lower()
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

        if row is None:
            return "You don't see that here."

        target_id, target_name = row

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM active_combats
                WHERE attacker_type = 'character'
                  AND attacker_id   = %s
                  AND defender_type = 'character'
                  AND defender_id   = %s
                """,
                (character.id, target_id),
            )
            if cur.fetchone():
                return f"You are already fighting {target_name.capitalize()}."

            cur.execute(
                """
                SELECT id FROM active_combats
                WHERE attacker_type = 'character'
                  AND attacker_id   = %s
                  AND defender_type = 'character'
                """,
                (target_id,),
            )
            already_retaliating = cur.fetchone() is not None

            cur.execute(
                """
                INSERT INTO active_combats
                    (attacker_type, attacker_id, defender_type, defender_id, location_id)
                VALUES ('character', %s, 'character', %s, %s)
                """,
                (character.id, target_id, character.location_id),
            )

            if not already_retaliating:
                cur.execute(
                    """
                    INSERT INTO active_combats
                        (attacker_type, attacker_id, defender_type, defender_id, location_id)
                    VALUES ('character', %s, 'character', %s, %s)
                    """,
                    (target_id, character.id, character.location_id),
                )

        conn.commit()

        emit_event(
            conn,
            event_type="combat",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name.capitalize()} attacks {target_name.capitalize()}!",
        )

        # Personal message to target
        emit_event(
            conn,
            event_type="system",
            sender_id=target_id,
            message=f"{character.name.capitalize()} attacks you!",
        )

        session.send(f"You attack {target_name.capitalize()}!\n")
        return None