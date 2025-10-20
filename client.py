import socket
import threading
import argparse


def receive(sock):
    while True:
        data = sock.recv(1024)
        if data:
            print()
            print("------")
            print("Received:")
            print(data.decode())
            print("------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
    description='TCP Server',
    )
    parser.add_argument('--port',type = int, help='The port to host the client.')
    parser.add_argument('--address',type= str, help='The address to host the server.')

    args = parser.parse_args()

    ADDRESS = args.address if args.address else "0.0.0.0"
    PORT = args.port if args.port else 1234

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ADDRESS, PORT))

    threading.Thread(target=receive, args=(client,), daemon=True).start()


    while True:

        message = input("Send: ")

        if message == "exit":
            client.close()
            break

        client.sendall(message.encode())
        print(message)
