"""
server.py — TCP game server

Run this to host the game.
Players connect with client.py.

Each connected player gets their own thread,
which runs an independent game session.

Usage:
    python server.py
"""

import socket
import threading

from db import get_connection, close_pool
from login import run_login
from character_creation import run_character_creation
# from game_loop import run_game_loop_for_client


HOST = "0.0.0.0"   # Accept connections from anywhere
PORT = 3000

class ClientSession:
    """
    Wraps a TCP socket connection for one player.

    Provides simple send/recv so game code never
    touches raw sockets directly.
    """

    def __init__(self, conn: socket.socket):
        self.conn = conn
        self.file = conn.makefile("r", encoding="utf-8")  
        # makefile lets us use readline() instead of 
        # manually handling byte buffers

    def send(self, text: str) -> None:
        """Send text to this player's terminal."""
        try:
            self.conn.sendall(text.encode("utf-8"))
        except OSError:
            pass  # Player disconnected

    def recv(self) -> str | None:
        """
        Read one line of input from the player.
        Returns None if they disconnected.
        """
        try:
            line = self.file.readline()
            if not line:
                return None  # Disconnected
            return line.strip()
        except OSError:
            return None

def handle_client(conn: socket.socket, addr):
    """
    Runs in its own thread for each connected player.

    Responsible for:
    - Wrapping the socket in a session
    - Running login/character creation
    - Handing off to the game loop
    - Cleaning up on disconnect
    """

    print(f"[server] Connection from {addr}")

    session = ClientSession(conn)

    try:
        session.send("Welcome to Pathfinder!\n")
        session.send("[1] Create character\n[2] Login\n[3] Quit\n")

        while True:
            choice = session.recv()

            if choice is None or choice == "3":
                session.send("Goodbye.\n")
                break

            elif choice == "1":
                character_id = run_character_creation(session)
                if character_id:
                    print("TBD")
                    #run_game_loop_for_client(character_id, session)
                break

            elif choice == "2":
                character_id = run_login(session)
                if character_id:
                    print("TBD")
                    #run_game_loop_for_client(character_id, session)
                break

            else:
                session.send("Please enter 1, 2, or 3.\n")

    except Exception as e:
        print(f"[server] Error with {addr}: {e}")

    finally:
        print(f"[server] {addr} disconnected.")
        conn.close()


def start_server():
    """
    Binds to HOST:PORT and accepts connections forever.
    Each connection spawns a new thread.
    """

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # This lets you restart the server quickly without
    # "address already in use" errors
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"[server] Listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server_socket.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True,   # Thread dies automatically if server stops
            )
            thread.start()

    except KeyboardInterrupt:
        print("\n[server] Shutting down.")

    finally:
        server_socket.close()
        close_pool()


if __name__ == "__main__":
    start_server()