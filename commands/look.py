"""
commands/look.py — LookCommand
"""

from commands.base import Command
from models import Item, NpcInstance

from events import emit_event


class LookCommand(Command):
    def execute(self, character, conn,  args: list[str], session) -> str:

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
            _emit_look_event(conn, character, room, match["name"])
            return f"\nYou see a fellow adventurer.\n"

        # ── LOOK AT NPC ───────────────────────────────────────────────────
        npcs = room.get_npcs(conn)
        match = _find_by_name(target_name, npcs)

        if match:
            _emit_look_event(conn, character, room, match.name)
            condition = _health_condition(match.hp, match.hp_max)
            return f"\n{match.description}\n{match.name} {condition}.\n"

        # ── LOOK AT ITEM IN ROOM ──────────────────────────────────────────
        items = room.get_items(conn)
        match = _find_by_name(target_name, items)

        if match:
            _emit_look_event(conn, character, room, match.name)
            return f"\n{match.description}\n"

        # ── LOOK AT ITEM IN INVENTORY ─────────────────────────────────────
        inventory = Item.get_inventory(conn, character.id)
        match = _find_by_name(target_name, inventory)

        if match:
            _emit_look_event(conn, character, room, match.name)
            return f"\n{match.description}\n"

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

    lines = []                                          # CHANGED: build lines list
    lines.append("\n")
    lines.append("")
    lines.append(room.name)
    lines.append("-" * len(room.name))
    lines.append("\n")
    lines.append("")
    description = " ".join(room.description.split())
    lines.append(description)

    if players:
        lines.append("")
        for player in players:
            lines.append(f"{player['name'].capitalize()}.")

    if npcs:
        lines.append("")
        for npc in npcs:
            lines.append(f"{npc.name.capitalize()}.")

    if items:
        lines.append("")
        for item in items:
            lines.append(f"{item.name}.")

    lines.append("")
    if exits:
        exit_parts = []
        for ex in exits:
            direction = ex["direction"].lower()
            if ex["is_locked"]:
                exit_parts.append(f"{direction} (locked)")
            else:
                exit_parts.append(direction)
        lines.append('\n')
        lines.append("Exits: " + " ".join(exit_parts))
    else:
        lines.append("There are no obvious exits.")

    lines.append("")
    return "\n".join(lines)              # CHANGED: return instead of print

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
    elif ratio >= 0.9:
        return "is scratched"
    elif ratio >= 0.75:
        return "is bleeding lightly"
    elif ratio >= 0.6:
        return "is bleeding"
    elif ratio >= 0.50:
        return "is bleeding moderately"
    elif ratio >= 0.35:
        return "is wounded"
    elif ratio >= 0.25:
        return "is badly wounded"
    elif ratio >=0.1:
        return "is nearly dead"
    else:
        return "looks close to death"

def _emit_look_event(conn, character, room, target_name: str):
    emit_event(
        conn,
        event_type="room",
        message=f"{character.name} looks at {target_name}.",
        location_id=room.id,
        sender_id=character.id,
    )