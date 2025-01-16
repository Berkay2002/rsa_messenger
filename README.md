# RSA Messenger

RSA Messenger is a secure real-time messaging application built with Python. It uses **Flask** for the backend, **MongoDB** for data storage, **Flask-SocketIO** for real-time communication, and **PyCryptodome** for implementing RSA encryption to ensure end-to-end security.

---

## Features

- **Real-Time Messaging**: Communicate instantly using WebSockets.
- **End-to-End Encryption (E2EE)**: Messages are encrypted using RSA and can only be decrypted by the recipient.
- **Offline Message Storage**: Messages sent to offline users are stored securely on the server and delivered when the user reconnects.
- **User Authentication**: Secure login system with password hashing and RSA key management.
- **Web Interface**: A responsive web-based GUI.

---

## Project Structure

```plaintext
rsa_messenger/
├── app.py                       # Flask server
├── models.py                    # MongoDB models
├── crypto_utils.py              # RSA encryption/decryption logic
├── templates/
│   └── index.html               # Web interface
├── static/
│   ├── js/
│   │   └── main.js               # Client-side JavaScript
│   └── css/
│       └── styles.css            # Stylesheets
├── .env                         # Configuration for Flask/MongoDB
├── .gitignore                   # Git ignore file
├── README.md
├── Procfile                     # Deployment configuration
└── requirements.txt             # Dependency list