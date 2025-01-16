import requests
import socketio
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QTextBrowser, QLineEdit, QPushButton
from PyQt5.QtCore import QDateTime, Qt

from crypto_utils import encrypt_message, decrypt_message

class ChatWindow(QWidget):
    """
    A QWidget-based chat window that handles:
      - Direct RSA-encrypted messages
      - Group messages (simplified encryption logic)
      - Offline store-and-forward
      - Real-time updates via Socket.IO
    """

    def __init__(self, username, private_key, public_key, is_group=False, group_name=None, direct_recipient=None):
        super().__init__()
        uic.loadUi('./ui/chat.ui', self)

        self.username = username
        self.private_key = private_key
        self.public_key = public_key
        self.is_group = is_group
        self.group_name = group_name
        self.direct_recipient = direct_recipient

        self.chatBox = self.findChild(QTextBrowser, "chatBox")
        self.recipient_input = self.findChild(QLineEdit, "recipient_input")
        self.message_input = self.findChild(QLineEdit, "message_input")
        self.send_button = self.findChild(QPushButton, "send_button")

        if not self.chatBox:
            print("[ChatWindow] Error: QTextBrowser 'chatBox' not found.")
        if not self.recipient_input:
            print("[ChatWindow] Error: QLineEdit 'recipient_input' not found.")
        if not self.message_input:
            print("[ChatWindow] Error: QLineEdit 'message_input' not found.")
        if not self.send_button:
            print("[ChatWindow] Error: QPushButton 'send_button' not found.")
        else:
            self.send_button.clicked.connect(self.handle_send)

        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            print("[ChatWindow] Socket.IO: Connected.")
            self.sio.emit('register', {'username': self.username})

        @self.sio.on('receive_message')
        def on_receive_message(data):
            self.receive_direct_message(data)

        @self.sio.on('receive_group_message')
        def on_receive_group_message(data):
            self.receive_group_message(data)

        @self.sio.event
        def connect_error(err):
            print(f"[ChatWindow] Socket.IO connection error: {err}")

        try:
            self.sio.connect("http://127.0.0.1:5000")
        except Exception as e:
            print("[ChatWindow] Could not connect Socket.IO:", e)

        self.fetch_undelivered_messages()

    # ----------------------
    #     Sending Logic
    # ----------------------
    def handle_send(self):
        """
        Decide if user wants to send a direct or group message 
        based on the recipient input (e.g. `#GroupName` for group).
        """
        msg_text = self.message_input.text().strip()
        if not msg_text:
            self.update_chat("[Error] Message is empty.")
            return

        if self.is_group and self.group_name:
            self.send_group_message(self.group_name, msg_text)
        elif self.direct_recipient:
            self.send_direct_message(self.direct_recipient, msg_text)
        else:
            recipient = self.recipient_input.text().strip()
            if not recipient:
                self.update_chat("[Error] Recipient is empty.")
                return
            self.send_direct_message(recipient, msg_text)
            
    def handle_group_clicked(self, item):
        group_name = item.text()
        if group_name not in self.groupChats:
            chat = ChatWindow(self.username, self.private_key, self.public_key, is_group=True, group_name=group_name)
            self.groupChats[group_name] = chat
        for i in reversed(range(self.chat_container.layout().count())):
            widget = self.chat_container.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.chat_container.layout().addWidget(self.groupChats[group_name])


    def send_direct_message(self, recipient, plaintext):
        """
        Encrypt with the recipient's public key, emit via Socket.IO or fallback to REST.
        """
        rec_pub = self.get_recipient_public_key(recipient)
        if not rec_pub:
            self.update_chat(f"[Error] Could not fetch public key for {recipient}")
            return
        try:
            ciphertext_hex = encrypt_message(plaintext, rec_pub).hex()
        except Exception as e:
            self.update_chat(f"[Encryption error] {e}")
            return

        # Now fetch the sender's own profile if you want to display your avatar or display name:
        my_profile = self.fetch_profile(self.username)
        my_avatar = my_profile.get("avatar_url", "default_avatar.png")
        # ... then do add_chat_message or something that uses the avatar.

        data = {
            "sender": self.username,
            "recipient": recipient,
            "message": ciphertext_hex
        }
        
        if self.sio.connected:
            self.sio.emit('send_message', data)
            # Fetch the sender's profile to get the avatar URL
            my_profile = self.fetch_profile(self.username)
            my_avatar = my_profile.get("avatar_url", "default.png")
            self.add_chat_message("Me", my_avatar, plaintext)
            self.message_input.clear()
        else:
            # fallback to POST /send_message
            try:
                r = requests.post("http://127.0.0.1:5000/send_message", json=data)
                if r.status_code == 200:
                    my_profile = self.fetch_profile(self.username)
                    my_avatar = my_profile.get("avatar_url", "default.png")
                    self.add_chat_message("Me", my_avatar, plaintext)
                    self.message_input.clear()
                else:
                    err = r.json().get("error", "Unknown error")
                    self.update_chat(f"[Send failed] {err}")
            except Exception as e:
                self.update_chat(f"[Network error] {e}")
                
    def fetch_profile(self, username):
        """
        Calls /get_profile?username=... on the server and returns the user's doc.
        """
        import requests
        url = f"http://127.0.0.1:5000/get_profile?username={username}"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                return resp.json()  # { "username":..., "display_name":..., "avatar_url":... }
        except Exception as e:
            print(f"[ChatWindow] Could not fetch profile for {username}: {e}")
        return {}


    def send_group_message(self, group_name, plaintext):
        """
        For simplicity, 'encrypt' by just hexing the plaintext. 
        Real group E2E is more complex. This is a minimal placeholder.
        """
        msg_hex = plaintext.encode().hex()
        data = {
            "group_name": group_name,
            "sender": self.username,
            "message": msg_hex
        }

        if self.sio.connected:
            self.sio.emit('send_group_message', data)
            self.update_chat(self.format_message(f"Me (#{group_name})", plaintext))
            self.message_input.clear()
        else:
            # fallback /send_group_message
            try:
                r = requests.post("http://127.0.0.1:5000/send_group_message", json=data)
                if r.status_code == 200:
                    self.update_chat(self.format_message(f"Me (#{group_name})", plaintext))
                    self.message_input.clear()
                else:
                    err = r.json().get("error", "Unknown error")
                    self.update_chat(f"[Group send failed] {err}")
            except Exception as e:
                self.update_chat(f"[Network error] {e}")
                
    def add_chat_message(self, sender_username, sender_avatar_url, message_text):
        """
        Insert HTML into the QTextBrowser with an inline image and text.
        """
        timestamp = QDateTime.currentDateTime().toString("HH:mm")

        # On Windows, replace backslashes to forward slashes & prepend file:///
        avatar_path_fixed = sender_avatar_url.replace('\\', '/')
        if not avatar_path_fixed.startswith("file:///"):
            avatar_path_fixed = "file:///" + avatar_path_fixed

        avatar_html = f'<img src="{avatar_path_fixed}" width="40" height="40" style="vertical-align: middle; border-radius: 20px; margin-right: 8px;" />'

        message_html = f"""
        <div style="margin: 8px 0;">
            <div>
                {avatar_html}
                <b>{sender_username}</b>
                <span style="color: #888; margin-left: 10px;">{timestamp}</span>
            </div>
            <div style="margin-left: 48px; margin-top: 4px;">
                {message_text}
            </div>
        </div>
        """
        self.chatBox.insertHtml(message_html)
        self.chatBox.insertHtml("<br/>")
        self.chatBox.verticalScrollBar().setValue(self.chatBox.verticalScrollBar().maximum())


    # ----------------------
    #    Receiving Logic
    # ----------------------
    def receive_direct_message(self, data):
        """
        data: { sender, recipient, message(hex) }
        Decrypt with our private key.
        """
        sender = data.get("sender")
        enc_hex = data.get("message")
        try:
            plaintext = decrypt_message(bytes.fromhex(enc_hex), self.private_key)
        except Exception as e:
            self.update_chat(f"[Decryption error] {e}")
            return
        # Fetch the sender's profile to get the avatar URL
        sender_profile = self.fetch_profile(sender)
        avatar_url = sender_profile.get("avatar_url", "default_avatar.png")
        
        self.add_chat_message(sender, avatar_url, plaintext)


    def receive_group_message(self, data):
        """
        data: { group_name, sender, message(hex) }
        For simplicity, decode the hex back to plaintext. 
        """
        group_name = data.get("group_name")
        sender = data.get("sender")
        msg_hex = data.get("message")
        if not msg_hex:
            return
        try:
            msg_bytes = bytes.fromhex(msg_hex)
            plaintext = msg_bytes.decode()
            self.update_chat(self.format_message(f"{sender} (#{group_name})", plaintext))
        except Exception as e:
            self.update_chat(f"[{sender} -> #{group_name}] Decryption error: {e}")

    # ----------------------
    #     Offline Logic
    # ----------------------
    def fetch_undelivered_messages(self):
        """
        Retrieve stored offline messages for our user from /fetch_messages
        and decrypt them.
        """
        try:
            r = requests.get("http://127.0.0.1:5000/fetch_messages", params={
                "username": self.username
            })
            if r.status_code == 200:
                msgs = r.json().get("messages", [])
                for msg in msgs:
                    sender = msg.get("sender")
                    enc_hex = msg.get("encrypted_message")
                    if not enc_hex:
                        continue
                    try:
                        decrypted = decrypt_message(bytes.fromhex(enc_hex), self.private_key)
                        self.update_chat(self.format_message(sender, decrypted))
                    except Exception as e:
                        self.update_chat(f"[{sender}] Decrypt error: {e}")
            else:
                err = r.json().get("error", "Unknown error")
                self.update_chat(f"[Fetch failed] {err}")
        except requests.exceptions.RequestException as e:
            self.update_chat(f"[Network error while fetching messages] {e}")

    # ----------------------
    #    Helper Methods
    # ----------------------
    def get_recipient_public_key(self, recipient):
        """
        GET /get_public_key?username=recipient
        """
        url = f"http://127.0.0.1:5000/get_public_key?username={recipient}"
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                return resp.json().get("public_key")
        except Exception as e:
            print(f"[ChatWindow] get_recipient_public_key error: {e}")
        return None

    def update_chat(self, line):
        """
        Append text to chatBox or fallback to console
        """
        if self.chatBox:
            self.chatBox.append(line)
        else:
            print(line)

    def format_message(self, sender, text):
        """
        Show timestamps & simple bubble style
        """
        timestamp = QDateTime.currentDateTime().toString("HH:mm")
        return f"[{timestamp}] {sender}: {text}"
