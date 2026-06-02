"""
commands/proclaim.py — ProclaimCommand (staff only)
"""

from io import StringIO
from rich.console import Console

from commands.base import Command
from events import emit_event
import textwrap

# Standard 16 ANSI colors — (display label, Rich markup name)
PROCLAIM_COLORS = [
    ("White",           "white"),
    ("Bright White",    "bright_white"),
    ("Silver",          "bright_black"),        # bright black = grey
    ("Black",           "black"),
    ("Red",             "red"),
    ("Bright Red",      "bright_red"),
    ("Yellow",          "yellow"),
    ("Bright Yellow",   "bright_yellow"),
    ("Green",           "green"),
    ("Bright Green",    "bright_green"),
    ("Cyan",            "cyan"),
    ("Bright Cyan",     "bright_cyan"),
    ("Blue",            "blue"),
    ("Bright Blue",     "bright_blue"),
    ("Magenta",         "magenta"),
    ("Bright Magenta",  "bright_magenta"),
]

PROCLAIM_STYLES = [
    ("Plain centered",  "plain_centered"),
    ("Divider",         "divider"),
    ("Corner accent",   "corner_accent"),
    ("Single box",      "box_single"),
    ("Double box",      "box_double"),
]


def to_ansi(markup: str) -> str:
    buf = StringIO()
    c = Console(file=buf, highlight=False, force_terminal=True)
    c.print(markup, end="")
    return buf.getvalue()


class ProclaimCommand(Command):
    def execute(self, character, conn, args, session):

        if not character.is_staff:
            return "You don't have permission to do that."

        # Step 1: Color picker — two columns so 16 options aren't a wall of text
        lines = ["\nChoose a color:\n"]
        pairs = list(enumerate(PROCLAIM_COLORS, 1))
        for i in range(0, len(pairs), 2):
            left_num,  (left_label,  _) = pairs[i]
            if i + 1 < len(pairs):
                right_num, (right_label, _) = pairs[i + 1]
                lines.append(f"  [{left_num:>2}] {left_label:<20}  [{right_num:>2}] {right_label}")
            else:
                lines.append(f"  [{left_num:>2}] {left_label}")
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

        # Step 2: Style picker
        lines = ["\nChoose a style:\n"]
        for i, (label, _) in enumerate(PROCLAIM_STYLES, 1):
            lines.append(f"  [{i}] {label}")
        lines.append("")
        session.send("\n".join(lines) + "\n")

        style_str = "plain_centered"
        while True:
            session.send("> ")
            raw = session.recv() or ""
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(PROCLAIM_STYLES):
                    style_str = PROCLAIM_STYLES[idx][1]
                    break
            session.send(f"Enter a number between 1 and {len(PROCLAIM_STYLES)}.\n")

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
        session.send(render_proclaim(message, color_str, style_str))
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
            style=style_str,
        )

        return "Proclaimed."


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_proclaim(message: str, color: str, style: str) -> str:
    """
    Render a proclamation with the given style and color.
    style can be: plain_centered | divider | corner_accent | box_single | box_double

    Backwards compatibility: if style is a bool (old use_border calls),
    treat True as box_single and False as plain_centered.
    """
    if isinstance(style, bool):
        style = "box_single" if style else "plain_centered"

    _styles = {
        "plain_centered": _plain_centered,
        "divider":        _divider,
        "corner_accent":  _corner_accent,
        "box_single":     _box_single,
        "box_double":     _box_double,
    }

    render_fn = _styles.get(style, _plain_centered)
    raw = render_fn(message)

    return to_ansi(f"[{color}]{raw}[/{color}]")


# ---------------------------------------------------------------------------
# Style implementations
# ---------------------------------------------------------------------------

WIDTH = 60      # total display width all styles align to


def _plain_centered(message: str) -> str:
    """
    Simple centered text.
    """
    lines = []
    lines.append("\n")
    for line in message.splitlines():
        lines.append(line.center(WIDTH))
    lines.append("\n")
    return "\n".join(lines)


def _divider(message: str) -> str:
    """
    Text between two spaced dividers.
    """
    divider = "- " * (WIDTH // 2)
    lines = []
    lines.append("\n")
    lines.append(divider)
    for line in message.splitlines():
        lines.append(line.center(WIDTH))
    lines.append(divider)
    lines.append("\n")
    return "\n".join(lines)


def _corner_accent(message: str) -> str:
    """
    Asterisk corners, centered text. """
    corner_line = "*" + " " * (WIDTH - 2) + "*"
    lines = []
    lines.append("\n")
    lines.append(corner_line)
    for line in message.splitlines():
        lines.append(line.center(WIDTH))
    lines.append(corner_line)
    lines.append("\n")
    return "\n".join(lines)


def _box_single(message: str) -> str:
    inner = WIDTH - 4
    wrapped_lines = []
    for line in message.splitlines():
        wrapped_lines.extend(textwrap.wrap(line, width=inner) or [""])

    lines = []
    lines.append("\n")
    lines.append("+" + "-" * (WIDTH - 2) + "+")
    lines.append("|" + " " * (WIDTH - 2) + "|")
    for line in wrapped_lines:
        padded = f"  {line:<{inner}}  "
        lines.append(f"|{padded}|")
    lines.append("|" + " " * (WIDTH - 2) + "|")
    lines.append("+" + "-" * (WIDTH - 2) + "+")
    lines.append("\n")
    return "\n".join(lines)


def _box_double(message: str) -> str:
    inner = WIDTH - 4
    wrapped_lines = []
    for line in message.splitlines():
        wrapped_lines.extend(textwrap.wrap(line, width=inner) or [""])

    lines = []
    lines.append("\n")
    lines.append("//" + "=" * (WIDTH - 2) + "\\\\")
    lines.append("||" + " " * (WIDTH - 2) + "||")
    for line in wrapped_lines:
        padded = f"  {line:<{inner}}  "
        lines.append(f"||{padded}||")
    lines.append("||" + " " * (WIDTH - 2) + "||")
    lines.append("\\\\" + "=" * (WIDTH - 2) + "//")
    lines.append("\n")
    return "\n".join(lines)