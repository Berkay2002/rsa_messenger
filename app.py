import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

from models import (
    create_user,
    verify_user,
    save_message,
    fetch_undelivered_messages,
    mark_messages_as_delivered,
    messages_collection,
    users_collection,
    add_friend,
    get_friends,
    create_group,
    get_groups,
    add_member_to_group,
    get_group_members
)

app = Flask(__name__)
CORS(app)  # Enable CORS
socketio = SocketIO(app, async_mode='eventlet')

active_users = {}  # Track online users

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    public_key = data.get('public_key')
    encrypted_private_key = data.get('encrypted_private_key')  # optional

    if not username or not password or not public_key:
        return jsonify({"error": "username, password, and public_key are required"}), 400
    
    try:
        create_user(
            username=username,
            password=password,
            public_key=public_key,
            encrypted_private_key=encrypted_private_key
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user_doc = verify_user(username, password)
    if not user_doc:
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return jsonify({"error": "Incorrect password"}), 400
        else:
            return jsonify({"error": "User does not exist"}), 404

    return jsonify({
        "message": "Login successful",
        "public_key": user_doc.get("public_key", None),
        "encrypted_private_key": user_doc.get("encrypted_private_key", None)
    }), 200

@app.route('/send_message', methods=['POST'])
def send_message_route():
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
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    existing_user = users_collection.find_one({"username": username})
    if not existing_user:
        return jsonify({"error": "User does not exist"}), 400

    messages = fetch_undelivered_messages(username)

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
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    user_doc = users_collection.find_one({"username": username})
    if not user_doc:
        return jsonify({"error": f"User {username} not found"}), 404

    public_key = user_doc.get("public_key")
    if not public_key:
        return jsonify({"error": f"User {username} has no public key stored"}), 400

    return jsonify({"public_key": public_key}), 200

# ------------ Friend Management Routes ------------

@app.route('/add_friend', methods=['POST'])
def add_friend_route():
    data = request.get_json()
    user = data.get('user')
    friend = data.get('friend')
    
    if not user or not friend:
        return jsonify({"error": "Both user and friend usernames are required."}), 400
    
    try:
        add_friend(user, friend)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to add friend."}), 500
    
    return jsonify({"message": f"{friend} added as a friend."}), 200

@app.route('/get_friends', methods=['GET'])
def get_friends_route():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required."}), 400
    
    try:
        friends = get_friends(username)
    except Exception:
        return jsonify({"error": "Failed to retrieve friends."}), 500
    
    return jsonify({"friends": friends}), 200

# ------------ Group Management Routes ------------

@app.route('/create_group', methods=['POST'])
def create_group_route():
    data = request.get_json()
    group_name = data.get('group_name')
    creator = data.get('creator')
    members = data.get('members')  # List of usernames
    
    if not group_name or not creator or not members:
        return jsonify({"error": "group_name, creator, and members are required."}), 400
    
    try:
        create_group(group_name, creator, members)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to create group."}), 500
    
    return jsonify({"message": f"Group '{group_name}' created successfully."}), 201

@app.route('/get_groups', methods=['GET'])
def get_groups_route():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required."}), 400
    
    try:
        groups = get_groups(username)
    except Exception:
        return jsonify({"error": "Failed to retrieve groups."}), 500
    
    return jsonify({"groups": groups}), 200

@app.route('/add_member', methods=['POST'])
def add_member_route():
    data = request.get_json()
    group_name = data.get('group_name')
    username = data.get('username')
    
    if not group_name or not username:
        return jsonify({"error": "group_name and username are required."}), 400
    
    try:
        add_member_to_group(group_name, username)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to add member to group."}), 500
    
    return jsonify({"message": f"User {username} added to group '{group_name}'."}), 200

# ------------ SocketIO Events ------------

@socketio.on('connect')
def handle_connect():
    print("A user connected to the default namespace.")
    emit('connected', {'data': 'Connected to server'})

@socketio.on('user_join')
def handle_user_join(data):
    username = data.get('username')
    public_key = data.get('public_key')
    if not username or not public_key:
        emit("error", {"message": "Username and public_key are required."})
        print("Error: Username or public_key missing in user_join event.")
        return
    
    # Check if username is already connected
    if username in active_users:
        emit("error", {"message": "Username already connected."})
        print(f"Error: Username {username} already connected.")
        return

    active_users[username] = request.sid
    print(f"User joined: {username} with SID: {request.sid}")
    
    # Notify all users that a new user has joined
    emit("chat", {"message": f"{username} has joined the chat."}, broadcast=True)

@socketio.on('join_group')
def handle_join_group(data):
    group_name = data.get('group_name')
    username = data.get('username')
    
    if not group_name or not username:
        emit("error", {"message": "group_name and username are required to join a group."})
        return
    
    try:
        members = get_group_members(group_name)
        if username not in members:
            emit("error", {"message": "You are not a member of this group."})
            return
        
        room = f"group_{group_name}"
        join_room(room)
        emit("chat", {"message": f"{username} has joined the group '{group_name}'."}, room=room)
        print(f"User {username} joined group '{group_name}'.")
    except Exception as e:
        emit("error", {"message": "Failed to join group."})
        print(f"Error joining group: {e}")

@socketio.on('new_message')
def handle_new_message(data):
    recipient = data.get("recipient")      # Can be a username or group name
    message = data.get("message")
    is_group = data.get("is_group", False)
    sender = None

    # Identify the sender based on the session ID
    for user, sid in active_users.items():
        if sid == request.sid:
            sender = user
            break

    if not sender:
        emit("error", {"message": "User not identified."})
        print("Error: Sender not identified for the new_message event.")
        return

    if not recipient or not message:
        emit("error", {"message": "Recipient and message are required."})
        print("Error: Recipient or message missing in new_message event.")
        return

    if is_group:
        room = f"group_{recipient}"
        # Check if group exists and sender is a member
        try:
            members = get_group_members(recipient)
            if sender not in members:
                emit("error", {"message": "You are not a member of this group."})
                return
            
            # Broadcast the message to the group
            emit("chat", {"message": message, "username": sender, "group": recipient}, room=room)
            print(f"Sent message from {sender} to group '{recipient}'.")
        except Exception as e:
            emit("error", {"message": "Failed to send group message."})
            print(f"Error sending group message: {e}")
    else:
        # One-on-one message
        recipient_sid = active_users.get(recipient)
        if recipient_sid:
            emit("chat", {"message": message, "username": sender}, room=recipient_sid)
            print(f"Sent message from {sender} to {recipient}.")
        else:
            # Recipient offline, save message
            save_message(sender, recipient, message)
            print(f"Recipient {recipient} is offline. Message from {sender} saved.")
            emit("error", {"message": f"{recipient} is offline. Message saved for later delivery."})

@socketio.on('disconnect')
def handle_disconnect():
    for user, sid in list(active_users.items()):
        if sid == request.sid:
            del active_users[user]
            print(f"{user} disconnected. SID: {request.sid}")
            emit("chat", {"message": f"{user} has left the chat."}, broadcast=True)
            break

if __name__ == "__main__":
    socketio.run(app, debug=True, use_reloader=False)