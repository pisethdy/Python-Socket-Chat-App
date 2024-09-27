import socket
import threading
import time

PORT = 5050
SERVER = "localhost"
ADDR = (SERVER, PORT)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"

def receive_messages(client):
    """
    Listen to messages from the server in a separate thread.
    """
    while True:
        try:
            msg = client.recv(1024).decode(FORMAT)
            if not msg:
                break
            print(msg)  # Display message from the server
        except Exception as e:
            print(f"[ERROR] Failed to receive message: {e}")
            break

def connect():
    """
    Create a new client socket and connect to the server.
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(ADDR)
        return client
    except Exception as e:
        print(f"[ERROR] Could not connect to server: {e}")
        return None

def send(client, msg):
    """
    Send a message to the server.
    - To broadcast a message to all clients: all message
    - To send a message to a specific client: client_name message
    """
    try:
        client.send(msg.encode(FORMAT))
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}")

def start():
    """
    Main client function to handle connection and messaging.
    """
    answer = input('Would you like to connect (y/n)? ')
    if answer.lower() != 'y':
        return

    connection = connect()
    if not connection:
        return

    # Receive name prompt from the server
    name_prompt = connection.recv(1024).decode(FORMAT)
    print(name_prompt)
    client_name = input("Your Name: ")
    send(connection, client_name)

    # Start receiving messages in a separate thread
    threading.Thread(target=receive_messages, args=(connection,), daemon=True).start()

    print("Instructions:")
    print("- To broadcast to all clients: all message")
    print("- To send to a specific client: @client_name message")
    print("- Type 'q' to disconnect")

    while True:
        msg = input("Message: ")

        if msg.lower() == 'q':
            break

        # Check if the message starts with 'all ' for broadcasting
        if msg.startswith("all "):
            send(connection, msg)  # Send broadcast message
        # Check if the message starts with '@' for direct messages
        elif msg.startswith("@"):
            send(connection, msg)  # Send direct message
        else:
            print("[ERROR] Invalid message format. Use 'all <message>' or '@client <message>'.")

    time.sleep(1)
    print('Disconnected')

if __name__ == "__main__":
    start()
