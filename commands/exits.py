"""
commands/exits.py — ExitsCommand

Lists all visible exits from the character's current location.

Returns a string on error, None on success (matching command interface convention).

Needs some work.
"""

from output import (
    console,
    print_info, rule, blank,
    COLOR_STAT, COLOR_INFO, COLOR_FLAVOR,
)


class ExitsCommand:
    def execute(self, character, conn, args):
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
        rule("Exits")

        if not exits:
            print_info("There are no visible exits from here.")
            rule()
            return None

        for direction, is_locked, is_secret, description, dest_name in exits:

            # Direction — left-padded so columns line up
            console.print(f"  {direction.upper():<8} ", style="bold grey74", end="")

            # Destination room name
            # console.print(dest_name, style=COLOR_STAT, end="")

            # Tags
            if is_locked:
                console.print("  [locked]", style="bold red3", end="")
            if is_secret and character.is_staff:
                console.print("  [hidden]", style="bold dark_orange", end="")

            console.print()  # end the line


        blank()
        rule()

        return None  # success — no error message