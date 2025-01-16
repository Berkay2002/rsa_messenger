import sys
from PyQt5.QtWidgets import QApplication
from LoginWindow import LoginWindow

def main():
    app = QApplication(sys.argv)

    # Load dark mode QSS (optional)
    with open("dark.qss", "r") as f:
        dark_style = f.read()
    app.setStyleSheet(dark_style)

    # Show your login window
    login_window = LoginWindow()
    login_window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
