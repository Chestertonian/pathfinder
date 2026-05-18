"""
seed_world.py

Populates the database with a small set of starter locations and exits.
Run this once after applying schema.sql to give the world something to load.

Safe to re-run: clears existing location/exit data before inserting.
WARNING: This will delete all locations and exits. Do not run on live data.
"""

import db  # Your existing connection module


# ------------------------------------------------------------------
# Location definitions
# Each dict maps directly to a row in the `locations` table.
# ------------------------------------------------------------------

LOCATIONS = [
    {
        "name": "Ashford Town Square",
        "description": (
            "The heart of Ashford, a modest frontier settlement. Cobblestones worn smooth "
            "by years of boot traffic surround a dry stone fountain. A few locals go about "
            "their business without paying you much attention."
        ),
        "region": "Ashford",
        "is_safe": True,
        "is_settlement": True,
        "is_outdoor": True,
        "brightness": 3,
        "smell": "Woodsmoke and horse manure.",
        "sound": "Distant hammering, murmuring voices.",
        "search": "",
    },
    {
        "name": "Ashford North Gate",
        "description": (
            "A heavy timber gate marks the northern edge of Ashford. Two bored guards lean "
            "against the posts. Beyond the gate, a rutted dirt road disappears into the tree line."
        ),
        "region": "Ashford",
        "is_safe": True,
        "is_settlement": True,
        "is_outdoor": True,
        "brightness": 3,
        "smell": "Pine sap on the wind.",
        "sound": "Creaking gate hinges, birdsong.",
        "search": "",
    },
    {
        "name": "The Greywood Road",
        "description": (
            "A lonely road threading between tall, pale-barked trees. The canopy is thick "
            "enough to muffle sound from the settlement behind you. Wheel ruts in the mud "
            "suggest infrequent but regular use."
        ),
        "region": "Greywood",
        "is_safe": False,
        "is_settlement": False,
        "is_outdoor": True,
        "brightness": 2,
        "smell": "Damp earth and rotting leaves.",
        "sound": "Wind through branches. Something rustles off the path.",
        "search": "A torn piece of sacking is caught on a low branch.",
    },
    {
        "name": "Greywood Depths",
        "description": (
            "The road thins to a track here. Trees press close on both sides and the light "
            "dims noticeably. Animal trails branch off in several directions. This feels like "
            "a place that does not welcome visitors."
        ),
        "region": "Greywood",
        "is_safe": False,
        "is_settlement": False,
        "is_outdoor": True,
        "brightness": 1,
        "smell": "Moss, mud, and something faintly sweet that you cannot place.",
        "sound": "Silence, mostly. The birds have stopped.",
        "search": "Claw marks score the bark of a nearby oak, roughly at head height.",
    },
    {
        "name": "Collapsed Waystation",
        "description": (
            "The ruin of a small stone building, long abandoned. The roof has caved in and "
            "weeds grow through the floor. A firepit in the corner looks like it was used "
            "within the last season, though not recently."
        ),
        "region": "Greywood",
        "is_safe": False,
        "is_settlement": False,
        "is_outdoor": False,
        "brightness": 1,
        "smell": "Ash, mildew, and old leather.",
        "sound": "Water dripping somewhere in the rubble.",
        "search": "Beneath a loose flagstone you find a rusted iron ring, but nothing below it.",
    },
    {
        "name": "Ashford East Road",
        "description": (
            "The road east out of Ashford is better maintained than the northern track. "
            "Merchant posts mark the distance at irregular intervals. Open farmland rolls "
            "out on either side."
        ),
        "region": "Ashford",
        "is_safe": True,
        "is_settlement": False,
        "is_outdoor": True,
        "brightness": 3,
        "smell": "Cut grass and turned soil.",
        "sound": "Crows, distant cattle.",
        "search": "",
    },
    {
        "name": "Millford Crossing",
        "description": (
            "A stone bridge crosses a wide, shallow river here. A watermill turns slowly on "
            "the far bank. The settlement of Millford is visible downstream, smoke rising "
            "from its chimneys."
        ),
        "region": "Millford",
        "is_safe": True,
        "is_settlement": False,
        "is_outdoor": True,
        "brightness": 3,
        "smell": "River water and fresh-cut wood.",
        "sound": "The mill wheel, rushing water, distant voices.",
        "search": "",
    },
]


