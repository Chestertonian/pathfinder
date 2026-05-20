"""
seed_world.py

Populates the database with a small set of starter locations and exits.
Run this once after applying schema.sql to give the world something to load.

Safe to re-run: clears existing location/exit data before inserting.
WARNING: This will delete all locations and exits. Do not run on live data.
"""

import db  # Connection module

# ------------------------------------------------------------------
# Location definitions
# Each dict maps directly to a row in the `locations` table.
# ------------------------------------------------------------------

LOCATIONS = [
    {
        "name": "Immigration Entry Offices",
        "description": (
            """You stand in a long stone chamber built just within the Eastern Gate's
            inner wall where the guards gather immigrants before releasing them into 
            the city itself. The room is bare and functional: there are broad flagstones 
            worn smooth, iron-barred counters where clerks record names, and high windows
            that admit light from the outer yard beyond. People arrive here in clusters
            - caravans finishing long journeys, travelers dusty from the road, 
            mercenaries attempting to enter town, and refugees trying to decide what 
            story to tell the city. Guards move through them with practiced indifference, 
            not unkind, yet entirely focused on procedure, while noticeboards along the walls 
            crowd with overlapping postings for escorts, missing persons, warnings from the 
            frontier, and requests written in hurried scripts. Nothing here tells you what 
            you are meant to be; it only makes clear that you are known to the city."""
        ),
        "region": "veranis",
        "is_safe": True,
        "is_settlement": True,
        "is_outdoor": False,
        "brightness": 1,
        "smell": "It smells of torch smoke and unwashed bodies.",
        "sound": "You smell distant hammering and the quiet murmur of voices.",
        "search": "",
    },
    
    {
        "name": "Inside the Gate - Veranis",
        "description": (
            """Inside the eastern gate complex of Veranis, a broad stone courtyard opens between the gatehouse walls and low administrative buildings, where arriving traffic is briefly funneled before dispersing into the city. Wagon tracks score the flagstones in pale lines, converging toward marked lanes that separate carts, riders, and foot traffic without fully stopping movement. The air carries constant noise from wheels, shouted directions, and clerks calling out inspections while seated under narrow awnings along the edges. A battered well and a tall notice post stand among stacks of temporarily held goods, and from here travelers either turn deeper into the city or peel away toward hiring yards, inns, and the main roads leading onward through the city."""
        ),
        "region": "veranis",
        "is_safe": True,
        "is_settlement": True,
        "is_outdoor": True,
        "brightness": 0,
        "smell": "It smells of animals.",
        "sound": "You hear wagons as they rumble through the city. Hawkers shout their wares. At all hours, the city is busy.",
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
    {
        "from_index": 0,
        "to_index": 1,
        "direction": "north",
        "cost": 1,
        "description": "",
    },
    {
        "from_index": 1,
        "to_index": 0,
        "direction": "south",
        "cost": 1,
        "description": "",
    },
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
            to_id = location_ids[exit_def["to_index"]]
            cur.execute(
                """
                INSERT INTO exits (from_location, to_location, direction, cost, description)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    from_id,
                    to_id,
                    exit_def["direction"],
                    exit_def["cost"],
                    exit_def["description"],
                ),
            )
    conn.commit()
    print(f"Inserted {len(EXITS)} exits.")


def seed():
    with db.get_connection() as conn:
        clear_world(conn)
        location_ids = insert_locations(conn)
        insert_exits(conn, location_ids)
        print("World seeded successfully.")


if __name__ == "__main__":
    seed()
