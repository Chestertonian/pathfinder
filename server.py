import socket
import threading
from db import get_connection
from game_loop import run_command_for_network  # we’ll define this wrapper

HOST = "0.0.0.0"
PORT = 5000

clients = {}  # conn -> character_id


def handle_client(conn, addr):
    print(f"Client connected: {addr}")

    try:
        conn.sendall(b"Enter character_id: ")
        character_id = int(conn.recv(1024).decode().strip())
        clients[conn] = character_id

        conn.sendall(b"Welcome to the world.\n")

        while True:
            data = conn.recv(4096)
            if not data:
                break

            command = data.decode().strip()

            output = run_command_for_network(character_id, command)

            if output:
                conn.sendall((output + "\n").encode())

    except Exception as e:
        print("Client error:", e)

    finally:
        conn.close()
        clients.pop(conn, None)
        print(f"Client disconnected: {addr}")


def broadcast(message):
    dead = []

    for conn in clients:
        try:
            conn.sendall((message + "\n").encode())
        except:
            dead.append(conn)

    for d in dead:
        clients.pop(d, None)


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f"Server running on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    start_server()