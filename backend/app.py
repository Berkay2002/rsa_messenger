from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from models import create_user, save_message, fetch_undelivered_messages, mark_messages_as_delivered, messages_collection

app = Flask(__name__)
socketio = SocketIO(app)

active_users = {}  # Track online users

@app.route('/register', methods=['POST'])
def register_user():
    """Register a new user."""
    data = request.get_json()
    username = data['username']
    public_key = data['public_key']
    
    try:
        create_user(username, public_key)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/send_message', methods=['POST'])
def send_message():
    """Save a message to the database."""
    data = request.get_json()
    sender = data['sender']
    recipient = data['recipient']
    encrypted_message = data['message']
    
    save_message(sender, recipient, encrypted_message)
    return jsonify({"message": "Message sent!"}), 200

@app.route('/fetch_messages', methods=['GET'])
def fetch_messages():
    """Fetch undelivered messages for a user."""
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    messages = fetch_undelivered_messages(username)

    # Format timestamp as ISO 8601 string for JSON response
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

@socketio.on('connect')
def handle_connect():
    print("A user connected.")

@socketio.on('register')
def handle_register(data):
    username = data['username']
    active_users[username] = request.sid
    print(f"{username} is online.")

@socketio.on('send_message')
def handle_send_message(data):
    sender = data['sender']
    recipient = data['recipient']
    encrypted_message = data['message']

    if recipient in active_users:
        # Send the message to the recipient in real time
        emit('receive_message', data, to=active_users[recipient])
    else:
        # Save the message to the database if the recipient is offline
        save_message(sender, recipient, encrypted_message)

@socketio.on('message_read')
def handle_message_read(data):
    message_id = data['message_id']
    messages_collection.update_one(
        {"_id": message_id},
        {"$set": {"read": True}}
    )


@socketio.on('disconnect')
def handle_disconnect():
    for user, sid in list(active_users.items()):
        if sid == request.sid:
            del active_users[user]
            print(f"{user} disconnected.")
            break

if __name__ == "__main__":
    socketio.run(app, debug=True)