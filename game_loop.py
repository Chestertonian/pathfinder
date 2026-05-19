"""
game_loop.py — Main game loop

Thin dispatcher. Its only job is to:
  1. Load the character
  2. Start the broadcast poller
  3. Read input, parse it, hand off to the right Command
  4. Print the result
  5. Stop the poller on quit

To add a new command: write a new file in commands/, import it here,
and add it to the COMMANDS dict. Nothing else changes.

Performance rule: each command gets exactly ONE connection, opened here
and passed through. No command should open its own connection.
"""

from db import get_connection
from models import BroadcastMessage, Character
from output import blank, console, print_error, print_flavor, print_success, prompt
from broadcast import BroadcastPoller

from commands.look import LookCommand
from commands.say import SayCommand
from commands.emote import EmoteCommand
from commands.spawn import SpawnCommand
from commands.summon import SummonCommand
from commands.proclaim import ProclaimCommand


# ---------------------------------------------------------------------------
# Direction aliases
# ---------------------------------------------------------------------------
_DIRS = {
    "n": "north", "north": "north",
    "s": "south", "south": "south",
    "e": "east",  "east":  "east",
    "w": "west",  "west":  "west",
    "ne": "northeast", "northeast": "northeast",
    "nw": "northwest", "northwest": "northwest",
    "se": "southeast", "southeast": "southeast",
    "sw": "southwest", "southwest": "southwest",
    "u":  "up",   "up":   "up",
    "d":  "down", "down": "down",
}

# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------
# All commands live here. Staff-only commands are still registered globally
# — the command itself checks character.is_staff and refuses if not staff.
# This keeps the dispatcher simple and uniform.

COMMANDS = {
    "look":     LookCommand(),
    "l":        LookCommand(),
    "spawn":    SpawnCommand(),
    "summon":   SummonCommand(),
    "proclaim": ProclaimCommand(),
    "say":      SayCommand(),
    ";":        EmoteCommand(),
    "emote":    EmoteCommand()
    # "exits":     ExitsCommand(),
    # "inventory": InventoryCommand(),
    # "score":     ScoreCommand(),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(raw: str) -> tuple[str, list[str]]:
    """Split raw input into (verb, args). Returns ("", []) for empty input."""
    parts = raw.strip().split()
    if not parts:
        return ("", [])
    return (parts[0].lower(), parts[1:])


def _run_command(command, character, conn, args):
    """Execute a command and print its string output if any."""
    output = command.execute(character, conn, args)
    if output:
        console.print(output)


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def run_game_loop(character_id: int) -> None:
    """
    Main game loop. One DB connection per command; no command opens its own.

    Starts a BroadcastPoller in the background before the loop begins,
    and stops it cleanly when the player quits.
    """

    # Initial load
    with get_connection() as conn:
        character = Character.get_by_id(conn, character_id)

    if character is None:
        print_error("Could not load character. Returning to menu.")
        return

    print_success(f"Entering the world as {character.name.capitalize()}...")

    # Get the current highest broadcast ID so we only show future messages,
    # not old history from before this session started.
    with get_connection() as conn:
        starting_broadcast_id = BroadcastMessage.get_latest_id(conn)

    # Start the background broadcast poller
    poller = BroadcastPoller(starting_broadcast_id, character_id)
    poller.start()

    try:
        # Show starting room
        with get_connection() as conn:
            character = Character.get_by_id(conn, character_id)
            _run_command(COMMANDS["look"], character, conn, [])

        # ── Main loop ─────────────────────────────────────────────────────
        while True:
            raw = prompt(">")
            if not raw:
                continue

            verb, args = _parse(raw)

            # ── Quit ──────────────────────────────────────────────────────
            if verb in ("quit", "exit", "q"):
                blank()
                print_flavor(f"{character.name.capitalize()} rests for now. Farewell.")
                blank()
                break

            # ── Movement ──────────────────────────────────────────────────
            elif verb in _DIRS:
                direction = _DIRS[verb]
                with get_connection() as conn:
                    character = Character.get_by_id(conn, character_id)
                    room = character.get_room(conn)
                    exit_data = room.get_exit(conn, direction)

                    if exit_data is None:
                        print_error(f"You cannot go {direction} from here.")
                        continue
                    if exit_data["is_locked"]:
                        print_error("That way is locked.")
                        BroadcastMessage.announce(conn, room.id, "It's locked.", sender_character_id=None)
                        continue
                    
                    BroadcastMessage.announce(conn, character.get_room(conn).id, f"{character.name} moves away.", sender_character_id=character.id)
                    character.move_to(conn, exit_data["to_location"])
                    _run_command(COMMANDS["look"], character, conn, [])
                    BroadcastMessage.announce(conn, character.get_room(conn).id, f"{character.name} enters.", sender_character_id=character.id)

            # ── Registered commands ────────────────────────────────────────
            elif verb in COMMANDS:
                with get_connection() as conn:
                    character = Character.get_by_id(conn, character_id)
                    _run_command(COMMANDS[verb], character, conn, args)

            # ── Unknown ───────────────────────────────────────────────────
            else:
                print_error(f"Unknown command '{verb}'. Try: look, north, south, quit.")

    finally:
        # Always stop the poller, even if the loop crashes
        poller.stop()