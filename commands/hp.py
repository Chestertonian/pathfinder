"""
commands/hp.py — HpCommand

Displays current HP, SP, and EP as a single compact line.

Example output:
    10/10 HP  -  8/8 SP  -  9/9 EP
"""

class HpCommand:
    def execute(self, character, conn, args, session):
        c = character
        session.send(
            f"{c.hp}/{c.hp_max} HP - {c.power}/{c.power_max} SP - {c.endurance}/{c.endurance_max} EP \n")
        return None