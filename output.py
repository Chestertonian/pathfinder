"""
output.py — Centralized display and styling module

All game output should go through this module rather than
calling print() or Rich directly in other files.

This means if you want to change a color or style, you change
it here once and it updates everywhere.

Usage:
    from output import print_error, print_success, print_info, rule, prompt

Install Rich first:
    pip install rich
"""

from rich.console import Console
from rich.rule import Rule

# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------
# width=90 enforces line wrapping at 90 characters everywhere.
# highlight=False stops Rich from auto-coloring numbers and strings.
# ---------------------------------------------------------------------------
console = Console(highlight=False, width=90)


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
# Kept minimal. Most game text is plain white.
# Color is reserved for things that genuinely need to stand out.
# ---------------------------------------------------------------------------

COLOR_TITLE   = "bold white"   # Section headers, room names, menu options
COLOR_PROMPT  = "bold white"   # Input prompts
COLOR_SUCCESS = "white"        # Login success, positive outcomes
COLOR_ERROR   = "bold red"     # Errors, warnings — the one place we use color
COLOR_INFO    = "white"        # Neutral text, instructions
COLOR_STAT    = "white"        # Stats and numbers
COLOR_FLAVOR  = "white"        # Room descriptions, narrative text


# ---------------------------------------------------------------------------
# Core print helpers
# ---------------------------------------------------------------------------

def print_title(text: str) -> None:
    """Bold section header — CHARACTER CREATION, LOGIN, etc."""
    console.print(f"\n{text}", style=COLOR_TITLE)


def print_success(text: str) -> None:
    """Positive outcome — character created, login success, etc."""
    console.print(text, style=COLOR_SUCCESS)


def print_error(text: str) -> None:
    """Errors and warnings. The only place we consistently use red."""
    console.print(text, style=COLOR_ERROR)


def print_info(text: str) -> None:
    """Neutral informational text — instructions, ambient details."""
    console.print(text, style=COLOR_INFO)


def print_flavor(text: str) -> None:
    """Room descriptions and narrative prose. Plain white, wraps at 90."""
    console.print(text, style=COLOR_FLAVOR)


def print_stat(label: str, value) -> None:
    """A labeled stat line, e.g. 'STR  14'."""
    console.print(f"{label:<12}{value}")


def rule(title: str = "") -> None:
    """A horizontal divider, optionally with a centered title."""
    console.print(Rule(title=title, style="white"))


def blank() -> None:
    """Print an empty line."""
    console.print()


# ---------------------------------------------------------------------------
# Input helper
# ---------------------------------------------------------------------------

def prompt(text: str) -> str:
    """
    Input prompt. Returns the stripped string the player typed.
    Use this instead of input() everywhere for consistency.

    Example:
        name = prompt("Enter your name:")
    """
    return console.input(f"[bold white]{text}[/bold white] ").strip()