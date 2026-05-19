"""
main.py — Game entry point

Run this file to start the game.

Shows the main menu and routes the player to login,
character creation, or exit.
"""

from db import close_pool
from character_creation import run_character_creation
from login import run_login
from game_loop import run_game_loop
from output import blank, console, print_error, print_flavor, prompt, rule, COLOR_PROMPT, COLOR_TITLE


TITLE = r"""
============================================================================================

             /\                                                        /\
            |  |                                                      |  |
           /----\                                                    /----\
          [______]                                                  [______]
           |    |         _____                        _____         |    |
           |[]  |        [     ]                      [     ]        |  []|
           |    |       [_______][ ][ ][ ][][ ][ ][ ][_______]       |    |
           |    [ ][ ][ ]|     |  ,----------------,  |     |[ ][ ][ ]    |
           |             |     |/'    ____..____    '\|     |             |
            \  []        |     |    /'    ||    '\    |     |        []  /
             |      []   |     |   |o     ||     o|   |     |  []       |
             |           |  _  |   |     _||_     |   |  _  |           |
             |   []      | (_) |   |    (_||_)    |   | (_) |       []  |
             |           |     |   |     (||)     |   |     |           |
             |           |     |   |      ||      |   |     |           |
           /''           |     |   |o     ||     o|   |     |           ''\
          [_____________[_______]--'------''------'--[_______]_____________]

 _______  _______ _________          _______ _________ _        ______   _______  _______ 
(  ____ )(  ___  )\__   __/|\     /|(  ____ \\__   __/( (    /|(  __  \ (  ____ \(  ____ )
| (    )|| (   ) |   ) (   | )   ( || (    \/   ) (   |  \  ( || (  \  )| (    \/| (    )|
| (____)|| (___) |   | |   | (___) || (__       | |   |   \ | || |   ) || (__    | (____)|
|  _____)|  ___  |   | |   |  ___  ||  __)      | |   | (\ \) || |   | ||  __)   |     __)
| (      | (   ) |   | |   | (   ) || (         | |   | | \   || |   ) || (      | (\ (   
| )      | )   ( |   | |   | )   ( || )      ___) (___| )  \  || (__/  )| (____/\| ) \ \__
|/       |/     \|   )_(   |/     \||/       \_______/|/    )_)(______/ (_______/|/   \__/

=============================================================================================
Welcome to the realm, hero!
============================================================================================="""


def show_main_menu() -> None:
    console.print(TITLE, style=None)
    blank()
    console.print(f"  [1] Create new character")
    console.print(f"  [2] Login")
    console.print(f"  [3] Quit")
    blank()


def main() -> None:
    """
    Main menu loop. Runs until the player chooses Quit.

    After a successful login or character creation, drops into the game loop.
    When the player exits the game loop, they return here — not to their OS.
    This lets someone switch characters without restarting the program.
    """
    try:
        while True:
            show_main_menu()
            choice = prompt(">")

            if choice == "1":
                character_id = run_character_creation()
                if character_id is not None:
                    run_game_loop(character_id)

            elif choice == "2":
                character_id = run_login()
                if character_id is not None:
                    run_game_loop(character_id)

            elif choice == "3":
                blank()
                print_flavor("Goodbye.")
                blank()
                break

            else:
                print_error("Please enter 1, 2, or 3.")
                blank()

    finally:
        # ALWAYS close the DB pool cleanly on exit, even after a crash
        close_pool()


if __name__ == "__main__":
    main()