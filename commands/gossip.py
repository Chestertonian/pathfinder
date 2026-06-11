# commands/gossip.py

import re
import random

# Mara's npc_template_id
MARA_TEMPLATE_ID = 6

class GossipCommand:
    """
    gossip <message>  — whisper gossip to Mara (replaces your previous entry)
    gossip            — Mara tells you a random piece of gossip
    """

    def execute(self, character, conn, args, session):
        if not self._mara_present(character, conn):
            session.send("Mara doesn't seem to be around.\n")
            return

        if args:
            self._submit(character, conn, args, session)
        else:
            self._receive(character, conn, session)


    def _submit(self, character, conn, args, session):
        message = " ".join(args).strip()

        if not message:
            session.send("Gossip about what?\n")
            return

        # Check if the player mentioned themselves by whole word (case-insensitive)
        # \b means "word boundary" — so "Ed" won't match inside "Edward"
        name_pattern = re.compile(rf"\b{re.escape(character.name)}\b", re.IGNORECASE)
        self_mentioned = bool(name_pattern.search(message))

        # Upsert: insert, but if this player already has a row for this NPC,
        # replace the message and reset the timestamp instead of erroring
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO npc_gossip (npc_template_id, author_id, message, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (npc_template_id, author_id)
                DO UPDATE SET message = EXCLUDED.message,
                              created_at = NOW()
            """, (MARA_TEMPLATE_ID, character.id, message))
        conn.commit()

        if self_mentioned:
            session.send(
                "Mara nods slowly and tucks the information away, though she looks "
                "a little skeptical.\n"
            )
        else:
            session.send(
                "You lean in close. Mara listens carefully and gives a small nod.\n"
            )


    def _receive(self, character, conn, session):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT g.message, c.name AS author_name
                FROM npc_gossip g
                JOIN characters c ON c.id = g.author_id
                WHERE g.npc_template_id = %s
                  AND g.created_at > NOW() - INTERVAL '7 days'
                ORDER BY RANDOM()
                LIMIT 1
            """, (MARA_TEMPLATE_ID,))
            row = cur.fetchone()

        if not row:
            session.send(
                "Mara shrugs and says, \"I haven't heard anything worth repeating.\"\n"
            )
            return

        message, author_name = row

        # Append disclaimer if the author mentioned themselves
        name_pattern = re.compile(rf"\b{re.escape(author_name)}\b", re.IGNORECASE)
        disclaimer = ""
        if name_pattern.search(message):
            disclaimer = f" I don't know how reliable this is because {author_name} told me about it."

        session.send(
            f"Mara turns to you and says, \"I heard that {message}.{disclaimer}\"\n"
        )
        
    def _mara_present(self, character, conn):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM npc_instances
                WHERE npc_template_id = %s
                AND location_id = %s
                AND is_alive = TRUE
                LIMIT 1
            """, (MARA_TEMPLATE_ID, character.location_id))
            return cur.fetchone() is not None


