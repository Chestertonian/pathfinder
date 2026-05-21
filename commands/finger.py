"""
commands/finger.py — FingerCommand

Usage:
    finger <name>

Looks up a character by name and displays their public profile.
Works whether the target is online or offline.
"""

from output import console, print_info, rule, blank, COLOR_STAT, COLOR_INFO, COLOR_FLAVOR


class FingerCommand:
    def execute(self, character, conn, args):
        if not args:
            return "Finger whom?"

        search = " ".join(args).lower()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.name, c.class, c.level,
                    c.is_logged_in, c.created_at,
                    l.name AS location_name
                FROM characters c
                JOIN locations l ON l.id = c.location_id
                WHERE LOWER(c.name) = %s
                """,
                (search,),
            )
            row = cur.fetchone()

        if row is None:
            return f"No character named '{search}' exists."

        name, char_class, level, is_logged_in, created_at, location_name = row

        rule()
        console.print(f"\n  {name}", style="bold gold1", end="")
        console.print(f"  —  {char_class.capitalize()}, Level {level}", style=COLOR_INFO)
        blank()

        if is_logged_in:
            console.print("  Currently online.", style="green")
        else:
            console.print("  Not logged in.", style="red")
            # last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M") if last_seen else "unknown"
            # console.print(f"  Last seen:  ", style=COLOR_INFO, end="")
            # console.print(last_seen_str, style=COLOR_STAT)

        console.print(f"  Played since:  ", style=COLOR_INFO, end="")
        console.print(created_at.strftime("%Y-%m-%d"), style=COLOR_STAT)

        blank()
        rule()

        return None