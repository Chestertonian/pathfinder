"""
commands/proclaim.py — ProclaimCommand (staff only)
"""

from commands.base import Command
from events import emit_event

PROCLAIM_COLORS = [
    ("White",       "white"),
    ("Soft Gold",   "gold1"),
    ("Amber",       "dark_orange"),
    ("Red",         "red3"),
    ("Crimson",     "dark_red"),
    ("Green",       "green4"),
    ("Teal",        "dark_cyan"),
    ("Sky Blue",    "steel_blue1"),
    ("Royal Blue",  "blue1"),
    ("Purple",      "medium_purple"),
    ("Pink",        "deep_pink4"),
    ("Silver",      "grey74"),
]


class ProclaimCommand(Command):
    def execute(self, character, conn, args, session):

        if not character.is_staff:
            return "You don't have permission to do that."

        # Step 1: Color picker
        lines = ["\nChoose a color:\n"]
        for i, (label, _) in enumerate(PROCLAIM_COLORS, 1):
            lines.append(f"  [{i:>2}] {label}")
        lines.append("")
        session.send("\n".join(lines) + "\n")

        color_str = "white"
        while True:
            session.send("> ")
            raw = session.recv() or ""
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(PROCLAIM_COLORS):
                    color_str = PROCLAIM_COLORS[idx][1]
                    break
            session.send(f"Enter a number between 1 and {len(PROCLAIM_COLORS)}.\n")

        # Step 2: Border option
        session.send("\nAdd a decorative border?\n\n")
        session.send("  [1] No border\n  [2] Yes — add border\n\n")

        use_border = False
        while True:
            session.send("> ")
            raw = session.recv() or ""
            if raw == "1":
                use_border = False
                break
            elif raw == "2":
                use_border = True
                break
            session.send("Enter 1 or 2.\n")

        # Step 3: Multi-line composer
        session.send("\nEnter your proclamation. Type END to send, CANCEL to abort.\n\n")

        lines = []
        while True:
            session.send("  | ")
            line = session.recv() or ""

            if line.upper() == "CANCEL":
                return "Proclamation cancelled."

            if line.upper() == "END":
                break

            lines.append(line)

        if not lines:
            return "Nothing to proclaim."

        message = "\n".join(lines)

        if len(message) > 1000:
            return "Message too long (max 1000 characters)."

        # Step 4: Preview
        session.send("\nPreview:\n\n")
        session.send(render_proclaim(message, color_str, use_border))
        session.send("\n  [1] Send\n  [2] Cancel\n\n")

        session.send("> ")
        raw = session.recv() or ""
        if raw != "1":
            return "Proclamation cancelled."

        # Step 5: Send
        emit_event(
            conn,
            event_type="global",
            sender_id=character.id,
            message=message,
            color=color_str,
            use_border=use_border,
        )

        return "Proclaimed."


# ---------------------------------------------------------------------------
# Shared rendering helper — now returns a string instead of printing
# ---------------------------------------------------------------------------

def render_proclaim(message: str, color: str, use_border: bool) -> str:
    # CHANGED: returns string instead of printing
    if use_border:
        return _render_bordered(message)
    else:
        return message + "\n"


def _render_bordered(message: str) -> str:
    # CHANGED: returns string instead of printing
    lines = message.splitlines()
    width = max(len(line) for line in lines) + 4

    top    = "O" + "=" * width + "O"
    bottom = "O" + "=" * width + "O"
    empty  = "|" + " " * width + "|"

    result = []
    result.append(top)
    result.append(empty)
    for line in lines:
        padded = f"  {line:<{width - 2}}  "
        result.append(f"|{padded}|")
    result.append(empty)
    result.append(bottom)

    return "\n".join(result) + "\n"