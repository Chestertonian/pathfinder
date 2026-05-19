"""
models.py — Game object models

Each class wraps a database row and owns the queries needed to fetch
and manipulate that kind of object. Other modules import these classes
rather than writing raw SQL themselves.

Pattern:
  - Class.__init__ unpacks a row dict into attributes
  - Class.get_by_id(conn, id) is the standard fetch method
  - Instance methods handle queries that need self (e.g. room.get_exits)
"""

from db import get_connection


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class Room:
    def __init__(self, row: dict):
        self.id            = row["id"]
        self.name          = row["name"]
        self.description   = row["description"]
        self.region        = row["region"]
        self.is_safe       = row["is_safe"]
        self.is_settlement = row["is_settlement"]
        self.is_outdoor    = row["is_outdoor"]
        self.brightness    = row["brightness"]
        self.smell         = row["smell"]
        self.sound         = row["sound"]

    @staticmethod
    def get_by_id(conn, room_id: int) -> "Room | None":
        """Fetch a room by ID. Returns None if not found."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, region, is_safe, is_settlement,
                       is_outdoor, brightness, smell, sound
                FROM locations
                WHERE id = %s
                """,
                (room_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return Room({
                "id":            row[0],
                "name":          row[1],
                "description":   row[2],
                "region":        row[3],
                "is_safe":       row[4],
                "is_settlement": row[5],
                "is_outdoor":    row[6],
                "brightness":    row[7],
                "smell":         row[8],
                "sound":         row[9],
            })

    def get_exits(self, conn) -> list[dict]:
        """
        Fetch all visible (non-secret) exits from this room.
        Returns a list of dicts with direction, is_locked, description.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT direction, is_locked, description, cost
                FROM exits
                WHERE from_location = %s AND is_secret = FALSE
                ORDER BY direction
                """,
                (self.id,),
            )
            return [
                {
                    "direction":   row[0],
                    "is_locked":   row[1],
                    "description": row[2],
                    "cost":        row[3],
                }
                for row in cur.fetchall()
            ]

    def get_exit(self, conn, direction: str) -> "dict | None":
        """
        Fetch a specific exit by direction string.
        Returns None if no exit exists in that direction.
        Includes locked and secret exits — callers decide what to do.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT to_location, is_locked, is_secret, cost
                FROM exits
                WHERE from_location = %s AND direction = %s
                """,
                (self.id, direction),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "to_location": row[0],
                "is_locked":   row[1],
                "is_secret":   row[2],
                "cost":        row[3],
            }

    def get_items(self, conn) -> list["Item"]:
        """Fetch all item instances on the ground in this room."""
        return Item.get_at_location(conn, self.id)

    def get_npcs(self, conn) -> list["NpcInstance"]:
        """Fetch all living NPC instances present in this room."""
        return NpcInstance.get_at_location(conn, self.id)


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------

class Character:
    def __init__(self, row: dict):
        self.id            = row["id"]
        self.name          = row["name"]
        self.char_class    = row["class"]
        self.level         = row["level"]
        self.xp            = row["xp"]
        self.location_id   = row["location_id"]
        self.is_staff      = row["is_staff"]

        # Resources
        self.hp            = row["hp"]
        self.hp_max        = row["hp_max"]
        self.power         = row["power"]
        self.power_max     = row["power_max"]
        self.endurance     = row["endurance"]
        self.endurance_max = row["endurance_max"]
        self.gold          = row["gold"]

        # Stats
        self.strength      = row["strength"]
        self.dexterity     = row["dexterity"]
        self.constitution  = row["constitution"]
        self.intelligence  = row["intelligence"]
        self.wisdom        = row["wisdom"]
        self.charisma      = row["charisma"]

    @staticmethod
    def get_by_id(conn, character_id: int) -> "Character | None":
        """Fetch a character by ID. Returns None if not found."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, class, level, xp, location_id, is_staff,
                       hp, hp_max, power, power_max, endurance, endurance_max, gold,
                       strength, dexterity, constitution, intelligence, wisdom, charisma
                FROM characters
                WHERE id = %s
                """,
                (character_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return Character({
                "id":            row[0],
                "name":          row[1],
                "class":         row[2],
                "level":         row[3],
                "xp":            row[4],
                "location_id":   row[5],
                "is_staff":      row[6],
                "hp":            row[7],
                "hp_max":        row[8],
                "power":         row[9],
                "power_max":     row[10],
                "endurance":     row[11],
                "endurance_max": row[12],
                "gold":          row[13],
                "strength":      row[14],
                "dexterity":     row[15],
                "constitution":  row[16],
                "intelligence":  row[17],
                "wisdom":        row[18],
                "charisma":      row[19],
            })

    def get_room(self, conn) -> "Room | None":
        """Fetch the room this character is currently in."""
        return Room.get_by_id(conn, self.location_id)

    def move_to(self, conn, new_location_id: int) -> None:
        """Update this character's location in the DB and on self."""
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE characters SET location_id = %s WHERE id = %s",
                (new_location_id, self.id),
            )
        conn.commit()
        self.location_id = new_location_id  # keep self in sync

    def stat_modifier(self, stat: str) -> int:
        """Return the D&D-style modifier for a given stat name."""
        value = getattr(self, stat)
        return (value - 10) // 2


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

