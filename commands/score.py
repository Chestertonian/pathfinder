"""
commands/score.py — ScoreCommand

Displays the character's full stat sheet.

Does NOT open its own DB connection — uses the one passed in by the caller.
Does NOT call emit_event() — this is a personal UI panel, not a world event.
"""


def _stat_modifier(value: int) -> int:
    return (value - 10) // 2


def _fmt_modifier(mod: int) -> str:
    return f"+{mod}" if mod >= 0 else str(mod)


class ScoreCommand:
    def execute(self, character, conn, args, session):

        lines = []

        lines.append("-" * 40)
        lines.append(f"\n  {character.name.capitalize()}  —  {character.char_class.capitalize()}")
        lines.append("-" * 40)
        lines.append("")

        lines.append(f"  Level  {character.level}    XP  {character.xp}    Gold  {character.gold}")
        lines.append("")

        lines.append("  Resources")
        lines.append(f"  HP    {character.hp} / {character.hp_max}")
        lines.append(f"  EP    {character.endurance} / {character.endurance_max}")
        lines.append(f"  SP    {character.power} / {character.power_max}")
        lines.append("")

        lines.append("  Attributes")
        for label, value in [
            ("STR", character.strength),
            ("DEX", character.dexterity),
            ("CON", character.constitution),
            ("INT", character.intelligence),
            ("WIS", character.wisdom),
            ("CHA", character.charisma),
        ]:
            mod = _stat_modifier(value)
            lines.append(f"  {label:<4} {value:>2}  ({_fmt_modifier(mod)})")

        lines.append("")
        lines.append("-" * 40)

        session.send("\n".join(lines) + "\n")
        return None