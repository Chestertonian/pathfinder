"""
client.py — Game client

Connects to the game server and lets you play.

Usage:
    python client.py
    python client.py --host 0.tcp.ngrok.io --port 12345
"""

import socket
import threading
import argparse
import sys
import textwrap

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 3000


def receive_loop(sock: socket.socket) -> None:
    """
    Runs in a background thread.
    Continuously reads text from the server and prints it.
    Exits when the server disconnects.
    """
    try:
        file = sock.makefile("r", encoding="utf-8")
        while True:
            line = file.readline()
            if not line:
                # Server closed the connection
                print("\n[Disconnected from server.]")
                sys.exit(0)
            wrapped = textwrap.fill(line.rstrip(), width=90)
            print(wrapped, flush=True)


    except OSError:
        print("\n[Connection lost.]")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Pathfinder game client")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    print(f"Connecting to {args.host}:{args.port}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.host, args.port))
    except ConnectionRefusedError:
        print("Could not connect. Is the server running?")
        sys.exit(1)

    print("Connected.\n")

    # Start background thread to handle incoming text
    receiver = threading.Thread(target=receive_loop, args=(sock,), daemon=True)
    receiver.start()

    # Main thread handles your keyboard input
    try:
        while True:
            line = input()
            sock.sendall((line + "\n").encode("utf-8"))

    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
        sock.close()


if __name__ == "__main__":
    main()