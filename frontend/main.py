from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('ui/login.ui', self)  # Load login UI
        self.login_button.clicked.connect(self.handle_login)  # Connect button click

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        response = login(username, password)
        if response.get("status") == "success":
            self.chat_window = ChatWindow()
            self.chat_window.show()
            self.close()  # Close login window
        else:
            self.error_label.setText("Invalid credentials!")  # Display error

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('ui/chat.ui', self)  # Load chat UI

        # Initialize WebSocket client
        self.websocket_client = ChatClient("ws://127.0.0.1:8000")  # Replace with your server URL
        asyncio.run(self.websocket_client.connect())  # Connect to WebSocket server

        # Start WebSocket listening thread
        self.websocket_thread = WebSocketThread(self.websocket_client)
        self.websocket_thread.message_received.connect(self.update_chat)  # Connect signal to slot
        self.websocket_thread.start()

        # Connect send button to the send_message method
        self.send_button.clicked.connect(self.send_message)
    
    def send_message(self):
        """
        Send a message typed by the user to the WebSocket server.
        """
        message = self.message_input.text()
        asyncio.run(self.websocket_client.send_message(message))
        self.message_input.clear()

    def update_chat(self, message):
        """
        Update the chat box with a new message.
        """
        self.chat_box.append(message)

import requests
def login(username, password):
    url = "http://127.0.0.1:5000/login"  # Flask server endpoint
    response = requests.post(url, json={"username": username, "password": password})
    return response.json()  # Handle the response (success or error)

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256

def generate_keypair():
    """Generate an RSA keypair."""
    key = RSA.generate(2048)
    private_key = key.export_key().decode()
    public_key = key.publickey().export_key().decode()
    return private_key, public_key

def encrypt_message(message, recipient_public_key):
    """Encrypt a message using the recipient's public key with SHA-256."""
    public_key = RSA.import_key(recipient_public_key.encode())
    cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
    return cipher.encrypt(message.encode())

def decrypt_message(encrypted_message, recipient_private_key):
    """Decrypt a message using the recipient's private key with SHA-256."""
    private_key = RSA.import_key(recipient_private_key.encode())
    cipher = PKCS1_OAEP.new(private_key, hashAlgo=SHA256)
    return cipher.decrypt(encrypted_message).decode()

import asyncio
import websockets

class ChatClient:
    def __init__(self, uri):
        """
        Initialize the WebSocket client with the server's URI.
        """
        self.uri = uri
        self.connection = None
        self.private_key, self.public_key = generate_keypair()

    async def connect(self):
        """
        Establish a connection to the WebSocket server.
        """
        self.connection = await websockets.connect(self.uri)

    async def send_message(self, message):
        """
        Send a message to the WebSocket server.
        """
        if self.connection:
            cipher = PKCS1_OAEP.new(self.public_key)
            encrypted_message = cipher.encrypt(message.encode())
            await self.connection.send(encrypted_message)

    async def receive_message(self):
        """
        Receive a message from the WebSocket server.
        """
        if self.connection:
            encrypted_message = await self.connection.recv()
            cipher = PKCS1_OAEP.new(self.private_key)
            decrypted_message = cipher.decrypt(encrypted_message)
            return decrypted_message.decode()
        
from PyQt5.QtCore import QThread, pyqtSignal

class WebSocketThread(QThread):
    """
    A thread for listening to incoming WebSocket messages.
    """
    message_received = pyqtSignal(str)  # Signal to update the UI with a new message

    def __init__(self, websocket_client):
        super().__init__()
        self.websocket_client = websocket_client

    def run(self):
        """
        Start the WebSocket listening loop in a thread.
        """
        asyncio.run(self.listen_to_server())

    async def listen_to_server(self):
        """
        Continuously listen for messages from the server.
        """
        while True:
            message = await self.websocket_client.receive_message()
            self.message_received.emit(message)  # Emit the signal with the new message

