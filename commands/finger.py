"""
commands/finger.py — FingerCommand

Usage:
    finger <name>

Looks up a character by name and displays their public profile.
Works whether the target is online or offline.
"""


class FingerCommand:
    def execute(self, character, conn, args, session):
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

        lines = []
        lines.append("-" * 40)
        lines.append(f"\n  {name}\n")
        lines.append(f"  {char_class.capitalize()}, Level {level}")
        lines.append("")

        if is_logged_in:
            lines.append("  Currently online.")
        else:
            lines.append("  Not logged in.")

        lines.append(f"  Played since:  {created_at.strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("-" * 40)

        session.send("\n".join(lines) + "\n")
        return None