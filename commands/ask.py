"""
commands/ask.py — AskCommand

Usage:
    ask <npc> about <topic>

Looks up a dialogue entry for the NPC and topic.
If found, displays the NPC's response.
If not found, a generic fallback.
"""

from events import emit_event


class AskCommand:
    def execute(self, character, conn, args, session):

        # Parse "ask <npc> about <topic>"
        if "about" not in args:
            return "Ask whom about what?"

        about_idx = args.index("about")
        npc_name_parts = args[:about_idx]
        topic_parts    = args[about_idx + 1:]

        if not npc_name_parts:
            return "Ask whom?"
        if not topic_parts:
            return "Ask about what?"

        npc_search = " ".join(npc_name_parts).lower()
        topic      = " ".join(topic_parts).lower()

        # Find NPC in room
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ni.id, nt.id, nt.name, nt.gender
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.location_id = %s
                  AND ni.is_alive = TRUE
                  AND LOWER(nt.name) LIKE %s
                ORDER BY ni.id ASC
                LIMIT 1
                """,
                (character.location_id, f"%{npc_search}%"),
            )
            row = cur.fetchone()

        if row is None:
            return f"You don't see '{npc_search}' here."

        npc_instance_id, npc_template_id, npc_name, npc_gender = row

        # Look up dialogue
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT response
                FROM dialogue
                WHERE npc_template_id = %s
                  AND LOWER(topic) = %s
                """,
                (npc_template_id, topic),
            )
            row = cur.fetchone()

        # Pronoun for fallback
        pronouns = {0: "they", 1: "he", 2: "she"}
        pronoun = pronouns.get(npc_gender, "they")

        if row is None:
            response_text = f"{npc_name.capitalize()} doesn't seem to know anything about that."
        else:
            response_text = f"{row[0]}"

        # Room event — others see the exchange
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name.capitalize()} asks {npc_name.capitalize()} about {topic}.",
        )

        # Personal response — only the asker sees the full reply
        session.send(f"\n{response_text}\n\n")

        return None