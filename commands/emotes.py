"""
commands/emotes.py — Emote system

Each emote defines up to five message templates:
    self_untargeted   — what YOU see when no target ("You smile.")
    room_untargeted   — what OTHERS see when no target ("Erium smiles.")
    self_targeted     — what YOU see when targeting ("You bow to Tavin.")
    room_targeted     — what OTHERS see when targeting ("Erium bows to Tavin.")
    target_targeted   — what the TARGET sees ("Erium bows to you.")

Tokens:
    {actor}    — actor's name
    {target}   — target's name
    {his_her}  — his/her/their based on actor gender
    {him_her}  — him/her/them
    {he_she}   — he/she/they

Targeted emotes work on both players and NPCs.
NPCs don't receive the target_targeted message (no session).
"""

from events import emit_event

# ---------------------------------------------------------------------------
# Pronoun helpers
# ---------------------------------------------------------------------------


def _pronouns(gender: int) -> dict:
    """
    gender: 0=unknown/neutral, 1=male, 2=female
    Returns dict of pronoun tokens.
    """
    if gender == 1:
        return {"he_she": "he", "his_her": "his", "him_her": "him"}
    elif gender == 2:
        return {"he_she": "she", "his_her": "her", "him_her": "her"}
    else:
        return {"he_she": "they", "his_her": "their", "him_her": "them"}


# ---------------------------------------------------------------------------
# Emote registry
# ---------------------------------------------------------------------------
# Each entry:
#   "keyword": {
#       "self_untargeted":  str,
#       "room_untargeted":  str,
#       "targetable":       bool,
#       "self_targeted":    str | None,
#       "room_targeted":    str | None,
#       "target_targeted":  str | None,
#   }
#
# Tokens: {actor}, {target}, {his_her}, {him_her}, {he_she}

