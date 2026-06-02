"""
commands/level.py — LevelCommand

Shows current level and XP required to advance.
"""


def _xp_required(level: int) -> int:
    BASE = 1000
    K    = 2.3
    return int(BASE * (level ** K))


class LevelCommand:
    def execute(self, character, conn, args, session):
        xp_needed = _xp_required(character.level)
        xp_remaining = max(0, xp_needed - character.xp)

        lines = []
        lines.append(f"\n  You are level {character.level}.")
        lines.append(f"  To advance, you require {xp_remaining} XP.")
        lines.append("")

        return "\n".join(lines)