class PlayersCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You don't have permission to do that."
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name, c.class, c.level, l.name
                FROM characters c
                JOIN locations l ON l.id = c.location_id
                WHERE c.is_logged_in = TRUE
                ORDER BY c.name ASC
                """
            )
            rows = cur.fetchall()
        if not rows:
            return "No players online."
        lines = [f"  {'Name':<20} {'Class':<10} {'Lvl':<5} Location"]
        lines.append("  " + "-" * 50)
        for name, cls, level, loc in rows:
            lines.append(f"  {name.capitalize():<20} {cls.capitalize():<10} {level:<5} {loc}")
        return "\n".join(lines)