"""
commands/look.py — LookCommand

Handles the 'look' command in all its forms:
  look              — describe the current room
  look at <target>  — describe an NPC or item by name
"""

from commands.base import Command
from models import Item, NpcInstance
from output import (
    blank, console, print_flavor, print_info,
    COLOR_TITLE, COLOR_INFO, COLOR_STAT, COLOR_PROMPT,
)


class LookCommand(Command):
    def execute(self, character, conn, args: list[str]) -> str:

        # ── LOOK (no args) → describe the room ───────────────────────────
        if not args or (len(args) == 1 and args[0] == "at"):
            return _describe_room(character, conn)

        # Strip a leading "at" so "look at sword" and "look sword" both work
        target_name = " ".join(args[1:] if args[0] == "at" else args).lower()

        room = character.get_room(conn)
        if room is None:
            return "You seem to be nowhere. Something has gone wrong."

        # ── LOOK AT NPC ───────────────────────────────────────────────────
        npcs = room.get_npcs(conn)
        match = _find_by_name(target_name, npcs)

        if match:
            condition = _health_condition(match.hp, match.hp_max)
            return f"\n  {match.description}\n  {match.name} {condition}.\n"

        # ── LOOK AT ITEM IN ROOM ──────────────────────────────────────────
        items = room.get_items(conn)
        match = _find_by_name(target_name, items)

        if match:
            return f"\n  {match.description}\n"

        # ── LOOK AT ITEM IN INVENTORY ─────────────────────────────────────
        inventory = Item.get_inventory(conn, character.id)
        match = _find_by_name(target_name, inventory)

        if match:
            return f"\n  {match.description}\n"

        # ── NOT FOUND ─────────────────────────────────────────────────────
        return f"  You don't see '{target_name}' here."


# ---------------------------------------------------------------------------
# Room description — the main visual output of the game
# ---------------------------------------------------------------------------

def _describe_room(character, conn) -> str:
    """
    Print the room description in a clean, plain style.
    Room name, dash underline, blank line, description, then exits.
    No color on prose — only red for hostile NPCs.
    """
    room = character.get_room(conn)
    if room is None:
        return "Your location could not be found. Something has gone wrong."
 
    exits = room.get_exits(conn)
    items = room.get_items(conn)
    npcs  = room.get_npcs(conn)
 
    # Room name + dash underline
    blank()
    console.print(room.name)
    console.print("-" * len(room.name))
 
    # Description — plain white, no indent, no color
    blank()
    description = " ".join(room.description.split())
    console.print(description)


    # NPCs
    if npcs:
        blank()
        for npc in npcs:
            console.print(
                f"{npc.name}."
            )
 

    # Items on the ground
    if items:
        blank()
        for item in items:
            console.print(
                f"{item.name}"
            )

    # Exits
    blank()
    if exits:
        exit_parts = []
        for ex in exits:
            direction = ex["direction"].lower()
            if ex["is_locked"]:
                exit_parts.append(f"{direction} (locked)")
            else:
                exit_parts.append(f"{direction}")
        console.print(f"Exits: " + "  ".join(exit_parts))
    else:
        print_info("There are no obvious exits.")

    blank()
    return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_by_name(name: str, objects: list) -> object | None:
    """
    Find the first object whose name contains the search string.
    Simple substring match — good enough for now.
    """
    name = name.lower()
    for obj in objects:
        if name in obj.name.lower():
            return obj
    return None


def _health_condition(hp: int, hp_max: int) -> str:
    """
    Return a plain-English health description.
    Players see this instead of raw numbers — keeps combat information
    appropriately ambiguous, matching the design doc's intent.
    """
    if hp_max == 0:
        return "is in unknown condition"
    ratio = hp / hp_max
    if ratio >= 1.0:
        return "looks uninjured"
    elif ratio >= 0.75:
        return "has a few minor wounds"
    elif ratio >= 0.50:
        return "is noticeably wounded"
    elif ratio >= 0.25:
        return "is badly wounded"
    else:
        return "looks close to death"