class Item:
    """
    Represents a specific item instance in the world, joined with its template.
    Most display and interaction logic only needs the template fields,
    so we join them at fetch time rather than making two queries.
    """
    def __init__(self, row: dict):
        self.instance_id     = row["instance_id"]
        self.template_id     = row["template_id"]
        self.name            = row["name"]
        self.type            = row["type"]
        self.description     = row["description"]
        self.weight          = row["weight"]
        self.value           = row["value"]
        self.is_takeable     = row["is_takeable"]
        self.is_droppable    = row["is_droppable"]
        self.owner_type      = row["owner_type"]
        self.owner_id        = row["owner_id"]
        self.equipped        = row["equipped"]

    @staticmethod
    def get_at_location(conn, location_id: int) -> "list[Item]":
        """Fetch all items on the ground at a location."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ii.id, it.id, it.name, it.type, it.description,
                       it.weight, it.value, it.is_takeable, it.is_droppable,
                       ii.owner_type, ii.owner_id, ii.equipped
                FROM item_instances ii
                JOIN item_templates it ON ii.item_template_id = it.id
                WHERE ii.owner_type = 'location' AND ii.owner_id = %s
                ORDER BY it.name
                """,
                (location_id,),
            )
            return [Item(_item_row(row)) for row in cur.fetchall()]

    @staticmethod
    def get_inventory(conn, character_id: int) -> "list[Item]":
        """Fetch all items carried by a character."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ii.id, it.id, it.name, it.type, it.description,
                       it.weight, it.value, it.is_takeable, it.is_droppable,
                       ii.owner_type, ii.owner_id, ii.equipped
                FROM item_instances ii
                JOIN item_templates it ON ii.item_template_id = it.id
                WHERE ii.owner_type = 'character' AND ii.owner_id = %s
                ORDER BY it.name
                """,
                (character_id,),
            )
            return [Item(_item_row(row)) for row in cur.fetchall()]


def _item_row(row) -> dict:
    """Helper — maps a raw item query row to a named dict."""
    return {
        "instance_id":  row[0],
        "template_id":  row[1],
        "name":         row[2],
        "type":         row[3],
        "description":  row[4],
        "weight":       row[5],
        "value":        row[6],
        "is_takeable":  row[7],
        "is_droppable": row[8],
        "owner_type":   row[9],
        "owner_id":     row[10],
        "equipped":     row[11],
    }


# ---------------------------------------------------------------------------
# NpcInstance
# ---------------------------------------------------------------------------

class NpcInstance:
    """
    A specific NPC living in the world, joined with its template data.
    Like Item, we join at fetch time to avoid double queries.
    """
    def __init__(self, row: dict):
        self.instance_id   = row["instance_id"]
        self.template_id   = row["template_id"]
        self.name          = row["name"]
        self.description   = row["description"]
        self.gender        = row["gender"]
        self.location_id   = row["location_id"]
        self.hp            = row["hp"]
        self.hp_max        = row["hp_max"]
        self.is_alive      = row["is_alive"]
        self.is_hostile    = row["is_hostile"]
        self.is_merchant   = row["is_merchant"]

    @staticmethod
    def get_at_location(conn, location_id: int) -> "list[NpcInstance]":
        """Fetch all living NPCs at a location."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ni.id, nt.id, nt.name, nt.description, nt.gender,
                       ni.location_id, ni.hp, nt.hp_max, ni.is_alive,
                       nt.is_hostile, nt.is_merchant
                FROM npc_instances ni
                JOIN npc_templates nt ON ni.npc_template_id = nt.id
                WHERE ni.location_id = %s AND ni.is_alive = TRUE
                ORDER BY nt.name
                """,
                (location_id,),
            )
            return [
                NpcInstance({
                    "instance_id": row[0],
                    "template_id": row[1],
                    "name":        row[2],
                    "description": row[3],
                    "gender":      row[4],
                    "location_id": row[5],
                    "hp":          row[6],
                    "hp_max":      row[7],
                    "is_alive":    row[8],
                    "is_hostile":  row[9],
                    "is_merchant": row[10],
                })
                for row in cur.fetchall()
            ]