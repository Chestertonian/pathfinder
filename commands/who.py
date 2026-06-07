"""
commands/who.py — WhoCommand

Lists all characters currently online with race, guild, and title.
"""


class WhoCommand:
    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name, c.race, c.class, t.name AS title
                FROM characters c
                LEFT JOIN titles t ON t.id = c.title_id
                WHERE c.is_logged_in = TRUE
                ORDER BY c.name ASC
                """,
            )
            rows = cur.fetchall()

        lines = []
        lines.append("\n======== Who is Online ========\n")

        if not rows:
            lines.append("  No one is online.\n")
        else:
            for name, race, char_class, title in rows:
                race_class = f"{race.capitalize()} {char_class.capitalize()}" if char_class else race.capitalize()
                identity   = f"{name.capitalize()}, {race_class}"
                if title:
                    line = f"  {identity:<35} {title}"
                else:
                    line = f"  {identity}"
                lines.append(line)

        lines.append("")
        lines.append(f"  {len(rows)} player{'s' if len(rows) != 1 else ''} online.")
        lines.append("===============================\n")

        session.send("\n".join(lines))
        return None