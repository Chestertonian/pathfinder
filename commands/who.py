"""
commands/who.py — WhoCommand

Lists all characters currently online, their class, and location name.

No emit_event() needed — this is a personal UI panel.
"""


class WhoCommand:
    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name, c.class
                FROM characters c
                WHERE c.is_logged_in = TRUE
                ORDER BY c.name ASC
                """,
            )
            rows = cur.fetchall()

        session.send("======== Who is Online ========")
        session.send("\n\n")

        if not rows:
            session.send("No one is online.\n")
        else:
            for name, char_class in rows:
                session.send(f"  {name:<20}")
                session.send(f"the {char_class.capitalize():<12}\n")

        session.send(' ')
        session.send(
            f"  {len(rows)} player{'s' if len(rows) != 1 else ''} online.\n",
        )
        session.send("===============================\n")

        return None
