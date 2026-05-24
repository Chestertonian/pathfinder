"""
client.py — Game client
"""

import socket
import threading
import argparse
import sys
import textwrap

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 3000
PROMPT = "> "


def print_prompt():
    print(PROMPT, end="", flush=True)


def receive_loop(sock: socket.socket) -> None:
    try:
        file = sock.makefile("r", encoding="utf-8")
        while True:
            line = file.readline()
            if not line:
                print("\n[Disconnected from server.]")
                sys.exit(0)

            wrapped = textwrap.fill(line.rstrip(), width=90)
            if wrapped:
                # Clear current line, print received text, reprint prompt
                sys.stdout.write(f"\r{' ' * 60}\r")
                sys.stdout.write(wrapped + "\n")
                print_prompt()
                sys.stdout.flush()

    except OSError:
        print("\n[Connection lost.]")
        sys.exit(0)


def input_loop(sock: socket.socket) -> None:
    """
    Reads stdin one character at a time so we control
    exactly when the prompt appears.
    """
    buf = []
    print_prompt()

    while True:
        ch = sys.stdin.read(1)

        if not ch:          # EOF
            break

        if ch == "\n":
            line = "".join(buf).strip()
            buf.clear()

            try:
                sock.sendall((line + "\n").encode("utf-8"))
            except OSError:
                break

            # Always reprint prompt after sending, even on empty input
            print_prompt()

        else:
            buf.append(ch)


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

    receiver = threading.Thread(target=receive_loop, args=(sock,), daemon=True)
    receiver.start()

    try:
        input_loop(sock)
    except KeyboardInterrupt:
        pass

    print("\nGoodbye.")
    sock.close()


if __name__ == "__main__":
    main()