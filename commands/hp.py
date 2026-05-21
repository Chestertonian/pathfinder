"""
commands/hp.py — HpCommand

Displays current HP, SP, and EP as a single compact line.

Example output:
    10/10 HP  -  8/8 SP  -  9/9 EP
"""

from output import console, COLOR_STAT, COLOR_INFO


class HpCommand:
    def execute(self, character, conn, args):
        c = character

        console.print(
            f"  {c.hp}/{c.hp_max} HP",
            style=COLOR_STAT,
            end="",
        )
        console.print("  -  ", style=COLOR_INFO, end="")
        console.print(f"{c.power}/{c.power_max} SP", style=COLOR_STAT, end="")
        console.print("  -  ", style=COLOR_INFO, end="")
        console.print(f"{c.endurance}/{c.endurance_max} EP", style=COLOR_STAT)

        return None