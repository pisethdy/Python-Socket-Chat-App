import threading
import socket

PORT = 5050
SERVER = "localhost"
ADDR = (SERVER, PORT)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

clients = {}
clients_lock = threading.Lock()

def broadcast(message, sender_conn=None):
    """Send a message to all connected clients except the sender."""
    with clients_lock:
        for client_conn in list(clients.keys()):  # Iterate over a list to avoid modifying the dict while iterating
            if client_conn != sender_conn:  # Avoid sending the message back to the sender
                try:
                    client_conn.sendall(message.encode(FORMAT))
                except (BrokenPipeError, ConnectionResetError) as send_error:  # Specific exceptions
                    print(f"[ERROR] Failed to send message to client: {send_error}")
                    clients.pop(client_conn, None)  # Remove client if connection fails

def handle_client(conn, addr):
    """Handles an individual client connection."""
    client_name = None  # Initialize client_name

    try:
        conn.send("Please enter your name!".encode(FORMAT))
        client_name = conn.recv(1024).decode(FORMAT).strip()

        with clients_lock:
            clients[conn] = client_name  # Store the client's name

        print(f"[NEW CONNECTION] {client_name} ({addr}) connected")

        # Use a flag to control connection status
        is_connected = True
        while is_connected:
            try:
                msg = conn.recv(1024).decode(FORMAT)
                if not msg:
                    break

                if msg == DISCONNECT_MESSAGE:
                    is_connected = False
                    break

                print(f"[{client_name}] {msg}")

                if msg.startswith("all "):
                    message = msg[len("all "):].strip()
                    broadcast(f"[{client_name}] {message}", sender_conn=conn)
                elif msg.startswith("@"):  # Check for direct message
                    parts = msg.split(" ", 1)  # Split into two parts
                    if len(parts) < 2:
                        conn.sendall(f"[SERVER] Please specify a target client and a message.".encode(FORMAT))
                        continue

                    target_client = parts[0][1:]  # Remove the '@' from target client name
                    message = parts[1]

                    found = False
                    with clients_lock:
                        for client_conn, client_id in clients.items():
                            if target_client == client_id:
                                client_conn.sendall(f"[{client_name} -> {client_id}] {message}".encode(FORMAT))
                                found = True
                                break

                    if not found:
                        conn.sendall(f"[SERVER] Client {target_client} not found.".encode(FORMAT))
                else:
                    conn.sendall(
                        f"[SERVER] Invalid message format. Use 'all <message>' or '@client <message>'.".encode(FORMAT))

            except (ConnectionResetError, BrokenPipeError) as recv_error:  # Different name for error variable
                print(f"[ERROR] Connection with {client_name} ({addr}) was reset: {recv_error}")
                break

    except (ConnectionResetError, BrokenPipeError) as handle_error:  # Different name for error variable
        print(f"[ERROR] Exception in handling client {addr}: {handle_error}")

    finally:
        with clients_lock:
            if client_name is not None:  # Check if client_name was successfully assigned
                clients.pop(conn, None)
                print(f"[DISCONNECT] {client_name} ({addr}) Disconnected")
            else:
                print(f"[DISCONNECT] A client disconnected without a name ({addr})")
        conn.close()

def server_console():
    """Allows the server to send broadcast messages to all connected clients."""
    while True:
        msg = input("[Server Message]: ")
        if msg.lower() == 'q':
            break
        broadcast(f"[SERVER] {msg}")

def start():
    """Start the server and listen for incoming connections."""
    print('[SERVER STARTED] Listening for connections...')
    server.listen()

    console_thread = threading.Thread(target=server_console, daemon=True)
    console_thread.start()

    while True:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

        except Exception as accept_error:  # Different name for error variable
            print(f"[ERROR] Exception in accepting connections: {accept_error}")

if __name__ == "__main__":
    try:
        start()
    except Exception as start_error:  # Different name for error variable
        print(f"[ERROR] Server encountered an error: {start_error}")
    finally:
        server.close()
