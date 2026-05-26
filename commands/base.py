"""
commands/base.py — Base class for all commands

Every command in the game inherits from Command and implements execute().
The consistent signature (character, conn, args) means the dispatcher
in game_loop.py never needs to know what a command does internally.
"""


class Command:
    def execute(self, character, conn, args: list[str], session) -> str:
        """
        Execute this command and return output as a string.

        Args:
            character: a Character model instance (the acting player)
            conn:      an active DB connection from get_connection()
            args:      list of remaining words after the verb
                       e.g. "look at sword" → args = ["at", "sword"]

        Returns a string to be printed by the game loop.
        Returning an empty string is valid (no output).
        """
        raise NotImplementedError("Command subclasses must implement execute().")