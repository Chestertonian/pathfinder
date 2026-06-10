"""
commands/look.py — LookCommand
"""
from collections import Counter

from commands.base import Command
from models import Item, NpcInstance
from output import to_ansi, colorize, _get_item_color

from events import emit_event

IRREGULAR_PLURALS = {
    "wolf": "wolves",
    "ox": "oxen",
    "dwarf": "dwarves",
    "elf": "elves",
    # add as encountered
}

SLOT_ORDER = [
    'weapon', 'offhand', 'head', 'neck', 'back',
    'chest', 'arms', 'legs', 'feet', 'ring'
]


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
            condition = _health_condition(match["hp"], match["hp_max"])
            gear = _describe_player_gear(conn, match["id"])
            return f"\n{match['description']}\n{match['name']} {condition}.\n{gear}"

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
            return f"\n{_get_item_description(conn, match)}\n"

        # ── LOOK AT ITEM IN INVENTORY ─────────────────────────────────────
        inventory = Item.get_inventory(conn, character.id)
        match = _find_by_name(target_name, inventory)

        if match:
            _emit_look_event(conn, character, room, match.name)
            return f"\n{_get_item_description(conn, match)}\n"

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
    boards = _get_boards_in_room(conn, room.id)

    lines = []

    lines.append(f"\033[33m{room.name}\033[0m")   # amber color for name
    lines.append("\n")

    description = "   " + " ".join(room.description.split())  # indent
    lines.append(description)
    lines.append("\n")

    if boards:
            for board in boards:
                post_word = "message" if board["post_count"] == 1 else "messages"
                lines.append(f"{board['name']} ({board['post_count']} {post_word}).")
            lines.append("\n")
            
    if players:
        for player in players:
            lines.append(f"{player['name'].capitalize()}.")
        lines.append("\n")

    if npcs:
        lines.append("\n")
        counts = Counter(npc.name.lower() for npc in npcs)
        for name, count in counts.items():
            if count == 1:
                lines.append(f"{name.title()}.")
            else:
                lines.append(f"{_count_word(count)} {_pluralize(name).title()}.")

    if items:
            for item in items:
                color = _get_item_color(conn, item.instance_id)
                lines.append(f"{colorize(item.name, color)}.")
            lines.append("\n")

    if exits:
        exit_names = [ex["direction"].lower() for ex in exits]
        if len(exit_names) == 1:
            exit_str = exit_names[0]
        elif len(exit_names) == 2:
            exit_str = f"{exit_names[0]} and {exit_names[1]}"
        else:
            exit_str = ", ".join(exit_names[:-1]) + f" and {exit_names[-1]}"
        lines.append(f"   Obvious exits: {exit_str}.")
    else:
        lines.append("   There are no obvious exits.")

    return "\n".join(lines)
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
            SELECT id, name, description, hp, hp_max
            FROM characters
            WHERE location_id = %s
              AND is_logged_in = TRUE
              AND id != %s
            """,
            (room_id, exclude_id),
        )
        rows = cur.fetchall()
    return [{"id": row[0], "name": row[1], "description": f"{row[2]}", "type": "player", "hp": row[3], "hp_max": row[4]} for row in rows]


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
    
def _count_word(n: int) -> str:
    words = {2: "Two", 3: "Three", 4: "Four", 5: "Five",
             6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}
    return words.get(n, str(n))


def _pluralize(name: str) -> str:
    lower = name.lower()
    return IRREGULAR_PLURALS.get(lower, lower + "s")

def _get_boards_in_room(conn, room_id: int) -> list[dict]:
    """Returns all bulletin boards in the given room."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT bb.id, bb.name, COUNT(bp.id) as post_count
            FROM bulletin_boards bb
            LEFT JOIN board_posts bp ON bp.board_id = bb.id
            WHERE bb.location_id = %s
            GROUP BY bb.id, bb.name
        """, (room_id,))
        rows = cur.fetchall()
    return [{"id": row[0], "name": row[1], "post_count": row[2]} for row in rows]


def _describe_player_gear(conn, target_id) -> str:
    """
    Returns a formatted string of a player's equipped gear and clothing.
    """
    with conn.cursor() as cur:
        # Armor, weapons, and clothing — all in one query now
        cur.execute("""
            SELECT ii.equipped_slot, it.name, ii.id,
                   COALESCE(ii.color_override, it.color) as color,
                   it.type, ct.order_number
            FROM item_instances ii
            JOIN item_templates it ON it.id = ii.item_template_id
            LEFT JOIN clothing_templates ct ON ct.item_template_id = ii.item_template_id
            WHERE ii.owner_type = 'character'
              AND ii.owner_id = %s
              AND ii.equipped = TRUE
            ORDER BY ct.order_number ASC NULLS LAST
        """, (target_id,))
        rows = cur.fetchall()

    if not rows:
        return ""

    equipped = {}
    clothing_rows = []

    for slot, name, instance_id, color, item_type, order_number in rows:
        if item_type == 'clothing':
            clothing_rows.append((name, color))
        elif slot:
            equipped[slot] = (name, color)

    lines = []

    if equipped:
        lines.append("\n  Equipment:")
        for slot in SLOT_ORDER:
            if slot in equipped:
                name, color = equipped[slot]
                label = slot.capitalize().ljust(8)
                lines.append(f"    [{label}]  {colorize(name, color)}")

    if clothing_rows:
        lines.append("\n  Wearing:")
        for name, color in clothing_rows:
            lines.append(f"    {colorize(name, color)}")

    return "\n".join(lines) + "\n"




def _get_item_description(conn, item) -> str:
    """
    Returns alt_description if the item has been written on,
    otherwise returns the standard description.
    """
    with conn.cursor() as cur:
        # Check if this instance has been written on
        cur.execute(
            "SELECT 1 FROM written_items WHERE item_instance_id = %s",
            (item.instance_id,),
        )
        is_written = cur.fetchone() is not None

        if is_written:
            # Fetch alt_description from item_templates
            cur.execute(
                "SELECT alt_description FROM item_templates WHERE id = %s",
                (item.template_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                return row[0]

    return item.description