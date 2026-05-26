"""
commands/spawn.py — SpawnCommand (staff only)

Usage:
    spawn <npc name>
    spawn <npc name> <count>

Spawns NPC instances into the current room AND registers a permanent
spawn table entry so the NPC respawns after death. Use this only for
NPCs that are meant to be a permanent fixture of the room.

For temporary spawns (events, one-offs), use 'summon' instead.

Examples:
    spawn guard
    spawn city guard 2
"""

from commands.base import Command
from models import NpcTemplate, NpcInstance, NpcSpawn


class SpawnCommand(Command):
    def execute(self, character, conn, args: list[str], session) -> str:

        # ── Staff check ───────────────────────────────────────────────────
        if not character.is_staff:
            return "You don't have permission to do that."

        # ── Parse args ────────────────────────────────────────────────────
        if not args:
            return "Usage: spawn <npc name> [count]"

        count = 1
        if args[-1].isdigit():
            count = max(1, min(int(args[-1]), 10))
            name_parts = args[:-1]
        else:
            name_parts = args

        if not name_parts:
            return "Usage: spawn <npc name> [count]"

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

        # ── Spawn instances ────────────────────────────────────────────────
        for _ in range(count):
            NpcInstance.create(conn, template, location_id)

        # ── Register permanent spawn entry ────────────────────────────────
        # ON CONFLICT DO NOTHING: if a spawn entry already exists for this
        # template+location, leave it alone rather than overwriting it.
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO npc_spawns (npc_template_id, location_id, max_count)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (template.id, location_id, count),
            )
        conn.commit()

        noun = "instance" if count == 1 else "instances"
        return (
            f"Spawned {count} {noun} of {template.name} here. "
            f"A permanent spawn entry has been registered."
        )