EMOTES = {
    "smile": {
        "self_untargeted": "You smile.",
        "room_untargeted": "{actor} smiles.",
        "targetable": True,
        "self_targeted": "You smile warmly at {target}.",
        "room_targeted": "{actor} smiles warmly at {target}.",
        "target_targeted": "{actor} smiles warmly at you.",
    },
    
    "nod": {
        "self_untargeted": "You nod.",
        "room_untargeted": "{actor} nods.",
        "targetable": True,
        "self_targeted": "You nod at {target}.",
        "room_targeted": "{actor} nods at {target}.",
        "target_targeted": "{actor} nods at you.",
    },
    
    "bow": {
        "self_untargeted": "You bow.",
        "room_untargeted": "{actor} bows.",
        "targetable": True,
        "self_targeted": "You bow to {target}.",
        "room_targeted": "{actor} bows to {target}.",
        "target_targeted": "{actor} bows to you.",
    },
    
    "wave": {
        "self_untargeted": "You wave.",
        "room_untargeted": "{actor} waves.",
        "targetable": True,
        "self_targeted": "You wave at {target}.",
        "room_targeted": "{actor} waves at {target}.",
        "target_targeted": "{actor} waves at you.",
    },
    
    "laugh": {
        "self_untargeted": "You laugh.",
        "room_untargeted": "{actor} laughs.",
        "targetable": True,
        "self_targeted": "You laugh at {target}.",
        "room_targeted": "{actor} laughs at {target}.",
        "target_targeted": "{actor} laughs at you.",
    },
    
    "chuckle": {
        "self_untargeted": "You chuckle.",
        "room_untargeted": "{actor} chuckles.",
        "targetable": True,
        "self_targeted": "You chuckle at {target}.",
        "room_targeted": "{actor} chuckles at {target}.",
        "target_targeted": "{actor} chuckles at you.",
    },
    
    "snicker": {
        "self_untargeted": "You snicker.",
        "room_untargeted": "{actor} snickers.",
        "targetable": True,
        "self_targeted": "You snicker at {target}.",
        "room_targeted": "{actor} snickers at {target}.",
        "target_targeted": "{actor} snickers at you.",
    },
    
    "giggle": {
        "self_untargeted": "You giggle.",
        "room_untargeted": "{actor} giggles.",
        "targetable": True,
        "self_targeted": "You giggle at {target}.",
        "room_targeted": "{actor} giggles at {target}.",
        "target_targeted": "{actor} giggles at you.",
    },
    
    "sigh": {
        "self_untargeted": "You sigh.",
        "room_untargeted": "{actor} sighs.",
        "targetable": True,
        "self_targeted": "You sigh at {target}.",
        "room_targeted": "{actor} sighs at {target}.",
        "target_targeted": "{actor} sighs at you.",
    },
    
    "shrug": {
        "self_untargeted": "You shrug.",
        "room_untargeted": "{actor} shrugs.",
        "targetable": True,
        "self_targeted": "You shrug at {target}.",
        "room_targeted": "{actor} shrugs at {target}.",
        "target_targeted": "{actor} shrugs at you.",
    },
    
    "frown": {
        "self_untargeted": "You frown.",
        "room_untargeted": "{actor} frowns.",
        "targetable": True,
        "self_targeted": "You frown at {target}.",
        "room_targeted": "{actor} frowns at {target}.",
        "target_targeted": "{actor} frowns at you.",
    },
    
    "glare": {
        "self_untargeted": "You glare.",
        "room_untargeted": "{actor} glares.",
        "targetable": True,
        "self_targeted": "You glare at {target}.",
        "room_targeted": "{actor} glares at {target}.",
        "target_targeted": "{actor} glares at you.",
    },
    
    "wink": {
        "self_untargeted": "You wink.",
        "room_untargeted": "{actor} winks.",
        "targetable": True,
        "self_targeted": "You wink at {target}.",
        "room_targeted": "{actor} winks at {target}.",
        "target_targeted": "{actor} winks at you.",
    },
    
    "smirk": {
        "self_untargeted": "You smirk.",
        "room_untargeted": "{actor} smirks.",
        "targetable": True,
        "self_targeted": "You smirk at {target}.",
        "room_targeted": "{actor} smirks at {target}.",
        "target_targeted": "{actor} smirks at you.",
    },
    
    "cheer": {
        "self_untargeted": "You cheer!",
        "room_untargeted": "{actor} cheers!",
        "targetable": True,
        "self_targeted": "You cheer for {target}!",
        "room_targeted": "{actor} cheers for {target}!",
        "target_targeted": "{actor} cheers for you!",
    },
    
    "grin": {
        "self_untargeted": "You grin.",
        "room_untargeted": "{actor} grins.",
        "targetable": True,
        "self_targeted": "You grin at {target}.",
        "room_targeted": "{actor} grins at {target}.",
        "target_targeted": "{actor} grins at you.",
    },
    
    "scowl": {
        "self_untargeted": "You scowl.",
        "room_untargeted": "{actor} scowls.",
        "targetable": True,
        "self_targeted": "You scowl at {target}.",
        "room_targeted": "{actor} scowls at {target}.",
        "target_targeted": "{actor} scowls at you.",
    },
    
    "poke": {
        "self_untargeted": "You poke the air.",
        "room_untargeted": "{actor} pokes the air.",
        "targetable": True,
        "self_targeted": "You poke {target}.",
        "room_targeted": "{actor} pokes {target}.",
        "target_targeted": "{actor} pokes you.",
    },
    
    "point": {
        "self_untargeted": "You point.",
        "room_untargeted": "{actor} points.",
        "targetable": True,
        "self_targeted": "You point at {target}.",
        "room_targeted": "{actor} points at {target}.",
        "target_targeted": "{actor} points at you.",
    },
    
    "nod_slow": {
        "self_untargeted": "You nod slowly.",
        "room_untargeted": "{actor} nods slowly.",
        "targetable": True,
        "self_targeted": "You nod slowly at {target}.",
        "room_targeted": "{actor} nods slowly at {target}.",
        "target_targeted": "{actor} nods slowly at you.",
    },
    
    "shake_head": {
        "self_untargeted": "You shake your head.",
        "room_untargeted": "{actor} shakes {his_her} head.",
        "targetable": True,
        "self_targeted": "You shake your head at {target}.",
        "room_targeted": "{actor} shakes {his_her} head at {target}.",
        "target_targeted": "{actor} shakes {his_her} head at you.",
    },
    
    "clap": {
        "self_untargeted": "You clap.",
        "room_untargeted": "{actor} claps.",
        "targetable": True,
        "self_targeted": "You clap for {target}.",
        "room_targeted": "{actor} claps for {target}.",
        "target_targeted": "{actor} claps for you.",
    },
    
    "crossarms": {
        "self_untargeted": "You cross your arms.",
        "room_untargeted": "{actor} crosses {his_her} arms.",
        "targetable": True,
        "self_targeted": "You cross your arms at {target}.",
        "room_targeted": "{actor} crosses {his_her} arms at {target}.",
        "target_targeted": "{actor} crosses {his_her} arms at you.",
    },
    
    "squint": {
        "self_untargeted": "You squint.",
        "room_untargeted": "{actor} squints.",
        "targetable": True,
        "self_targeted": "You squint at {target}.",
        "room_targeted": "{actor} squints at {target}.",
        "target_targeted": "{actor} squints at you.",
    },
    
    "torex": {
        "self_untargeted": "You tug your beard respectfully.",
        "room_untargeted": "{actor} tugs {his_her} beard respectfully.",
        "targetable": True,
        "self_targeted": "You tug your beard respectfully toward {target}.",
        "room_targeted": "{actor} tugs {his_her} beard respectfully toward {target}.",
        "target_targeted": "{actor} tugs {his_her} beard respectfully toward you.",
    },
}


