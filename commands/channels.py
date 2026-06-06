"""
commands/channels.py — Configurable guild and role channels
"""

from events import emit_event
from commands.emotes import EMOTES, _pronouns



def _check_class(class_name):
    def check(character):
        return (character.char_class or "").lower() == class_name.lower()
    return check


def _check_staff(character):
    return character.is_staff


def _check_title(title_value):
    def check(character):
        return (getattr(character, "title", "") or "").lower() == title_value.lower()
    return check


def _check_council(character) -> bool:
    if not character.title_name:
        return False
    if "Guildmaster" not in character.title_name:
        return False
    if (character.title_guild or "").lower() == "thief":
        return False
    return True


CHANNELS = {
    "chat":       ("Chat",       lambda c: True,              "green"),
    "northlands": ("Northlands", lambda c: True,              "blue"),
    "world":      ("World",      lambda c: True,              "yellow"),
    "merchant":   ("Merchant",   _check_class("merchant"),    "cyan"),
    "fighter":    ("Fighter",    _check_class("fighter"),     "cyan"),
    "wizard":     ("Wizard",     _check_class("wizard"),      "cyan"),
    "cleric":     ("Cleric",     _check_class("cleric"),      "cyan"),
    "thief":      ("Thief",      _check_class("thief"),       "cyan"),
    "ranger":     ("Ranger",     _check_class("ranger"),      "cyan"),
    "staff":      ("Staff",      _check_staff,                "white"),
    "council":    ("Council",    _check_council,              "bright_yellow"),
}


class ChannelCommand:
    
    def __init__(self, channel_name: str):
        self.channel_name = channel_name.lower()
        
    def execute(self, character, conn, args, session):
        entry = CHANNELS.get(self.channel_name)

        if entry is None:
            return f"Unknown channel '{self.channel_name}'."

        display_name, access_check, color = entry

        if not access_check(character):
            return f"You don't have access to the {display_name} channel."

        if not args:
            return f"Say what on {display_name}?"

        raw = " ".join(args)
        actor = character.name.capitalize()
        pronouns = _pronouns(character.gender)

        # --- Emote prefix: fighter ;nod or fighter ;spits on the ground ---
        if raw.startswith(";"):
            emote_text = raw[1:].strip()

            if not emote_text:
                return "Emote what?"

            # Check if it's a registered emote keyword (e.g. ;nod, ;smile tavin)
            emote_parts = emote_text.split()
            first_word  = emote_parts[0].lower()

            if first_word in EMOTES:
                emote = EMOTES[first_word]

                # Targeted registered emote
                if len(emote_parts) > 1 and emote["targetable"]:
                    from commands.emotes import _resolve_target
                    target = _resolve_target(conn, character, emote_parts[1:])
                    if target is None:
                        session.send(f"You don't see '{' '.join(emote_parts[1:])}' here.\n")
                        return None
                    target_name = target["name"].capitalize()
                    room_msg = emote["room_targeted"].format(
                        actor=actor, target=target_name, **pronouns
                    )
                    self_msg = emote["self_targeted"].format(
                        actor=actor, target=target_name, **pronouns
                    )
                else:
                    room_msg = emote["room_untargeted"].format(actor=actor, **pronouns)
                    self_msg = emote["self_untargeted"].format(actor=actor, **pronouns)

            else:
                # Freeform emote — treat as raw action text
                if not emote_text.endswith((".", "!", "?")):
                    emote_text += "."
                room_msg = f"{actor} {emote_text}"

            full_message = f"<{display_name}> {room_msg}"

            emit_event(
                conn,
                event_type="channel",
                sender_id=character.id,
                channel=self.channel_name,
                message=full_message,
                color=color,
            )

            return None

        # --- Normal speech ---
        emit_event(
            conn,
            event_type="channel",
            sender_id=character.id,
            channel=self.channel_name,
            message=raw,
            color=color,
        )

        return None