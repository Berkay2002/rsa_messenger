from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit
from PyQt5.QtGui import QPixmap

class ProfileDialog(QDialog):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle("Profile")

        layout = QVBoxLayout()

        self.displayNameEdit = QLineEdit()
        self.displayNameEdit.setPlaceholderText("Display Name")

        # Label to preview the avatar image
        self.avatarLabel = QLabel("No avatar selected.")
        self.avatarLabel.setScaledContents(True)

        # Button to choose a local file
        self.chooseImageButton = QPushButton("Choose Avatar Image")

        self.saveButton = QPushButton("Save")

        layout.addWidget(QLabel("Update your display name:"))
        layout.addWidget(self.displayNameEdit)
        layout.addWidget(QLabel("Avatar Image:"))
        layout.addWidget(self.avatarLabel)
        layout.addWidget(self.chooseImageButton)
        layout.addWidget(self.saveButton)

        self.setLayout(layout)

        self.chooseImageButton.clicked.connect(self.handle_choose_image)
        self.saveButton.clicked.connect(self.save_profile)

        self.load_profile()

    def load_profile(self):
        import requests
        try:
            r = requests.get("http://127.0.0.1:5000/get_profile", params={"username": self.username})
            if r.status_code == 200:
                data = r.json()
                if data.get("display_name"):
                    self.displayNameEdit.setText(data["display_name"])
                if data.get("avatar_url"):
                    avatar_path = data["avatar_url"]
                    pixmap = QPixmap(avatar_path)
                    if not pixmap.isNull():
                        self.avatarLabel.setPixmap(pixmap.scaled(100, 100))
                    else:
                        self.avatarLabel.setText("Avatar file not found.")
        except Exception as e:
            print("[ProfileDialog] Could not fetch existing profile:", e)

    def handle_choose_image(self):
        dialog = QFileDialog()
        dialog.setNameFilters(["Images (*.png *.jpg *.jpeg *.bmp)"])
        if dialog.exec_():
            selected = dialog.selectedFiles()
            if selected:
                self.selectedAvatarPath = selected[0]
                pixmap = QPixmap(self.selectedAvatarPath)
                if not pixmap.isNull():
                    self.avatarLabel.setPixmap(pixmap.scaled(100, 100))
                else:
                    self.avatarLabel.setText("Failed to load image.")
            else:
                self.avatarLabel.setText("No avatar selected.")

    def save_profile(self):
        display_name = self.displayNameEdit.text().strip()
        avatar_path = getattr(self, 'selectedAvatarPath', None)

        payload = {
            "username": self.username,
            "display_name": display_name
        }
        if avatar_path:
            payload["avatar_url"] = avatar_path

        import requests
        try:
            r = requests.post("http://127.0.0.1:5000/update_profile", json=payload)
            if r.status_code == 200:
                print("[ProfileDialog] Profile updated:", r.json())
            else:
                print("[ProfileDialog] Error updating profile:", r.json())
        except Exception as e:
            print("[ProfileDialog] Network error saving profile:", e)

        self.accept()