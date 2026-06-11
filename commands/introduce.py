# commands/introduce.py

from events import emit_event
from social import visible_name, already_introduced


class IntroduceCommand:
    """
    introduce <player>

    Introduces yourself to another player in the same room.
    They will now see your real name. This is one-directional.
    """

    def execute(self, character, conn, args, session):
        if not args:
            session.send("Introduce yourself to whom?\n")
            return

        target_name = args[0].capitalize()

        # Find target in same room
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, gender, race
                FROM characters
                WHERE location_id = %s
                  AND is_logged_in = TRUE
                  AND id != %s
                  AND LOWER(name) = LOWER(%s)
            """, (character.location_id, character.id, target_name))
            row = cur.fetchone()

        if not row:
            session.send(f"You don't see anyone called '{target_name}' here.\n")
            return

        target_id, target_name_real, _, _ = row

        if already_introduced(character.id, target_id, conn):
            session.send(f"You have already introduced yourself to {target_name_real}.\n")
            return

        # Insert the introduction (one direction: you → target)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO character_introductions (character_id, known_character_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (character.id, target_id))
        conn.commit()

        # You see this
        session.send(f"You introduce yourself to {target_name_real}.\n")

        # Target sees this (system event — private)
        emit_event(conn,
            event_type="system",
            message=f"{character.name} introduces themselves to you.\n",
            sender_id=character.id,
            recipient_character_id=target_id,
        )

        # Room sees a vague version
        emit_event(conn,
            event_type="room",
            message=f"{character.name} introduces themselves to someone.\n",
            sender_id=character.id,
            location_id=character.location_id,
        )