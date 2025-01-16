import requests
import socketio  # <-- The python-socketio client library
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QTextBrowser, QLineEdit, QPushButton
from PyQt5.QtCore import Qt

# RSA encryption/decryption helpers (adjust path if needed)
from crypto_utils import encrypt_message, decrypt_message

class ChatWindow(QWidget):
    """
    A QWidget-based chat window that handles:
    - RSA-encrypted messages
    - Offline store-and-forward (via REST)
    - Real-time delivery (via Socket.IO)
    """
    def __init__(self, username, private_key, public_key):
        super().__init__()
        # Load chat UI
        uic.loadUi('./ui/chat.ui', self)

        # Store user info
        self.username = username
        self.private_key = private_key
        self.public_key = public_key

        # Find UI widgets
        self.chatBox = self.findChild(QTextBrowser, "chatBox")
        self.recipient_input = self.findChild(QLineEdit, "recipient_input")
        self.message_input = self.findChild(QLineEdit, "message_input")
        self.send_button = self.findChild(QPushButton, "send_button")

        # Check that widgets loaded
        if not self.chatBox:
            print("[ChatWindow] Error: No QTextBrowser named 'chatBox' found.")
        if not self.recipient_input:
            print("[ChatWindow] Error: No QLineEdit named 'recipient_input'.")
        if not self.message_input:
            print("[ChatWindow] Error: No QLineEdit named 'message_input'.")
        if not self.send_button:
            print("[ChatWindow] Error: No QPushButton named 'send_button'.")
        else:
            self.send_button.clicked.connect(self.send_message)

        # 1) Create a Socket.IO client
        self.sio = socketio.Client()

        # 2) Define event handlers before connecting
        @self.sio.event
        def connect():
            print("Socket.IO: Connected to server.")
            # Register this user so the server knows we're online
            self.sio.emit('register', {'username': self.username})

        @self.sio.on('receive_message')
        def on_receive_message(data):
            """
            Called when the server emits 'receive_message'.
            data: { 'sender': ..., 'recipient': ..., 'message': <hex-encoded> }
            """
            sender = data.get('sender')
            enc_hex = data.get('message')
            if not sender or not enc_hex:
                return

            # Decrypt
            try:
                ciphertext = bytes.fromhex(enc_hex)
                plaintext = decrypt_message(ciphertext, self.private_key)
                self.update_chat(f"[{sender}]: {plaintext}")
            except Exception as e:
                self.update_chat(f"[{sender}] Decryption error: {e}")

        @self.sio.event
        def connect_error(err):
            print(f"[ChatWindow] Socket.IO connection failed: {err}")

        @self.sio.on('error')
        def on_error(msg):
            print(f"[ChatWindow] Socket.IO error event: {msg}")

        # 3) Connect to Socket.IO server
        #    (Adjust URL/port if your server is elsewhere)
        try:
            self.sio.connect("https://rsa-messenger-app-de61cf2676c2.herokuapp.com")
        except Exception as e:
            print(f"[ChatWindow] Could not connect to Socket.IO: {e}")

        # 4) Fetch and display any offline messages
        self.fetch_undelivered_messages()

    def send_message(self):
        """
        Send an RSA-encrypted message to the user typed in recipient_input.
        We'll do real-time if they're online; if offline, the server will store it.
        """
        if not self.recipient_input or not self.message_input:
            self.update_chat("Error: Missing recipient_input or message_input widget.")
            return

        recipient = self.recipient_input.text().strip()
        message = self.message_input.text().strip()
        if not recipient or not message:
            self.update_chat("Error: Recipient or message cannot be empty.")
            return

        # Get the recipient's public key from your Flask backend
        rec_pub = self.get_recipient_public_key(recipient)
        if not rec_pub:
            self.update_chat(f"Error: Could not fetch public key for {recipient}")
            return

        # Encrypt the message
        try:
            ciphertext_bytes = encrypt_message(message, rec_pub)
            enc_hex = ciphertext_bytes.hex()
        except Exception as e:
            self.update_chat(f"Encryption failed: {e}")
            return

        # We send via Socket.IO for real-time
        data = {
            "sender": self.username,
            "recipient": recipient,
            "message": enc_hex
        }
        if self.sio.connected:
            # Real-time emit
            self.sio.emit('send_message', data)
            # Show on our own chat box
            self.update_chat(f"[Me -> {recipient}]: {message}")
            self.message_input.clear()
        else:
            # If for some reason Socket.IO is not connected, fallback to REST
            # (Though ideally you'd fix the socket connection.)
            self.update_chat("[Warning] Socket.IO not connected, using /send_message fallback.")
            try:
                resp = requests.post("https://rsa-messenger-app-de61cf2676c2.herokuapp.com/login", json={...})
                if resp.status_code == 200:
                    self.update_chat(f"[Me -> {recipient}]: {message}")
                    self.message_input.clear()
                else:
                    err = resp.json().get("error", "Unknown error")
                    self.update_chat(f"Send failed: {err}")
            except Exception as e:
                self.update_chat(f"Network error (fallback REST): {e}")

    def fetch_undelivered_messages(self):
        """
        Retrieve any stored (offline) messages from the server
        and decrypt them. This runs once at window init.
        """
        try:
            resp = requests.get("https://rsa-messenger-app-de61cf2676c2.herokuapp.com/fetch_messages", params={
                "username": self.username
            })
            if resp.status_code == 200:
                messages = resp.json().get("messages", [])
                for msg in messages:
                    sender = msg.get("sender")
                    enc_hex = msg.get("encrypted_message")
                    if not enc_hex:
                        continue

                    try:
                        plaintext = decrypt_message(bytes.fromhex(enc_hex), self.private_key)
                        self.update_chat(f"[{sender}]: {plaintext}")
                    except Exception as e:
                        self.update_chat(f"[{sender}] Decryption error: {e}")
            else:
                err = resp.json().get("error", "Unknown error")
                self.update_chat(f"Failed to fetch messages: {err}")
        except requests.exceptions.RequestException as e:
            self.update_chat(f"Network error while fetching offline messages: {e}")

    def get_recipient_public_key(self, recipient):
        """
        Calls /get_public_key?username={recipient} to retrieve the user's public key.
        """
        url = f"https://rsa-messenger-app-de61cf2676c2.herokuapp.com/get_public_key?username={recipient}"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                return resp.json().get("public_key")
        except requests.exceptions.RequestException as e:
            print(f"[ChatWindow] get_recipient_public_key error: {e}")
        return None

    def update_chat(self, text):
        """
        Append a new line of text to the chatBox.
        """
        if self.chatBox:
            self.chatBox.append(text)
        else:
            print(text)
