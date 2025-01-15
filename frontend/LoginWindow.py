import requests
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QLineEdit, QLabel, QPushButton
from PyQt5.QtCore import Qt

# We'll import some helper crypto functions from a hypothetical `crypto_utils.py`
# You can keep your existing RSA logic or adapt this as needed.
from crypto_utils import (
    generate_keypair,
    encrypt_private_key,
    decrypt_private_key
)

# Import your ChatWindow class
from ChatWindow import ChatWindow

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('./ui/login.ui', self)  # Adjust path if needed

        # Find UI elements
        self.username_input = self.findChild(QLineEdit, "username_input")
        self.password_input = self.findChild(QLineEdit, "password_input")
        self.error_label = self.findChild(QLabel, "error_label")
        self.login_button = self.findChild(QPushButton, "login_button")

        if self.login_button:
            self.login_button.clicked.connect(self.handle_login)
        
        # Clear error label
        if self.error_label:
            self.error_label.setText("")

        # Optionally set window title
        self.setWindowTitle("Login")

    def handle_login(self):
        # 1. Validate input
        if not self.username_input or not self.password_input:
            return  # Could show an error

        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.set_error("Username and password cannot be empty.")
            return

        # 2. Attempt /login
        try:
            resp = requests.post("http://127.0.0.1:5000/login", json={
                "username": username,
                "password": password
            })
        except requests.exceptions.RequestException as e:
            self.set_error(f"Could not connect to server: {e}")
            return

        if resp.status_code == 200:
            # Login success
            data = resp.json()
            # We get back "public_key" and possibly "encrypted_private_key"
            pub_key = data.get("public_key", None)
            enc_priv_key = data.get("encrypted_private_key", None)

            if pub_key is None:
                self.set_error("Error: No public key returned from server.")
                return
            
            # If the server stores the user's private key in encrypted form:
            if enc_priv_key:
                try:
                    # Decrypt it with the user's password
                    private_key = decrypt_private_key(enc_priv_key, password)
                except Exception as e:
                    self.set_error(f"Error decrypting private key: {e}")
                    return
            else:
                # If not stored on server, user must have it locally or generate anew
                # For demo, we can say we don't have it:
                private_key = None
                # Or show an error that user didn't save their private key
                # In real app, you'd handle this logic carefully
                self.set_error("No private key found on server. Provide a local private key or re-register.")
                return

            # Open chat window
            self.open_chat(username, private_key, pub_key)

        elif resp.status_code == 404:
            # User does not exist => auto-register
            self.register_user(username, password)
        else:
            err_json = resp.json()
            err_msg = err_json.get("error", "Unknown error")
            self.set_error(f"Login error: {err_msg}")

    def register_user(self, username, password):
        """
        Called if the user doesn't exist. We generate RSA keys, encrypt the private key,
        and send them to /register.
        """
        # 1. Generate RSA key pair
        private_key, public_key = generate_keypair()

        # 2. (Optional) Encrypt the private key so the server can store it
        #    This is only if you want the server to "back up" the private key.
        encrypted_priv = encrypt_private_key(private_key, password)

        # 3. POST /register
        try:
            reg_resp = requests.post("http://127.0.0.1:5000/register", json={
                "username": username,
                "password": password,
                "public_key": public_key,
                "encrypted_private_key": encrypted_priv
            })
        except requests.exceptions.RequestException as e:
            self.set_error(f"Registration failed: {e}")
            return

        if reg_resp.status_code == 201:
            # Registration success
            self.open_chat(username, private_key, public_key)
        else:
            err_data = reg_resp.json()
            self.set_error(f"Register error: {err_data.get('error', 'Unknown error')}")

    def open_chat(self, username, private_key, public_key):
        """
        Switch to the ChatWindow, passing the keys along.
        """
        self.chat_window = ChatWindow(username, private_key, public_key)
        self.chat_window.show()
        self.close()

    def set_error(self, msg):
        if self.error_label:
            self.error_label.setText(msg)
        else:
            print(f"[LoginWindow] Error: {msg}")
