"""
commands/score.py — ScoreCommand

Displays the character's full stat sheet.

Does NOT open its own DB connection — uses the one passed in by the caller.
Does NOT call emit_event() — this is a personal UI panel, not a world event.
Returns a string on error, None on success (matching command interface convention).
"""

from output import (
    console,
    print_error, rule, blank,
    COLOR_STAT, COLOR_INFO, COLOR_FLAVOR,
)


# ---------------------------------------------------------------------------
# Helpers (module-private)
# ---------------------------------------------------------------------------

def _stat_modifier(value: int) -> int:
    """Standard D&D modifier: (stat - 10) // 2"""
    return (value - 10) // 2


def _fmt_modifier(mod: int) -> str:
    """Format modifier as +2 or -1."""
    return f"+{mod}" if mod >= 0 else str(mod)


def _print_resource(label: str, current: int, maximum: int) -> None:
    """Print one resource line:   HP   18 / 25"""
    console.print(f"  {label:<4} ", style=COLOR_INFO, end="")
    console.print(f"{current}", style=COLOR_STAT, end="")
    console.print(" / ", style="grey54", end="")
    console.print(str(maximum), style=COLOR_STAT)


# ---------------------------------------------------------------------------
# Command class
# ---------------------------------------------------------------------------

class ScoreCommand:
    def execute(self, character, conn, args):
        """
        character : the logged-in character object (has .name, .hp, .strength, etc.)
        conn      : active DB connection (unused here — all data is on the character object)
        args      : list of extra words typed after 'score' (ignored)
        """

        # ── Header ──────────────────────────────────────────────────────────
        rule()
        console.print(
            f"\n  {character.name.capitalize()}  —  {character.char_class.capitalize()}",
            style="blue",
        )
        rule()
        blank()

        # ── Level / XP / Gold ───────────────────────────────────────────────
        console.print("  [bold]Level[/bold]  ", style=COLOR_INFO, end="")
        console.print(str(character.level), style=COLOR_STAT, end="")
        console.print("    [bold]XP[/bold]  ", style=COLOR_INFO, end="")
        console.print(str(character.xp), style=COLOR_STAT, end="")
        console.print("    [bold]Gold[/bold]  ", style=COLOR_INFO, end="")
        console.print(str(character.gold), style="bold yellow")

        blank()

        # ── Resources ───────────────────────────────────────────────────────
        console.print("  [bold]Resources[/bold]", style=COLOR_INFO)
        _print_resource("HP", character.hp, character.hp_max)
        _print_resource("EP", character.endurance, character.endurance_max)
        _print_resource("SP", character.power, character.power_max)

        blank()

        # ── Core attributes ─────────────────────────────────────────────────
        console.print("  [bold]Attributes[/bold]", style=COLOR_INFO)

        stats = [
            ("STR", character.strength),
            ("DEX", character.dexterity),
            ("CON", character.constitution),
            ("INT", character.intelligence),
            ("WIS", character.wisdom),
            ("CHA", character.charisma),
        ]

        for label, value in stats:
            mod = _stat_modifier(value)
            mod_str = _fmt_modifier(mod)
            console.print(f"  {label:<4} ", style=COLOR_INFO, end="")
            console.print(f"{value:>2}  ", style=COLOR_STAT, end="")
            console.print(f"({mod_str})", style="grey54")

        blank()
        rule()

        return None  # success — no error message