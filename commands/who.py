"""
commands/who.py — WhoCommand

Lists all characters currently online, their class, and location name.

No emit_event() needed — this is a personal UI panel.
"""

from output import console, rule, print_info, blank, COLOR_STAT, COLOR_INFO


class WhoCommand:
    def execute(self, character, conn, args):
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

        rule("Who is Online")
        blank()

        if not rows:
            print_info("No one is online.")
        else:
            for name, char_class in rows:
                console.print(f"  {name:<20}", style="bold grey74", end="")
                console.print(f"the {char_class.capitalize():<12}\n", style=COLOR_STAT, end="")

        blank()
        console.print(
            f"  {len(rows)} player{'s' if len(rows) != 1 else ''} online.",
            style="grey54",
        )
        blank()
        rule()

        return None
