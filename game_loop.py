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
from command_list_temp import COMMANDS
from events import emit_event
from threads.bell import start_bell_thread


from commands.look import LookCommand
from commands.smell import SmellCommand
from commands.listen import ListenCommand
from commands.exits import ExitsCommand
from commands.score import ScoreCommand
from commands.hp import HpCommand
from commands.time import TimeCommand
from commands.who import WhoCommand
from commands.finger import FingerCommand

from commands.say import SayCommand
from commands.emote import EmoteCommand
from commands.tell import TellCommand
from commands.chat import ChatCommand

from combat.attack import AttackCommand
from combat.flee   import FleeCommand

from commands.spawn import SpawnCommand
from commands.summon import SummonCommand
from commands.spawnitem import SpawnItemCommand
from commands.proclaim import ProclaimCommand
from commands.world import WorldCommand

from commands.items import GetCommand, DropCommand, InventoryCommand


# ---------------------------------------------------------------------------
# Direction aliases
# ---------------------------------------------------------------------------

# These are shorthand aliases only.
# Actual valid exits are determined dynamically from the exits table.
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

COMMANDS = {
    "look":      LookCommand(),
    "l":         LookCommand(),

    "spawn":     SpawnCommand(),
    "spawnitem": SpawnItemCommand(),
    "summon":    SummonCommand(),
    "proclaim":  ProclaimCommand(),

    "say":       SayCommand(),
    ";":         EmoteCommand(),
    "emote":     EmoteCommand(),
    "tell":      TellCommand(),
    "chat":      ChatCommand(),

    "world":     WorldCommand(),

    "exits":     ExitsCommand(),

    "i":         InventoryCommand(),
    "inventory": InventoryCommand(),
    "get":       GetCommand(),
    "drop":      DropCommand(),

    "score":     ScoreCommand(),
    "hp":        HpCommand(),
    "who":       WhoCommand(),
    "smell":     SmellCommand(),
    "listen":    ListenCommand(),
    "time":      TimeCommand(),
    "finger":    FingerCommand(),

    "attack":    AttackCommand(),
    "flee":      FleeCommand(),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(raw: str) -> tuple[str, list[str]]:
    """
    Split raw input into (verb, args).

    Returns:
        ("", []) for empty input.
    """

    if raw.startswith(";"):
        raw = "emote " + raw[1:].lstrip()

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
    Main game loop.

    Responsibilities:
      - Load player
      - Start broadcast polling
      - Handle commands
      - Handle movement
      - Clean shutdown
    """

    # -------------------------------------------------------------------
    # Initial load
    # -------------------------------------------------------------------

    with get_connection() as conn:
        character = Character.get_by_id(conn, character_id)

    if character is None:
        print_error("Could not load character. Returning to menu.")
        return

    print_success(f"Entering the world as {character.name.capitalize()}...")

    # -------------------------------------------------------------------
    # Broadcast startup
    # -------------------------------------------------------------------

    with get_connection() as conn:
        starting_broadcast_id = BroadcastMessage.get_latest_id(conn)

    poller = BroadcastPoller(starting_broadcast_id, character_id)
    poller.start()

    start_bell_thread(emit_event, get_connection)

    did_quit_cleanly = False

    try:

        # ---------------------------------------------------------------
        # Initial room look
        # ---------------------------------------------------------------

        with get_connection() as conn:
            character = Character.get_by_id(conn, character_id)
            _run_command(COMMANDS["look"], character, conn, [])

        # ---------------------------------------------------------------
        # Main loop
        # ---------------------------------------------------------------

        while True:

            raw = prompt(">")

            if not raw:
                continue

            verb, args = _parse(raw)

            # -----------------------------------------------------------
            # Quit
            # -----------------------------------------------------------

            if verb in ("quit", "exit", "q"):

                blank()

                print_flavor(
                    f"{character.name.capitalize()} rests for now. Farewell."
                )

                blank()

                with get_connection() as conn:

                    character = Character.get_by_id(conn, character_id)
                    room = character.get_room(conn)

                    emit_event(
                        conn,
                        event_type="room",
                        sender_id=character_id,
                        location_id=room.id,
                        message=f"{character.name.capitalize()} fades from the world.",
                    )

                did_quit_cleanly = True
                break

            # -----------------------------------------------------------
            # Everything else
            # -----------------------------------------------------------

            with get_connection() as conn:

                character = Character.get_by_id(conn, character_id)
                room = character.get_room(conn)

                # -------------------------------------------------------
                # Dynamic exit traversal
                # -------------------------------------------------------

                # Resolve shorthand aliases first.
                # Example: "n" -> "north"
                direction = _DIRS.get(verb, verb)

                exit_data = room.get_exit(conn, direction)

                # -------------------------------------------------------
                # Valid exit found
                # -------------------------------------------------------

                if exit_data is not None:

                    if exit_data["is_locked"]:
                        print_error("That way is locked.")
                        continue

                    old_room = room.id
                    new_room = exit_data["to_location"]

                    character.move_to(conn, new_room)

                    # Refresh room after movement
                    character = Character.get_by_id(conn, character_id)

                    # Auto-look
                    _run_command(COMMANDS["look"], character, conn, [])

                    # Departure event
                    emit_event(
                        conn,
                        event_type="room",
                        sender_id=character.id,
                        location_id=old_room,
                        message=f"{character.name} leaves {direction}.",
                    )

                    # Arrival event
                    emit_event(
                        conn,
                        event_type="room",
                        sender_id=character.id,
                        location_id=new_room,
                        message=f"{character.name} arrives.",
                    )

                    continue

                # -------------------------------------------------------
                # Registered commands
                # -------------------------------------------------------

                if verb in COMMANDS:

                    _run_command(
                        COMMANDS[verb],
                        character,
                        conn,
                        args,
                    )

                    continue

                # -------------------------------------------------------
                # Unknown
                # -------------------------------------------------------

                print_error(
                    f"Unknown command '{verb}'. "
                    f"Try: look, north, inside, quit."
                )

    finally:

        # ---------------------------------------------------------------
        # Always stop background poller
        # ---------------------------------------------------------------

        poller.stop()

        # ---------------------------------------------------------------
        # Always mark player offline
        # ---------------------------------------------------------------

        try:

            with get_connection() as conn:

                with conn.cursor() as cur:

                    cur.execute(
                        """
                        UPDATE characters
                        SET is_logged_in = FALSE
                        WHERE id = %s
                        """,
                        (character_id,),
                    )

                conn.commit()

        except Exception as e:

            print(f"[FATAL] Failed to mark character offline: {e}")


# ---------------------------------------------------------------------------
# Network hook
# ---------------------------------------------------------------------------

# Not currently in use.
def run_command_for_network(character_id: int, raw: str):

    parts = raw.strip().split()

    if not parts:
        return ""

    verb = parts[0].lower()
    args = parts[1:]

    with get_connection() as conn:

        character = Character.get_by_id(conn, character_id)

        if character is None:
            return "Character not found."

        room = character.get_room(conn)

        # Allow custom exits over network too
        direction = _DIRS.get(verb, verb)

        exit_data = room.get_exit(conn, direction)

        if exit_data is not None:

            if exit_data["is_locked"]:
                return "That way is locked."

            character.move_to(conn, exit_data["to_location"])

            return f"You go {direction}."

        # Registered command
        if verb in COMMANDS:

            cmd = COMMANDS[verb]

            return cmd.execute(character, conn, args)

        return f"Unknown command: {verb}"