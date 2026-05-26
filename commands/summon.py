"""
commands/summon.py — SummonCommand (staff only)

Usage:
    summon <npc name>
    summon <npc name> <count>

Spawns NPC instances into the current room temporarily.
No spawn table entry is created, so the NPC will not respawn after death.
Use this for events, one-off encounters, or testing.

For permanent room fixtures, use 'spawn' instead.

Examples:
    summon wolf
    summon bandit 3
"""

from commands.base import Command
from models import NpcTemplate, NpcInstance


class SummonCommand(Command):
    def execute(self, character, conn, args: list[str], session) -> str:

        # ── Staff check ───────────────────────────────────────────────────
        if not character.is_staff:
            return "You don't have permission to do that."

        # ── Parse args ────────────────────────────────────────────────────
        if not args:
            return "Usage: summon <npc name> [count]"

        count = 1
        if args[-1].isdigit():
            count = max(1, min(int(args[-1]), 10))
            name_parts = args[:-1]
        else:
            name_parts = args

        if not name_parts:
            return "Usage: summon <npc name> [count]"

        search = " ".join(name_parts)

        # ── Find matching template ─────────────────────────────────────────
        matches = NpcTemplate.find_by_name(conn, search)

        if not matches:
            return f"No NPC template found matching '{search}'."

        if len(matches) > 1:
            names = ", ".join(m.name for m in matches)
            return f"Multiple matches: {names}. Be more specific."

        template = matches[0]
        location_id = character.location_id

        # ── Summon instances (no spawn table entry) ────────────────────────
        for _ in range(count):
            NpcInstance.create(conn, template, location_id)

        noun = "instance" if count == 1 else "instances"
        return (
            f"Summoned {count} {noun} of {template.name} here. "
            f"They will not respawn after death."
        )