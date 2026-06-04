"""
commands/channels.py — Configurable guild and role channels

Each channel is defined by a name and an access check function.
To add a new channel: define a check function and register it in CHANNELS.
"""

from events import emit_event


def _check_class(class_name):
    """Returns a checker that requires a specific class."""
    def check(character):
        return (character.char_class or "").lower() == class_name.lower()
    return check


def _check_staff(character):
    """Staff only."""
    return character.is_staff


def _check_title(title_value):
    """Returns a checker that requires a specific title."""
    def check(character):
        return (getattr(character, "title", "") or "").lower() == title_value.lower()
    return check

def _check_council(character) -> bool:
    """Guildmasters of any guild except thieves."""
    if not character.title_name:
        return False
    if "Guildmaster" not in character.title_name:
        return False
    if (character.title_guild or "").lower() == "thief":
        return False
    return True



# ---------------------------------------------------------------------------
# Channel registry
# Add new channels here — no other changes needed.
# Each entry: "command_keyword": (display_name, access_checker)
# ---------------------------------------------------------------------------

CHANNELS = {
    "chat":     ("Chat",     lambda c: True, "green"),
    "northlands": ("Northlands", lambda c: True, "blue"),
    "merchant": ("Merchant", _check_class("merchant"), "cyan"),
    "fighter":  ("Fighter",  _check_class("fighter"), "cyan"),
    "wizard":   ("Wizard",   _check_class("wizard"), "cyan"),
    "cleric":   ("Cleric",   _check_class("cleric"), "cyan"),
    "thief":    ("Thief",    _check_class("thief"), "cyan"),
    "ranger":   ("Ranger",   _check_class("ranger"), "cyan"),
    "staff":    ("Staff",    _check_staff, "white"),
    "council": ("Council", _check_council, "bright_yellow"),
}


class ChannelCommand:
    """
    Generic channel command. One instance per channel, registered in game_loop.
    """

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

        message = " ".join(args)

        emit_event(
            conn,
            event_type="channel",
            sender_id=character.id,
            channel=self.channel_name,
            message=message,
            color=color,
        )

        return None