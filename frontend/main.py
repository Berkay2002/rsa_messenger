from PyQt5.QtWidgets import QApplication
from LoginWindow import LoginWindow
import sys

if __name__ == "__main__":
    # Initialize the PyQt application
    app = QApplication(sys.argv)

    # Create and show the login window
    login_window = LoginWindow()
    login_window.show()

    # Execute the application event loop
    sys.exit(app.exec_())