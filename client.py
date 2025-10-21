import socket
import threading
import argparse
import struct
from typing import Tuple

# The size of the length prefix (4 bytes for an 'I' - unsigned int)
HEADER_SIZE = 4 


def receive_all(sock: socket.socket, n: int) -> bytes:
    # Make sure that n-bytes are fully received. 
    data = b''
    while len(data) < n:
        # Calculate how many more bytes we need
        bytes_to_read = n - len(data)
        packet = sock.recv(bytes_to_read)
        if not packet:
            # Connection closed prematurely
            return b''
        data += packet
    return data

def receive_messages(sock: socket.socket):

    while True:
        try:

            length_prefix = receive_all(sock, HEADER_SIZE)
            if not length_prefix:
                print("\n[INFO] Server connection closed.")
                break

            message_length = struct.unpack('!I', length_prefix)[0]

            encoded_message = receive_all(sock, message_length)
            if not encoded_message:
                print("\n[INFO] Failed to receive message content.")
                break

            message = encoded_message.decode('utf-8')
            print()
            print("--- Received ---")
            print(message)
            print("----------------")
            
        except ConnectionResetError:
            print("\n[INFO] Server forcibly closed the connection.")
            break
        except Exception as e:
            # Handle other socket errors
            print(f"\n[ERROR] An error occurred while receiving: {e}")
            break
            
    sock.close()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='TCP Client for session-based chat server.',
    )
    parser.add_argument('--port', type=int, help='The port of the server.')
    parser.add_argument('--address', type=str, help='The address/hostname of the server.')

    args = parser.parse_args()

    ADDRESS = args.address if args.address else socket.gethostname()
    PORT = args.port if args.port else 1234
    
    print(f"Attempting to connect to {ADDRESS}:{PORT}...")

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ADDRESS, PORT))
        print("[SUCCESS] Connected to server.")

        # Start the thread to handle incoming messages
        threading.Thread(target=receive_messages, args=(client,), daemon=True).start()

        print("Type 'his' to request history, or 'exit' to disconnect.")
        print("-" * 30)

        # Main loop for sending messages
        while True:
            print("Send: ", end="", flush=True) 
            message = input()

            if message.lower() == "exit":
                print("[INFO] Disconnecting...")
                client.close()
                exit()

            if message:
                client.sendall(message.encode('utf-8'))
                
    except Exception as e:
        print(f"[ERROR] Connection refused. {e}")
