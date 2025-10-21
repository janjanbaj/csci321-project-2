import socket
import atexit
import threading
import argparse
import time
import struct
import datetime
from typing import Optional, List, Tuple

def send_message(sock: socket.socket, message: str):
    # Sends a message over the socket, prefixed with its length.

    encoded_message = message.encode('utf-8')
    message_length = len(encoded_message)

    # Pack the length into a 4-byte network byte order integer ('!I')
    length_prefix = struct.pack('!I', message_length)
    sock.sendall(length_prefix + encoded_message)

class Session:

    def __init__(self, user_id: str, sock: socket.socket):
        # [timestamp (float), message_content (str)]
        self.messages: List[Tuple[float, str]] = []
        self.user_id = user_id
        self.active = True
        self.sock = sock 

    def newMessage(self, msg: str):
        self.messages.append((time.time(), msg))

    def disconnect(self):
        self.active = False
        self.sock = None

    def connect(self,sock: socket.socket):
        self.active = True
        self.sock = sock

    def sendMessage(self, msg: str):
        send_message(self.sock, msg)



class SessionDB:

    def __init__(self):
        self.users: dict[str, Session] = {}
        self.lock = threading.Lock()

    def newSession(self, user_id: str, sock) -> Session:
        with self.lock:
            new_session = Session(user_id, sock)
            self.users[user_id] = new_session
            return new_session

    def getSession(self, user_id: str) -> Optional[Session]:
        with self.lock:
            return self.users.get(user_id)

    def getActiveSessions(self)-> [Session]:
        return [i for i in self.users.values() if i.active]

server_db = SessionDB()




def client_handler(sock: socket.socket, address: Tuple[str, int]):
    """Handles incoming connection for a single client in a separate thread."""

    ip_address = address[0]
    user_id = ip_address

    current_session = server_db.getSession(user_id)

    if current_session is None:
        current_session = server_db.newSession(user_id, sock)
        print(f"Client {address} connected. New session created.")
        msg = f"[{datetime.datetime.fromtimestamp(time.time())}]: {ip_address} has connected."
    else:
        current_session.connect(sock)
        print(f"Client {address} re-connected. Resuming session.")
        msg = f"[{datetime.datetime.fromtimestamp(time.time())}]: {ip_address} has reconnected."

    other_active_sessions = server_db.getActiveSessions() 
    for other in other_active_sessions:
        if other is not current_session:
            other.sendMessage(msg)

    try:
        while current_session.active:

            data = sock.recv(1024)
            
            if not data:
                break

            print(f"Received from {address}: {data}")

            try:
                msg = data.decode("utf-8").strip()
            except UnicodeDecodeError:
                print(f"Warning: Could not decode message from {ip_address}")
                continue

            if not msg:
                continue

            if msg == "his":
                print(f"Sending history to {ip_address}.")
                for message in current_session.messages:
                    msg = f"[{datetime.datetime.fromtimestamp(message[0])}][{ip_address}]: {message[1]}"
                    send_message(sock, msg)
            else:
                current_session.newMessage(msg)
                time_stamped_message = current_session.messages[-1]
                msg = f"[{datetime.datetime.fromtimestamp(time_stamped_message[0])}][{ip_address}]: {msg}"
                other_active_sessions = server_db.getActiveSessions() 
                for other in other_active_sessions:
                    if other is not current_session:
                        other.sendMessage(msg)
                

    except Exception as e:
        print(f"Error with {address}: {e}")
    finally:
        sock.close()
        current_session.disconnect()
        print(f"Client {address} has disconnected.")
        other_active_sessions = server_db.getActiveSessions() 
        msg = f"[{datetime.datetime.fromtimestamp(time.time())}]: Disconnected {ip_address}"
        for other in other_active_sessions:
            other.sendMessage(msg)
        



def exit_handler(sock: socket.socket):
    """Safely closes the main server socket upon program exit."""
    print("\nShutting down server...")
    print(f"SAFELY CLOSING SOCKET: {sock.getsockname()}")
    sock.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='A simple TCP Server with session history.',
    )
    parser.add_argument('--port', type=int, default=1234,
                        help='The port to host the server on (default: 1234).')
    parser.add_argument('--address', type=str, default=socket.gethostname(),
                        help='The address/hostname to host the server on (default: hostname).')

    args = parser.parse_args()

    SERVER_PORT = args.port
    SERVER_HOST = args.address

    print(f"Hosting the server at {SERVER_HOST}:{SERVER_PORT}")

    # Host Server:
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        serversocket.bind((SERVER_HOST, SERVER_PORT))
    except Exception as e:
        print(f"Error binding to {SERVER_HOST}:{SERVER_PORT}: {e}")
        exit(1)

    atexit.register(lambda: exit_handler(serversocket))
    serversocket.listen(5) # Set maximum queued connections

    print("Server listening for connections...")
    
    while True:
        try:
            (sock, address) = serversocket.accept()
            # Start a new thread to handle the client
            threading.Thread(target=client_handler, args=(sock, address)).start()
        except KeyboardInterrupt:
            # Cleanly exit the infinite loop on Ctrl+C
            break
        except Exception as e:
            print(f"Server error during accept: {e}")
            time.sleep(1) # Avoid busy loop on error
