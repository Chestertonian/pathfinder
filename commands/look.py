"""
commands/look.py — LookCommand
"""

from commands.base import Command
from models import Item, NpcInstance
from output import (
    blank,
    console,
    print_flavor,
    print_info,
    COLOR_TITLE,
    COLOR_INFO,
    COLOR_STAT,
    COLOR_PROMPT,
)
from events import emit_event


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

        # ── LOOK AT PLAYER IN ROOM ────────────────────────────────────────
        players = _get_players_in_room(conn, room.id, exclude_id=character.id)
        match = _find_by_name(target_name, players)

        if match:
            emit_event(
                conn,
                event_type=room,
                message=f"{character.name} looks at {target_name.capitalize()}.",
                location_id=room.id,
                sender_id=character.id,
            )
            # This isn't quite right.
            return f"\n  You see a fellow adventurer.\n"

        # ── LOOK AT NPC ───────────────────────────────────────────────────
        npcs = room.get_npcs(conn)
        match = _find_by_name(target_name, npcs)

        if match:
            condition = _health_condition(match.hp, match.hp_max)
            return f"\n{match.description}\n{match.name} {condition}.\n"

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
# Room description
# ---------------------------------------------------------------------------


def _describe_room(character, conn) -> str:
    room = character.get_room(conn)
    if room is None:
        return "Your location could not be found. Something has gone wrong."

    exits = room.get_exits(conn)
    items = room.get_items(conn)
    npcs = room.get_npcs(conn)
    players = _get_players_in_room(conn, room.id, exclude_id=character.id)

    # Room name + dash underline
    blank()
    console.print(room.name)
    console.print("-" * len(room.name))

    # Description
    blank()
    description = " ".join(room.description.split())
    console.print(description)

    # Other players
    if players:
        blank()
        for player in players:
            console.print(f"{player['name'].capitalize()} is here.")

    # NPCs
    if npcs:
        blank()
        for npc in npcs:
            console.print(f"{npc.name.capitalize()}.")

    # Items on the ground
    if items:
        blank()
        for item in items:
            console.print(f"{item.name}")

    # Exits
    blank()
    if exits:
        exit_parts = []
        for ex in exits:
            direction = ex["direction"].lower()
            if ex["is_locked"]:
                exit_parts.append(f"{direction} (locked)")
            else:
                exit_parts.append(direction)
        console.print("Exits: " + "  ".join(exit_parts))
    else:
        print_info("There are no obvious exits.")

    blank()
    return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_players_in_room(conn, room_id: int, exclude_id: int) -> list[dict]:
    """
    Returns all logged-in players in the given room, excluding yourself.
    Each result is a plain dict with 'id' and 'name'.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name
            FROM characters
            WHERE location_id = %s
              AND is_logged_in = TRUE
              AND id != %s
            """,
            (room_id, exclude_id),
        )
        rows = cur.fetchall()
    return [{"id": row[0], "name": row[1]} for row in rows]


def _find_by_name(name: str, objects: list) -> object | None:
    """
    Find the first object whose name contains the search string.
    Works on both model objects (with .name) and dicts (with ['name']).
    """
    name = name.lower()
    for obj in objects:
        obj_name = obj["name"] if isinstance(obj, dict) else obj.name
        if name in obj_name.lower():
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
