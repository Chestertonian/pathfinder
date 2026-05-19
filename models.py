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
        """Fetch all visible (non-secret) exits from this room."""
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
        """Fetch a specific exit by direction. Returns None if not found."""
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

    def get_items(self, conn) -> "list[Item]":
        """Fetch all item instances on the ground in this room."""
        return Item.get_at_location(conn, self.id)

    def get_npcs(self, conn) -> "list[NpcInstance]":
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
        self.location_id = new_location_id

    def stat_modifier(self, stat: str) -> int:
        """Return the D&D-style modifier for a given stat name."""
        value = getattr(self, stat)
        return (value - 10) // 2


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

class Item:
    """Represents a specific item instance, joined with its template."""
    def __init__(self, row: dict):
        self.instance_id  = row["instance_id"]
        self.template_id  = row["template_id"]
        self.name         = row["name"]
        self.type         = row["type"]
        self.description  = row["description"]
        self.weight       = row["weight"]
        self.value        = row["value"]
        self.is_takeable  = row["is_takeable"]
        self.is_droppable = row["is_droppable"]
        self.owner_type   = row["owner_type"]
        self.owner_id     = row["owner_id"]
        self.equipped     = row["equipped"]

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
# NpcTemplate
# ---------------------------------------------------------------------------

class NpcTemplate:
    """The definition of an NPC type. Used by the spawn system."""
    def __init__(self, row: dict):
        self.id          = row["id"]
        self.name        = row["name"]
        self.description = row["description"]
        self.gender      = row["gender"]
        self.xp          = row["xp"]
        self.hp_max      = row["hp_max"]
        self.damage_min  = row["damage_min"]
        self.damage_max  = row["damage_max"]
        self.defense     = row["defense"]
        self.is_hostile  = row["is_hostile"]
        self.is_merchant = row["is_merchant"]

    @staticmethod
    def get_by_id(conn, template_id: int) -> "NpcTemplate | None":
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, gender, xp, hp_max,
                       damage_min, damage_max, defense, is_hostile, is_merchant
                FROM npc_templates WHERE id = %s
                """,
                (template_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return NpcTemplate(_npc_template_row(row))

    @staticmethod
    def find_by_name(conn, name: str) -> "list[NpcTemplate]":
        """Find templates whose name contains the search string."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, gender, xp, hp_max,
                       damage_min, damage_max, defense, is_hostile, is_merchant
                FROM npc_templates
                WHERE LOWER(name) LIKE LOWER(%s)
                ORDER BY name
                """,
                (f"%{name}%",),
            )
            return [NpcTemplate(_npc_template_row(row)) for row in cur.fetchall()]


def _npc_template_row(row) -> dict:
    return {
        "id":          row[0],
        "name":        row[1],
        "description": row[2],
        "gender":      row[3],
        "xp":          row[4],
        "hp_max":      row[5],
        "damage_min":  row[6],
        "damage_max":  row[7],
        "defense":     row[8],
        "is_hostile":  row[9],
        "is_merchant": row[10],
    }


# ---------------------------------------------------------------------------
# NpcInstance
# ---------------------------------------------------------------------------

class NpcInstance:
    """A specific NPC in the world, joined with its template."""
    def __init__(self, row: dict):
        self.instance_id  = row["instance_id"]
        self.template_id  = row["template_id"]
        self.name         = row["name"]
        self.description  = row["description"]
        self.gender       = row["gender"]
        self.location_id  = row["location_id"]
        self.hp           = row["hp"]
        self.hp_max       = row["hp_max"]
        self.is_alive     = row["is_alive"]
        self.is_hostile   = row["is_hostile"]
        self.is_merchant  = row["is_merchant"]

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

    @staticmethod
    def create(conn, template: "NpcTemplate", location_id: int) -> "NpcInstance":
        """Create a new NPC instance from a template and insert it into the DB."""
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO npc_instances
                    (npc_template_id, location_id, hp, is_alive, home_room_id)
                VALUES (%s, %s, %s, TRUE, %s)
                RETURNING id
                """,
                (template.id, location_id, template.hp_max, location_id),
            )
            instance_id = cur.fetchone()[0]
        conn.commit()
        return NpcInstance({
            "instance_id": instance_id,
            "template_id": template.id,
            "name":        template.name,
            "description": template.description,
            "gender":      template.gender,
            "location_id": location_id,
            "hp":          template.hp_max,
            "hp_max":      template.hp_max,
            "is_alive":    True,
            "is_hostile":  template.is_hostile,
            "is_merchant": template.is_merchant,
        })


# ---------------------------------------------------------------------------
# NpcSpawn
# ---------------------------------------------------------------------------

