VALID_STATS = {"hp", "power", "endurance", "strength", "dexterity",
               "constitution", "intelligence", "wisdom", "charisma", "gold", "xp"}

class SetstatCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You don't have permission to do that."
        if len(args) != 2 or not args[1].isdigit():
            return "Usage: setstat <stat> <value>"
        stat, value = args[0].lower(), int(args[1])
        if stat not in VALID_STATS:
            return f"Unknown stat. Valid: {', '.join(sorted(VALID_STATS))}"
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE characters SET {stat} = %s WHERE id = %s",
                (value, character.id)
            )
        conn.commit()
        return f"{stat} set to {value}."