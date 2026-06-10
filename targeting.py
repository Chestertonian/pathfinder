"""
targeting.py — Shared target parsing and resolution utilities.

Usage pattern in any command:
    parsed = parse_target(args)
    targets = resolve_npc_targets(parsed, character.location_id, conn)
    if not targets:
        return "You don't see that here."
"""


def parse_target(args):
    """
    Parse a list of arg tokens into a target descriptor dict.

    Examples:
        ["orc"]         → { index: 1,    name: "orc",     all: False }
        ["2.orc"]       → { index: 2,    name: "orc",     all: False }
        ["all.orc"]     → { index: None, name: "orc",     all: True  }
        ["all"]         → { index: None, name: None,      all: True  }
        ["big", "orc"]  → { index: 1,    name: "big orc", all: False }

    Returns a dict with keys: index (int|None), name (str|None), all (bool)
    """
    if not args:
        return {"index": None, "name": None, "all": False}

    first = args[0].lower()

    # Check if the first token contains a dot — e.g. "2.orc" or "all.orc"
    if "." in first:
        prefix, _, rest = first.partition(".")
        remainder = ([rest] + args[1:]) if rest else args[1:]
        name = " ".join(remainder).strip() or None

        if prefix == "all":
            return {"index": None, "name": name, "all": True}

        if prefix.isdigit():
            return {"index": int(prefix), "name": name, "all": False}

        # Unrecognised prefix — treat the whole thing as a plain name
        return {"index": 1, "name": " ".join(args).lower(), "all": False}

    # Plain "all" with no dot — get all with no name filter
    if first == "all" and len(args) == 1:
        return {"index": None, "name": None, "all": True}

    # Plain name, possibly multi-word — e.g. ["big", "orc"]
    return {"index": 1, "name": " ".join(args).lower(), "all": False}


def resolve_npc_targets(parsed, location_id, conn):
    """
    Query live NPCs in a room and return matches based on a parsed target.

    Returns a list of (npc_instance_id, npc_name) tuples.
    Empty list means nothing matched.
    """
    name_filter = parsed["name"]
    want_all    = parsed["all"]
    index       = parsed["index"]

    with conn.cursor() as cur:
        if name_filter:
            cur.execute(
                """
                SELECT ni.id, nt.name
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.location_id = %s
                  AND ni.is_alive = TRUE
                  AND LOWER(nt.name) LIKE %s
                ORDER BY ni.id ASC
                """,
                (location_id, f"%{name_filter}%"),
            )
        else:
            # No name filter — match everything alive in the room
            cur.execute(
                """
                SELECT ni.id, nt.name
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.location_id = %s
                  AND ni.is_alive = TRUE
                ORDER BY ni.id ASC
                """,
                (location_id,),
            )

        rows = cur.fetchall()

    if not rows:
        return []

    if want_all:
        return rows

    # index is 1-based — "2.orc" means the second match
    if index is not None and index <= len(rows):
        return [rows[index - 1]]

    return []


def resolve_item_targets(parsed, location_id, conn):
    """
    Query items on the ground in a room and return matches based on a parsed target.

    Returns a list of (item_instance_id, item_name) tuples.
    """
    name_filter = parsed["name"]
    want_all    = parsed["all"]
    index       = parsed["index"]

    with conn.cursor() as cur:
        if name_filter:
            cur.execute(
                """
                SELECT ii.id, it.name
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'location'
                  AND ii.owner_id   = %s
                  AND LOWER(it.name) LIKE %s
                ORDER BY ii.id ASC
                """,
                (location_id, f"%{name_filter}%"),
            )
        else:
            cur.execute(
                """
                SELECT ii.id, it.name
                FROM item_instances ii
                JOIN item_templates it ON it.id = ii.item_template_id
                WHERE ii.owner_type = 'location'
                  AND ii.owner_id   = %s
                ORDER BY ii.id ASC
                """,
                (location_id,),
            )

        rows = cur.fetchall()

    if not rows:
        return []

    if want_all:
        return rows

    if index is not None and index <= len(rows):
        return [rows[index - 1]]

    return []


def resolve_player_targets(parsed, location_id, conn):
    """
    Query logged-in players in a room and return matches based on a parsed target.
    Never returns the searching character — callers handle self-targeting if needed.

    Returns a list of (character_id, character_name) tuples.
    """
    name_filter = parsed["name"]
    want_all    = parsed["all"]
    index       = parsed["index"]

    with conn.cursor() as cur:
        if name_filter:
            cur.execute(
                """
                SELECT id, name
                FROM characters
                WHERE location_id  = %s
                  AND is_logged_in = TRUE
                  AND LOWER(name) LIKE %s
                ORDER BY id ASC
                """,
                (location_id, f"%{name_filter}%"),
            )
        else:
            cur.execute(
                """
                SELECT id, name
                FROM characters
                WHERE location_id  = %s
                  AND is_logged_in = TRUE
                ORDER BY id ASC
                """,
                (location_id,),
            )

        rows = cur.fetchall()

    if not rows:
        return []

    if want_all:
        return rows

    if index is not None and index <= len(rows):
        return [rows[index - 1]]

    return []


def resolve_npc_and_player_targets(parsed, location_id, conn):
    """
    Query both NPCs and logged-in players in a room and return matches.
    Useful for commands like 'consider' or powers that can target either.

    Returns a list of (id, name, kind) tuples where kind is 'npc' or 'player'.
    """
    name_filter = parsed["name"]
    want_all    = parsed["all"]
    index       = parsed["index"]

    with conn.cursor() as cur:
        if name_filter:
            cur.execute(
                """
                SELECT ni.id, nt.name, 'npc' AS kind
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.location_id = %s
                  AND ni.is_alive    = TRUE
                  AND LOWER(nt.name) LIKE %s

                UNION ALL

                SELECT c.id, c.name, 'player' AS kind
                FROM characters c
                WHERE c.location_id  = %s
                  AND c.is_logged_in = TRUE
                  AND LOWER(c.name)  LIKE %s

                ORDER BY kind, id ASC
                """,
                (location_id, f"%{name_filter}%", location_id, f"%{name_filter}%"),
            )
        else:
            cur.execute(
                """
                SELECT ni.id, nt.name, 'npc' AS kind
                FROM npc_instances ni
                JOIN npc_templates nt ON nt.id = ni.npc_template_id
                WHERE ni.location_id = %s
                  AND ni.is_alive    = TRUE

                UNION ALL

                SELECT c.id, c.name, 'player' AS kind
                FROM characters c
                WHERE c.location_id  = %s
                  AND c.is_logged_in = TRUE

                ORDER BY kind, id ASC
                """,
                (location_id, location_id),
            )

        rows = cur.fetchall()

    if not rows:
        return []

    if want_all:
        return rows

    if index is not None and index <= len(rows):
        return [rows[index - 1]]

    return []