class NpcSpawn:
    """
    A spawn entry — defines that a given NPC template should be kept
    populated at a given location up to max_count instances.
    """
    def __init__(self, row: dict):
        self.id              = row["id"]
        self.npc_template_id = row["npc_template_id"]
        self.location_id     = row["location_id"]
        self.max_count       = row["max_count"]
        self.respawn_seconds = row["respawn_seconds"]
        self.last_spawned_at = row["last_spawned_at"]
        self.is_active       = row["is_active"]

    @staticmethod
    def create(conn, template_id: int, location_id: int,
               max_count: int = 1, respawn_seconds: int = 300) -> "NpcSpawn":
        """Insert a new spawn entry and return it."""
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO npc_spawns
                    (npc_template_id, location_id, max_count, respawn_seconds)
                VALUES (%s, %s, %s, %s)
                RETURNING id, npc_template_id, location_id,
                          max_count, respawn_seconds, last_spawned_at, is_active
                """,
                (template_id, location_id, max_count, respawn_seconds),
            )
            row = cur.fetchone()
        conn.commit()
        return NpcSpawn({
            "id":              row[0],
            "npc_template_id": row[1],
            "location_id":     row[2],
            "max_count":       row[3],
            "respawn_seconds": row[4],
            "last_spawned_at": row[5],
            "is_active":       row[6],
        })

    @staticmethod
    def get_all_active(conn) -> "list[NpcSpawn]":
        """Fetch all active spawn entries. Used by the respawn system."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, npc_template_id, location_id,
                       max_count, respawn_seconds, last_spawned_at, is_active
                FROM npc_spawns
                WHERE is_active = TRUE
                """
            )
            return [
                NpcSpawn({
                    "id":              row[0],
                    "npc_template_id": row[1],
                    "location_id":     row[2],
                    "max_count":       row[3],
                    "respawn_seconds": row[4],
                    "last_spawned_at": row[5],
                    "is_active":       row[6],
                })
                for row in cur.fetchall()
            ]

    def count_alive(self, conn) -> int:
        """Count how many live instances of this spawn's template exist here."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM npc_instances
                WHERE npc_template_id = %s
                  AND location_id = %s
                  AND is_alive = TRUE
                """,
                (self.npc_template_id, self.location_id),
            )
            return cur.fetchone()[0]

    def touch(self, conn) -> None:
        """Update last_spawned_at to now."""
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE npc_spawns SET last_spawned_at = NOW() WHERE id = %s",
                (self.id,),
            )
        conn.commit()


# ---------------------------------------------------------------------------
# BroadcastMessage
# ---------------------------------------------------------------------------

class BroadcastMessage:
    """
    A message written to the global broadcast queue by a staff member.
    All connected clients poll for new rows and print them.
    """
    def __init__(self, row: dict):
        self.id           = row["id"]
        self.character_id = row["character_id"]
        self.sender_character_id = row["sender_character_id"]
        self.message      = row["message"]
        self.color        = row["color"]
        self.use_border   = row["use_border"]
        self.created_at   = row["created_at"]

    @staticmethod
    def send(conn, character_id: int, message: str,
             color: str = "white", use_border: bool = False) -> None:
        """
        Insert a global broadcast message (proclaim).
        location_id is NULL — visible to all connected clients.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO broadcast_messages
                    (character_id, message, color, use_border, location_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (character_id, message, color, use_border),
            )
        conn.commit()

    @staticmethod
    def announce(conn, location_id: int, message: str, color: str = "white", sender_character_id=None) -> None:
        """
        Send a message to all players currently in a specific room.
        Used internally by the game engine — not a player command.

        Examples of when to call this:
            - An NPC speaks to everyone in the room
            - A trap triggers and narrates its effect
            - A boss encounter begins
            - Environmental events (the ground shakes, a bell tolls)

        Usage:
            BroadcastMessage.announce(conn, room.id, "The guard shouts: Halt!", sender_character_id=None)
            BroadcastMessage.announce(conn, room.id, "The dragon roars.", color="red3", sender_character_id=None)
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO broadcast_messages
                    (message, color, location_id, sender_character_id)
                VALUES (%s, %s, %s, %s)
                """,
                (message, color, location_id, sender_character_id),
            )
        conn.commit()

    @staticmethod
    def get_since(conn, last_id: int, location_id: int, character_id: int)-> "list[BroadcastMessage]":
        """
        Fetch all messages since last_id that are relevant to this player.
        That means: global messages (location_id IS NULL) OR messages
        for the room they're currently in.
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, character_id, message, color, use_border, created_at, sender_character_id
                FROM broadcast_messages
                WHERE id > %s
                AND (location_id IS NULL OR location_id = %s)
                AND (sender_character_id IS NULL OR sender_character_id != %s)
                ORDER BY id ASC
                """,
                (last_id, location_id, character_id),
            )
            return [
                BroadcastMessage({
                    "id":           row[0],
                    "character_id": row[1],
                    "message":      row[2],
                    "color":        row[3],
                    "use_border":   row[4],
                    "created_at":   row[5],
                    "sender_character_id": row[6],
                })
                for row in cur.fetchall()
            ]

    @staticmethod
    def get_latest_id(conn) -> int:
        """Get the current highest message ID. Called once on login."""
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(id), 0) FROM broadcast_messages")
            return cur.fetchone()[0]