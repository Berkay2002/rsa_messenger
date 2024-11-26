# RSA Messenger

RSA Messenger is a secure real-time messaging application built with Python. It uses **Flask** for the backend, **MongoDB** for data storage, **PyQt** for the graphical user interface (GUI), and **PyCryptodome** for implementing RSA encryption to ensure end-to-end security.

---

## Features

- **Real-Time Messaging**: Communicate instantly using WebSockets.
- **End-to-End Encryption (E2EE)**: Messages are encrypted using RSA and can only be decrypted by the recipient.
- **Offline Message Storage**: Messages sent to offline users are stored securely on the server and delivered when the user reconnects.
- **User Authentication**: Simple login system with RSA key management.
- **Modern Interface**: A clean and responsive GUI built with PyQt.

---

## Project Structure

```plaintext
rsa_messenger/
├── backend/
│   ├── app.py               # Flask server
│   ├── models.py            # MongoDB models
│   ├── encryption.py        # RSA key generation & encryption logic
│   ├── websocket_server.py  # WebSocket handler
├── frontend/
│   ├── main.py              # PyQt main application
│   ├── ui/
│   │   ├── login.ui         # Login screen UI
│   │   ├── chat.ui          # Chat screen UI
│   └── assets/              # Icons, styles, etc.
├── .env                     # Configuration for Flask/MongoDB
├── README.md
└── requirements.txt          # Dependency list
