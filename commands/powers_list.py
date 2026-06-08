"""
commands/powers_list.py
"""

class PowersCommand:
    def execute(self, character, conn, args, session):
        guild = (character.char_class or "").lower()

        show_all = False
        if args and args[0].strip().lower() == "all":
            show_all = True

        with conn.cursor() as cur:
            if show_all:
                cur.execute(
                    """
                    SELECT
                        level_required,
                        display_name
                    FROM power_templates
                    WHERE source_type = 'class'
                      AND source_value = %s
                    ORDER BY level_required ASC, display_name ASC
                    """,
                    (guild,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        level_required,
                        display_name
                    FROM power_templates
                    WHERE source_type = 'class'
                      AND source_value = %s
                      AND level_required <= %s
                    ORDER BY level_required ASC, display_name ASC
                    """,
                    (guild, character.level),
                )

            rows = cur.fetchall()

        if not rows:
            session.send("\nYou are new to the city, and have no guild powers available yet.\n\n")
            return None

        guild_name = guild.capitalize()

        # Group powers by level
        by_level = {}
        for level_required, display_name in rows:
            by_level.setdefault(level_required, []).append(display_name)

        lines = []
        lines.append("")
        lines.append("[*****************************************]")
        lines.append(f"          {guild_name} Guild Powers")
        lines.append("[*****************************************]")
        lines.append("")
        lines.append("    Level    Power")

        for level in sorted(by_level.keys()):
            powers = ", ".join(by_level[level])
            lines.append(f"      {level:<2}     {powers}")

        if not show_all:
            lines.append("")
            lines.append("Type POWERS ALL to view your full guild progression.")

        lines.append("")
        session.send("\n".join(lines))
        return None