# ---------------------------------------------------------------------------
# Emote command
# ---------------------------------------------------------------------------


class EmoteCommand:
    """
    Generic emote command. One instance per emote, registered in game_loop.
    """

    def __init__(self, emote_name: str):
        self.emote_name = emote_name

    def execute(self, character, conn, args, session) -> str | None:
        emote = EMOTES.get(self.emote_name)
        if emote is None:
            return f"Unknown emote '{self.emote_name}'."

        actor = character.name.capitalize()
        pronouns = _pronouns(character.gender)

        # --- Targeted ---
        if args and emote["targetable"]:
            target = _resolve_target(conn, character, args)
            if target is None:
                session.send(f"You don't see '{' '.join(args)}' here.\n")
                return None

            target_name = target["name"].capitalize()

            def _fmt(template):
                return template.format(
                    actor=actor,
                    target=target_name,
                    **pronouns,
                )

            # Room sees it
            emit_event(
                conn,
                event_type="room",
                sender_id=character.id,
                location_id=character.location_id,
                message=_fmt(emote["room_targeted"]),
            )

            # Actor sees their own version
            session.send(_fmt(emote["self_targeted"]) + "\n")

            # Target sees their version (players only)
            if target["type"] == "player":
                emit_event(
                    conn,
                    event_type="system",
                    sender_id=target["id"],
                    message=_fmt(emote["target_targeted"]),
                )

            return None

        # --- Targeted but no target provided ---
        if args and not emote["targetable"]:
            session.send(f"You can't target that emote.\n")
            return None

        # --- Untargeted ---
        def _fmt(template):
            return template.format(actor=actor, **pronouns)

        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=_fmt(emote["room_untargeted"]),
        )

        session.send(_fmt(emote["self_untargeted"]) + "\n")
        return None


# ---------------------------------------------------------------------------
# Target resolver
# ---------------------------------------------------------------------------


def _resolve_target(conn, character, args) -> dict | None:
    """Find a player or NPC in the room matching the search string."""
    search = " ".join(args).lower()

    with conn.cursor() as cur:
        # Players first
        cur.execute(
            """
            SELECT id, name FROM characters
            WHERE location_id = %s
              AND is_logged_in = TRUE
              AND id != %s
              AND LOWER(name) LIKE %s
            """,
            (character.location_id, character.id, f"%{search}%"),
        )
        row = cur.fetchone()
    if row:
        return {"type": "player", "id": row[0], "name": row[1]}

    with conn.cursor() as cur:
        # NPCs second
        cur.execute(
            """
            SELECT ni.id, nt.name
            FROM npc_instances ni
            JOIN npc_templates nt ON nt.id = ni.npc_template_id
            WHERE ni.location_id = %s
              AND ni.is_alive = TRUE
              AND LOWER(nt.name) LIKE %s
            """,
            (character.location_id, f"%{search}%"),
        )
        row = cur.fetchone()
    if row:
        return {"type": "npc", "id": row[0], "name": row[1]}

    return None
