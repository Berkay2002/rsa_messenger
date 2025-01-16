import socketio
import requests
from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QWidget, QPushButton, QListWidget, QVBoxLayout

from crypto_utils import encrypt_message, decrypt_message
from ChatWindow import ChatWindow
from ProfileDialog import ProfileDialog

class MainWindow(QWidget):
    def __init__(self, username, private_key, public_key):
        super().__init__()
        uic.loadUi('./ui/mainwindow.ui', self)

        self.username = username
        self.private_key = private_key
        self.public_key = public_key

        # Find UI elements
        self.profile_button = self.findChild(QPushButton, "profile_button")
        self.online_users_list = self.findChild(QListWidget, "online_users_list")
        self.create_group_button = self.findChild(QPushButton, "create_group_button")
        self.join_group_button = self.findChild(QPushButton, "join_group_button")
        self.group_list = self.findChild(QListWidget, "group_list")
        self.chat_container = self.findChild(QWidget, "chat_container")
        self.friends_list_widget = self.findChild(QListWidget, "friends_list_widget")

        # We'll embed a ChatWindow inside chat_container
        self.chat_window = ChatWindow(self.username, self.private_key, self.public_key)
        if not self.chat_container.layout():
            layout = QVBoxLayout(self.chat_container)
        self.chat_container.layout().addWidget(self.chat_window)

        # Dictionary to hold ChatWindow references for group chats and direct chats
        self.groupChats = {}
        self.directChats = {}

        # Connect signals
        if self.profile_button:
            self.profile_button.clicked.connect(self.open_profile)
        if self.create_group_button:
            self.create_group_button.clicked.connect(self.handle_create_group)
        if self.join_group_button:
            self.join_group_button.clicked.connect(self.handle_join_group)
        if self.group_list:
            self.group_list.itemClicked.connect(self.handle_group_clicked)
        if self.friends_list_widget:
            self.friends_list_widget.itemDoubleClicked.connect(self.handle_friend_double_clicked)

        # Use double-click for groups
        if self.group_list:
            self.group_list.itemDoubleClicked.connect(self.handle_group_double_clicked)

        # Use double-click for friends
        if self.friends_list_widget:
            self.friends_list_widget.itemDoubleClicked.connect(self.handle_friend_double_clicked)

        # Socket.IO
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            print("[MainWindow] Connected to Socket.IO")
            self.sio.emit('register', {'username': self.username})

        @self.sio.on('online_users_update')
        def on_online_users_update(data):
            online = data.get("online_users", [])
            self.update_online_users(online)

        @self.sio.on('receive_message')
        def on_receive_message(data):
            self.chat_window.receive_direct_message(data)

        @self.sio.on('receive_group_message')
        def on_receive_group_message(data):
            group_name = data.get("group_name")
            if group_name in self.groupChats:
                self.groupChats[group_name].receive_group_message(data)

        @self.sio.event
        def connect_error(err):
            print(f"[MainWindow] Socket.IO connection error: {err}")

        try:
            self.sio.connect("http://127.0.0.1:5000")
        except Exception as e:
            print(f"[MainWindow] Could not connect to server: {e}")

        # Load initial data
        self.load_online_users()
        self.load_groups()
        self.load_friends()

    def handle_group_double_clicked(self, item):
        group_name = item.text()
        if group_name not in self.groupChats:
            chat = ChatWindow(self.username, self.private_key, self.public_key, is_group=True, group_name=group_name)
            self.groupChats[group_name] = chat
        for i in reversed(range(self.chat_container.layout().count())):
            widget = self.chat_container.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.chat_container.layout().addWidget(self.groupChats[group_name])

    def handle_friend_double_clicked(self, item):
        friend_name = item.text()
        if friend_name not in self.directChats:
            chat = ChatWindow(self.username, self.private_key, self.public_key, direct_recipient=friend_name)
            self.directChats[friend_name] = chat
        for i in reversed(range(self.chat_container.layout().count())):
            widget = self.chat_container.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.chat_container.layout().addWidget(self.directChats[friend_name])

    def load_friends(self):
        """
        Load the user's friends list from the server.
        """
        try:
            r = requests.get("http://127.0.0.1:5000/get_profile", params={"username": self.username})
            if r.status_code == 200:
                data = r.json()
                friend_list = data.get("friends", [])
                self.update_friend_list(friend_list)
        except Exception as e:
            print(f"Could not load friends: {e}")

    def update_friend_list(self, friend_list):
        """
        Update the friends list widget with the given list of friends.
        """
        self.friends_list_widget.clear()
        for friend in friend_list:
            self.friends_list_widget.addItem(friend)
        
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

    def open_profile(self):
        dialog = ProfileDialog(self.username)
        if dialog.exec_() == dialog.Accepted:
            print("[MainWindow] Profile updated")

    def handle_create_group(self):
        group_name, ok = self.get_text_input("Create Group", "Group name:")
        if ok and group_name.strip():
            payload = {
                "group_name": group_name.strip(),
                "creator": self.username
            }
            try:
                r = requests.post("http://127.0.0.1:5000/create_group", json=payload)
                if r.status_code == 201:
                    self.load_groups()
                else:
                    err = r.json().get("error", "Unknown error")
                    print(f"[MainWindow] Could not create group: {err}")
            except Exception as e:
                print(f"[MainWindow] Network error create_group: {e}")

    def handle_join_group(self):
        group_name, ok = self.get_text_input("Join Group", "Group name to join:")
        if ok and group_name.strip():
            payload = {
                "group_name": group_name.strip(),
                "username": self.username
            }
            try:
                r = requests.post("http://127.0.0.1:5000/join_group", json=payload)
                if r.status_code == 200:
                    self.load_groups()
                else:
                    err = r.json().get("error", "Unknown error")
                    print(f"[MainWindow] Could not join group: {err}")
            except Exception as e:
                print(f"[MainWindow] Network error join_group: {e}")

    def load_online_users(self):
        try:
            r = requests.get("http://127.0.0.1:5000/online_users")
            if r.status_code == 200:
                data = r.json()
                online = data.get("online_users", [])
                self.update_online_users(online)
        except Exception as e:
            print(f"[MainWindow] Could not load online users: {e}")

    def update_online_users(self, online):
        self.online_users_list.clear()
        for user in online:
            self.online_users_list.addItem(user)

    def load_groups(self):
        """
        Load the list of groups from the server and update the group_list widget.
        """
        try:
            r = requests.get("http://127.0.0.1:5000/all_groups")
            if r.status_code == 200:
                group_data = r.json().get("groups", [])
                self.group_list.clear()
                for grp in group_data:
                    self.group_list.addItem(grp)
            else:
                print("[MainWindow] Could not fetch groups:", r.json())
        except Exception as e:
            print("[MainWindow] Network error in load_groups:", e)


    def get_text_input(self, title, label):
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, title, label)
        return text, ok