# ------------------------------------------------------------------
# Exit definitions
# Each dict is one row in the `exits` table.
# from_index and to_index refer to positions in LOCATIONS above (0-based).
# They are resolved to real IDs after insert.
# ------------------------------------------------------------------

EXITS = [
    # Town square <-> North gate (two-way)
    {"from_index": 0, "to_index": 1, "direction": "north", "cost": 1, "description": "Toward the north gate."},
    {"from_index": 1, "to_index": 0, "direction": "south", "cost": 1, "description": "Back into the town square."},

    # North gate <-> Greywood Road (two-way)
    {"from_index": 1, "to_index": 2, "direction": "north", "cost": 1, "description": "Through the gate and onto the road."},
    {"from_index": 2, "to_index": 1, "direction": "south", "cost": 1, "description": "The road leads back toward the settlement gate."},

    # Greywood Road <-> Greywood Depths (two-way)
    {"from_index": 2, "to_index": 3, "direction": "north", "cost": 2, "description": "Deeper into the Greywood."},
    {"from_index": 3, "to_index": 2, "direction": "south", "cost": 2, "description": "Back toward the road and the settlement."},

    # Greywood Road -> Waystation (one-way visible, return is west)
    {"from_index": 2, "to_index": 4, "direction": "east", "cost": 1, "description": "A short track leads to a ruined building."},
    {"from_index": 4, "to_index": 2, "direction": "west", "cost": 1, "description": "Back to the main road."},

    # Town square <-> East road (two-way)
    {"from_index": 0, "to_index": 5, "direction": "east", "cost": 1, "description": "Out onto the eastern road."},
    {"from_index": 5, "to_index": 0, "direction": "west", "cost": 1, "description": "Back into Ashford."},

    # East road <-> Millford Crossing (two-way)
    {"from_index": 5, "to_index": 6, "direction": "east", "cost": 2, "description": "The road continues toward the river crossing."},
    {"from_index": 6, "to_index": 5, "direction": "west", "cost": 2, "description": "West along the road toward Ashford."},
]


# ------------------------------------------------------------------
# Seed functions
# ------------------------------------------------------------------

def clear_world(conn):
    """
    Deletes all exits and locations so we start fresh.
    Order matters: exits reference locations, so exits must go first.
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM exits;")
        cur.execute("DELETE FROM locations;")
    conn.commit()
    print("Cleared existing locations and exits.")


def insert_locations(conn) -> list[int]:
    """
    Inserts all locations and returns their generated IDs in order.
    The order matches the LOCATIONS list, so index 0 -> ID of first row, etc.
    """
    ids = []
    with conn.cursor() as cur:
        for loc in LOCATIONS:
            cur.execute(
                """
                INSERT INTO locations (
                    name, description, region,
                    is_safe, is_settlement, is_outdoor,
                    brightness, smell, sound, search
                )
                VALUES (
                    %(name)s, %(description)s, %(region)s,
                    %(is_safe)s, %(is_settlement)s, %(is_outdoor)s,
                    %(brightness)s, %(smell)s, %(sound)s, %(search)s
                )
                RETURNING id;
                """,
                loc,
            )
            row = cur.fetchone()
            ids.append(row[0])
    conn.commit()
    print(f"Inserted {len(ids)} locations.")
    return ids


def insert_exits(conn, location_ids: list[int]):
    """
    Inserts all exits, resolving from_index/to_index to real DB IDs.
    """
    with conn.cursor() as cur:
        for exit_def in EXITS:
            from_id = location_ids[exit_def["from_index"]]
            to_id   = location_ids[exit_def["to_index"]]
            cur.execute(
                """
                INSERT INTO exits (from_location, to_location, direction, cost, description)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (from_id, to_id, exit_def["direction"], exit_def["cost"], exit_def["description"]),
            )
    conn.commit()
    print(f"Inserted {len(EXITS)} exits.")


def seed():
    conn = db.get_connection()
    try:
        clear_world(conn)
        location_ids = insert_locations(conn)
        insert_exits(conn, location_ids)
        print("World seeded successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
