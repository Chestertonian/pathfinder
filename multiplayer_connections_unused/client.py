import socket
import threading

HOST = input("Server IP: ")
PORT = 5000


def listen(sock):
    while True:
        data = sock.recv(4096)
        if not data:
            break
        print(data.decode(), end="")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    threading.Thread(target=listen, args=(sock,), daemon=True).start()

    while True:
        msg = input("> ")
        sock.sendall((msg + "\n").encode())


if __name__ == "__main__":
    main()