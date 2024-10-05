import threading
import socket
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Setup logging with a cleaner format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",  
    datefmt="%Y-%m-%d %H:%M:%S"
)

PORT = 5050
SERVER = "localhost"
ADDR = (SERVER, PORT)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"

smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_email = "your_email@gmail.com"  # Change to your email
smtp_password = "your_password"  # Change to your email password

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

clients = {}
clients_info = {}  # Store additional info like name and email
clients_lock = threading.Lock()

def send_email_notification(sender_name, sender_email, recipient_name, recipient_email, message):
    """
    Send an email notification to the recipient when they receive a message.
    """
    subject = f"New Message from {sender_name}"
    body = f"""
    Hello {recipient_name},

    You have received a new message from {sender_name} ({sender_email}):

    "{message}"

    Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    Regards,
    Chat Server
    """

    msg = MIMEMultipart()
    msg['From'] = smtp_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        smtp_server_conn = smtplib.SMTP(smtp_server, smtp_port)
        smtp_server_conn.starttls()
        smtp_server_conn.login(smtp_email, smtp_password)
        smtp_server_conn.sendmail(smtp_email, recipient_email, msg.as_string())
        smtp_server_conn.quit()
        logging.info(f"Email notification sent to {recipient_email}.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


def broadcast(message, sender_conn=None):
    """
    Send a message to all connected clients except the sender (if applicable).
    """
    with clients_lock:
        for client_conn, client_id in clients.items():
            if client_conn != sender_conn:  # Don't send to the sender
                try:
                    client_conn.sendall(message)
                except Exception as e:
                    logging.error(f"Failed to send message to {client_id}: {e}")
                    clients.pop(client_conn)


def handle_client(conn, addr):
    conn.send("Enter your name: ".encode(FORMAT))
    name = conn.recv(1024).decode(FORMAT).strip()

    conn.send("Enter your email: ".encode(FORMAT))
    email = conn.recv(1024).decode(FORMAT).strip()

    with clients_lock:
        clients[conn] = name  # Use the client's name as the client ID
        clients_info[conn] = {"name": name, "email": email}

    logging.info(f"New connection: {name} ({addr}) with email {email}")

    conn.send(f"Welcome, {name}! Your client ID is your name.".encode(FORMAT))

    try:
        connected = True
        while connected:
            try:
                msg = conn.recv(1024).decode(FORMAT)
                if not msg:
                    break

                if msg == DISCONNECT_MESSAGE:
                    connected = False

                logging.info(f"Message from {name}: {msg}")

                if msg.startswith("@"):
                    if ":" in msg:
                        target_client, message = msg[1:].split(":", 1)

                        if target_client.strip().lower() == "all":
                            logging.info(f"Broadcasting message from {name}: {message}")
                            broadcast(f"[{name}] {message}".encode(FORMAT), sender_conn=conn)
                        else:
                            found = False
                            with clients_lock:
                                for client_conn, client_data in clients_info.items():
                                    if client_data['name'].lower() == target_client.strip().lower():
                                        recipient_name = client_data['name']
                                        recipient_email = client_data['email']
                                        sender_name = clients_info[conn]['name']
                                        sender_email = clients_info[conn]['email']

                                        logging.info(f"Sending to {recipient_name} ({recipient_email}): {message}")
                                        client_conn.sendall(
                                            f"[{sender_name} -> {recipient_name}] {message}".encode(FORMAT))

                                        send_email_notification(sender_name, sender_email, recipient_name,
                                                                recipient_email, message)
                                        conn.sendall(f"[SERVER] Email sent to {recipient_name}.".encode(FORMAT))
                                        found = True
                                        break
                            if not found:
                                conn.sendall(f"[SERVER] Client {target_client} not found.".encode(FORMAT))
                    else:
                        conn.sendall(
                            f"[SERVER] Invalid format. Use '@name: message' or '@all: message'.".encode(FORMAT))
                else:
                    conn.sendall(
                        f"[SERVER] Invalid message format. Use '@name: message' or '@all: message'.".encode(
                            FORMAT))

            except ConnectionResetError:
                logging.error(f"Connection with {name} ({addr}) was reset.")
                break

    except Exception as e:
        logging.error(f"Exception in handling client {addr}: {e}")
    finally:
        with clients_lock:
            clients.pop(conn, None)
            clients_info.pop(conn, None)
        conn.close()
        logging.info(f"{addr} ({name}) Disconnected")


def server_console():
    """
    Allows server to send messages to all clients.
    Type your message in the server terminal to broadcast it to all clients.
    """
    while True:
        msg = input()
        if msg == 'q':
            break
        broadcast(f"[SERVER] {msg}".encode(FORMAT))


def start():
    logging.info("Server started. Listening for connections...")
    server.listen()

    console_thread = threading.Thread(target=server_console, daemon=True)
    console_thread.start()

    while True:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
        except Exception as e:
            logging.error(f"Exception in accepting connections: {e}")


if __name__ == "__main__":
    try:
        start()
    except Exception as e:
        logging.error(f"Server encountered an error: {e}")
    finally:
        server.close()
