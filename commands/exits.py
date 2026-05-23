"""
commands/exits.py — ExitsCommand

Lists all visible exits from the character's current location.

Returns a string on error, None on success (matching command interface convention).

Needs some work.
"""


class ExitsCommand:
    def execute(self, character, conn, args, session):
        """
        character : the logged-in character object (has .location_id, .is_staff)
        conn      : active DB connection — used to query exits and location names
        args      : list of extra words typed after 'exits' (ignored)
        """

        with conn.cursor() as cur:

            # Staff see secret exits too; regular players do not.
            if character.is_staff:
                cur.execute(
                    """
                    SELECT e.direction, e.is_locked, e.is_secret,
                           e.description, l.name
                    FROM exits e
                    JOIN locations l ON l.id = e.to_location
                    WHERE e.from_location = %s
                    ORDER BY e.direction
                    """,
                    (character.location_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT e.direction, e.is_locked, e.is_secret,
                           e.description, l.name
                    FROM exits e
                    JOIN locations l ON l.id = e.to_location
                    WHERE e.from_location = %s
                      AND e.is_secret = FALSE
                    ORDER BY e.direction
                    """,
                    (character.location_id,),
                )

            exits = cur.fetchall()

        # ── Display ─────────────────────────────────────────────────────────
        session.send("-- Exits --")

        if not exits:
            session.send("There are no visible exits from here.\n")
            return None

        for direction, is_locked, is_secret, description, dest_name in exits:

            # Direction — left-padded so columns line up
            session.send(f"{direction.upper()}")

            if is_secret and character.is_staff:
                session.send("  [hidden]\n")

            session.send("\n")  # end the line


        return None  # success — no error message