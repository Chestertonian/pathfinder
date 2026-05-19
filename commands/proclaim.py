"""
commands/proclaim.py — ProclaimCommand (staff only)

Usage:
    proclaim

Walks staff through:
  1. Color picker
  2. Border option (yes/no — border rendering is handled by the caller)
  3. Multi-line message composer (END to send, CANCEL to abort)
  4. Preview + confirm

The message is written to broadcast_messages and displayed on all
connected clients within a few seconds via BroadcastPoller.
"""

from commands.base import Command
from models import BroadcastMessage
from output import blank, console, prompt


# ---------------------------------------------------------------------------
# Available colors
# (label shown in menu, Rich color string stored in DB and used at print time)
# ---------------------------------------------------------------------------
PROCLAIM_COLORS = [
    ("White",        "white"),
    ("Soft Gold",    "gold1"),
    ("Amber",        "dark_orange"),
    ("Red",          "red3"),
    ("Crimson",      "dark_red"),
    ("Green",        "green4"),
    ("Teal",         "dark_cyan"),
    ("Sky Blue",     "steel_blue1"),
    ("Royal Blue",   "blue1"),
    ("Purple",       "medium_purple"),
    ("Pink",         "deep_pink4"),
    ("Silver",       "grey74"),
]


class ProclaimCommand(Command):
    def execute(self, character, conn, args: list[str]) -> str:

        # ── Staff check ───────────────────────────────────────────────────
        if not character.is_staff:
            return "You don't have permission to do that."

        # ── Step 1: Color picker ──────────────────────────────────────────
        blank()
        console.print("Choose a color:")
        blank()
        for i, (label, rich_color) in enumerate(PROCLAIM_COLORS, 1):
            console.print(f"  [{rich_color}][{i:>2}] {label}[/{rich_color}]")
        blank()

        color_str = "white"
        while True:
            raw = prompt(">").strip()
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(PROCLAIM_COLORS):
                    color_str = PROCLAIM_COLORS[idx][1]
                    break
            console.print(f"  Enter a number between 1 and {len(PROCLAIM_COLORS)}.")

        # ── Step 2: Border option ─────────────────────────────────────────
        blank()
        console.print("Add a decorative border?")
        blank()
        console.print("  [1] No border")
        console.print("  [2] Yes — add border")
        blank()

        use_border = False
        while True:
            raw = prompt(">").strip()
            if raw == "1":
                use_border = False
                break
            elif raw == "2":
                use_border = True
                break
            console.print("  Enter 1 or 2.")

        # ── Step 3: Multi-line composer ───────────────────────────────────
        blank()
        console.print("Enter your proclamation. Type END to send, CANCEL to abort.")
        blank()

        lines = []
        while True:
            line = prompt("  |")

            if line.upper() == "CANCEL":
                blank()
                return "Proclamation cancelled."

            if line.upper() == "END":
                break

            lines.append(line)

        if not lines:
            return "Nothing to proclaim."

        message = "\n".join(lines)

        if len(message) > 1000:
            return "Message too long (max 1000 characters)."

        # ── Step 4: Preview ───────────────────────────────────────────────
        blank()
        console.print("Preview:")
        blank()
        _print_message(message, color_str, use_border)
        blank()
        console.print("  [1] Send")
        console.print("  [2] Cancel")
        blank()

        raw = prompt(">").strip()
        if raw != "1":
            return "Proclamation cancelled."

        # ── Step 5: Send ──────────────────────────────────────────────────
        BroadcastMessage.send(conn, character.id, message, color_str, use_border)

        blank()
        return "Proclaimed."


# ---------------------------------------------------------------------------
# Shared rendering helper
# ---------------------------------------------------------------------------
# This function is also imported by broadcast.py to render incoming messages
# consistently, so the preview and the live display look identical.

def _print_message(message: str, color: str, use_border: bool) -> None:
    """
    Print a proclaim message to the terminal.
    If use_border is True, wraps the message in a decorative border.
    The actual border characters are defined here — edit to your taste.
    """
    if use_border:
        _print_bordered(message, color)
    else:
        console.print(f"[bold {color}]{message}[/bold {color}]")


def _print_bordered(message: str, color: str) -> None:
    """
    Render the message inside a simple ASCII border.
    Replace the border characters below with whatever you prefer.
    """
    lines = message.splitlines()
    width = max(len(line) for line in lines) + 4  # padding on each side

    top    = "O" + "=" * width + '''O'''
    bottom = "O" + "=" * width + "O"
    empty  = "|" + " " * width + "|"

    console.print(f"[bold {color}]{top}[/bold {color}]")
    console.print(f"[bold {color}]{empty}[/bold {color}]")
    for line in lines:
        padded = f"  {line:<{width - 2}}  "
        console.print(f"[bold {color}]|{padded}|[/bold {color}]")
    console.print(f"[bold {color}]{empty}[/bold {color}]")
    console.print(f"[bold {color}]{bottom}[/bold {color}]")