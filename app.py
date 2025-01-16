from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import logging
from flask_cors import CORS

# Import the updated model functions
from models import (
    create_user,
    verify_user,
    save_message,
    fetch_undelivered_messages,
    mark_messages_as_delivered,
    messages_collection,
    users_collection
)

app = Flask(__name__, static_folder='frontend')
CORS(app)  # Enable CORS
socketio = SocketIO(app, async_mode='eventlet')

active_users = {}  # Track online users

@app.route('/')
def root():
    return "Welcome to the RSA Messenger API!"


@app.route('/register', methods=['POST'])
def register_user():
    """
    Register a new user with username, password, public_key, 
    and optionally encrypted_private_key.
    """
    data = request.get_json()

    username = data.get('username')
    password = data.get('password')
    public_key = data.get('public_key')
    encrypted_private_key = data.get('encrypted_private_key')  # optional

    # Basic checks
    if not username or not password or not public_key:
        return jsonify({"error": "username, password, and public_key are required"}), 400
    
    # Try creating user in DB
    try:
        create_user(
            username=username,
            password=password,
            public_key=public_key,
            encrypted_private_key=encrypted_private_key
        )
    except ValueError as e:
        # E.g. "User already exists"
        return jsonify({"error": str(e)}), 400
    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login_user():
    """
    Login an existing user by verifying username + password. 
    Return the user's stored public_key and encrypted_private_key if it exists.
    """
    data = request.get_json()

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    # Check the DB
    user_doc = verify_user(username, password)
    if not user_doc:
        # Could be user not found or incorrect password
        # Distinguish 404 vs 400 if you like
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            # Means user exists but password was incorrect
            return jsonify({"error": "Incorrect password"}), 400
        else:
            # Means user does not exist
            return jsonify({"error": "User does not exist"}), 404

    # If we get here, password is correct
    return jsonify({
        "message": "Login successful",
        "public_key": user_doc.get("public_key", None),
        "encrypted_private_key": user_doc.get("encrypted_private_key", None)
    }), 200

@app.route('/send_message', methods=['POST'])
def send_message_route():
    """Save a message to the database."""
    data = request.get_json()
    sender = data['sender']
    recipient = data['recipient']
    encrypted_message = data['message']
    
    existing_user = users_collection.find_one({"username": recipient})
    if not existing_user:
        return jsonify({"error": f"Recipient {recipient} does not exist"}), 400
    
    save_message(sender, recipient, encrypted_message)
    return jsonify({"message": "Message sent!"}), 200

@app.route('/fetch_messages', methods=['GET'])
def fetch_messages_route():
    """Fetch undelivered messages for a user."""
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    existing_user = users_collection.find_one({"username": username})
    if not existing_user:
        return jsonify({"error": "User does not exist"}), 400

    messages = fetch_undelivered_messages(username)

    # Format timestamps as ISO 8601
    formatted_messages = [
        {
            "sender": msg["sender"],
            "encrypted_message": msg["encrypted_message"],
            "timestamp": msg["timestamp"].isoformat() if msg["timestamp"] else None
        }
        for msg in messages
    ]

    mark_messages_as_delivered(username)
    return jsonify({"messages": formatted_messages}), 200

@app.route('/get_public_key', methods=['GET'])
def get_public_key():
    """
    Return the public key of the user specified by `?username=...`.
    Example: GET /get_public_key?username=Berkay
    """
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    # Look up the user in Mongo
    user_doc = users_collection.find_one({"username": username})
    if not user_doc:
        return jsonify({"error": f"User {username} not found"}), 404

    # Make sure the user has a "public_key" field
    public_key = user_doc.get("public_key")
    if not public_key:
        return jsonify({"error": f"User {username} has no public key stored"}), 400

    return jsonify({"public_key": public_key}), 200


# ------------
# SocketIO Events
# ------------

@socketio.on('connect', namespace='/chat')
def handle_connect():
    print("A user connected.")
    emit('connected', {'data': 'Connected to server'}, namespace='/chat')

@socketio.on('register', namespace='/chat')
def handle_register(data):
    """
    Called if a client tries to 'register' via Socket.IO. 
    In your PyQt, you might just do HTTP calls for register/login,
    but you can also do it over Socket.IO if you prefer.
    """
    username = data.get('username')
    if not username or not users_collection.find_one({"username": username}):
        emit('error', {"message": "Invalid or non-existent user"})
        return
    active_users[username] = request.sid
    print(f"{username} is online.")

@socketio.on('send_message', namespace='/chat')
def handle_send_message(data):
    """
    Real-time message sending via Socket.IO. 
    If recipient is online, deliver immediately; otherwise, save to DB.
    """
    sender = data['sender']
    recipient = data['recipient']
    encrypted_message = data['message']

    if recipient in active_users:
        # Send in real-time
        emit('receive_message', data, to=active_users[recipient])
    else:
        # Save to DB for offline recipient
        save_message(sender, recipient, encrypted_message)

@socketio.on('message_read')
def handle_message_read(data):
    message_id = data['message_id']
    messages_collection.update_one(
        {"_id": message_id},
        {"$set": {"read": True}}
    )

@socketio.on('disconnect', namespace='/chat')
def handle_disconnect():
    for user, sid in list(active_users.items()):
        if sid == request.sid:
            del active_users[user]
            print(f"{user} disconnected.")
            break

if __name__ == "__main__":
    socketio.run(app, debug=True, use_reloader=False)