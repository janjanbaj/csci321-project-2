#  Server-side code:
import socket
import atexit
import threading
import argparse
import time
import pickle
import struct


def send_message(sock, message):

    time, message = message
    encoded_message = f"Time: {time}" + message.encode('utf-8')
    message_length = len(encoded_message)

    # Pack the length into a 4-byte network byte order integer
    length_prefix = struct.pack('!I', message_length) 
    sock.sendall(length_prefix + encoded_message)



class Session:
    
    def __init__(self, user_id: str):
        self.messages = []
        self.user_id = user_id
        self.active = True

    def newMessage(self, msg: str):
        self.messages.append([time.time(), msg])
        return

    def disconnect(self):
        self.active = False

class SessionDB:

    def __init__(self):
        self.users = {}
        self.lock = threading.Lock()

    def newSession(self, user_id)-> Session:
        self.lock.acquire()
        self.users[user_id] = Session(user_id)
        self.lock.release()
        return self.users[user_id]

    def getSession(self, user_id)->Session | None:
        self.lock.acquire()
        if user_id in self.users.keys():
            session = self.users[user_id]
            self.lock.release()
            return session 
        self.lock.release()
        return None

server_db = SessionDB()

def client(sock: socket.socket, address):

    # check if there was an older session for this ip.
    ip = address[0]
    ip_hash = hash(ip)
    current_session = server_db.getSession(ip_hash)

    # make a new session if no previous session.
    if current_session is None:
        current_session = server_db.newSession(ip_hash)
        print(f"{address} has connected.")
    else:
        print(f"{address} has re-connected.")
    
    while True:
        try:
            data = sock.recv(1024)
            print(f"Received {address}: {data}")

            if not data:
                break

            msg = data.decode("utf-8") 

            if msg == "his":
                for message in current_session.messages:
                    send_message(sock, message)
            else:
                current_session.newMessage(msg)

        except Exception as e:
            print(f"Error with {address}: {e}")
            break

    sock.close()
    current_session.disconnect()
    print(f"{address} has disconnected.")
    print(current_session)



def exit_handler(sock):
    print()
    print(f"SAFELY CLOSING SOCKET: {sock}")
    print()
    sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description='TCP Server',
        )
    parser.add_argument('--port',type = int, help='The port to host the client.')
    parser.add_argument('--address',type= str, help='The address to host the server.')

    args = parser.parse_args()

    SERVER_PORT = int(args.port) if args.port is not None else 1234
    SERVER_HOST = args.address if args.address is not None else socket.gethostname()


    print(f"Hosting the server at {SERVER_HOST}:{SERVER_PORT}")

    # Host Server:
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind((SERVER_HOST , SERVER_PORT))
    atexit.register(lambda: exit_handler(serversocket))
    serversocket.listen(5)

    while True:
        (sock, address) = serversocket.accept()
        threading.Thread(target=client, args=(sock, address)).start()


