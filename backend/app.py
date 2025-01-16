from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import logging
from datetime import datetime

# Import the updated model functions
from models import (
    create_user,
    verify_user,
    save_message,
    fetch_undelivered_messages,
    mark_messages_as_delivered,
    fetch_group_messages,
    messages_collection,
    users_collection,
    update_profile,
    get_profile,
    create_group,
    join_group,
    send_group_message,
    groups_collection,
    add_friend
)

app = Flask(__name__)
socketio = SocketIO(app)

active_users = {}  # Track online users

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

@app.route("/update_profile", methods=["POST"])
def update_profile_route():
    """
    Update the profile fields (display_name, avatar_url).
    Expects JSON { "username": ..., "display_name": "...", "avatar_url": "..." }
    """
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    display_name = data.get("display_name")
    avatar_url = data.get("avatar_url")
    updated_count = update_profile(username, display_name, avatar_url)
    if updated_count > 0:
        return jsonify({"message": "Profile updated."}), 200
    return jsonify({"message": "No changes made."}), 200

@app.route("/get_profile", methods=["GET"])
def get_profile_route():
    """
    Return the profile info for a given user.
    Example: GET /get_profile?username=Alice
    """
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Username required"}), 400
    profile_data = get_profile(username)
    if not profile_data:
        return jsonify({"error": "User not found"}), 404
    return jsonify(profile_data), 200

@app.route("/create_group", methods=["POST"])
def create_group_route():
    """
    Create a new group. 
    Expects JSON { "group_name": "...", "creator": "..." }
    """
    data = request.get_json()
    group_name = data.get("group_name")
    creator = data.get("creator")
    if not group_name or not creator:
        return jsonify({"error": "group_name and creator required"}), 400
    try:
        create_group(group_name, creator)
        return jsonify({"message": f"Group {group_name} created."}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/join_group", methods=["POST"])
def join_group_route():
    """
    Add a user to an existing group.
    Expects JSON { "group_name": "...", "username": "..." }
    """
    data = request.get_json()
    group_name = data.get("group_name")
    username = data.get("username")
    if not group_name or not username:
        return jsonify({"error": "group_name and username required"}), 400
    try:
        join_group(group_name, username)
        return jsonify({"message": f"{username} joined group {group_name}."}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/send_group_message", methods=["POST"])
def send_group_message_route():
    """
    Store a message in the group. 
    Expects JSON { "group_name": "...", "sender": "...", "message": <hex-encoded> }
    """
    data = request.get_json()
    group_name = data.get("group_name")
    sender = data.get("sender")
    encrypted_message = data.get("message")
    if not group_name or not sender or not encrypted_message:
        return jsonify({"error": "group_name, sender, and message required"}), 400
    try:
        send_group_message(group_name, sender, encrypted_message)
        return jsonify({"message": "Group message sent"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/fetch_group_messages", methods=["GET"])
def fetch_group_messages_route():
    """
    Return all messages in a group. Optionally pass 'since' param (ISO8601).
    Example: GET /fetch_group_messages?group_name=TestGroup
    """
    group_name = request.args.get("group_name")
    if not group_name:
        return jsonify({"error": "group_name required"}), 400

    since_str = request.args.get("since")
    since_dt = None
    # parse since_str if provided
    if since_str:
        try:
            since_dt = datetime.fromisoformat(since_str)
        except:
            pass

    msgs = fetch_group_messages(group_name, since=since_dt)
    return jsonify({"messages": msgs}), 200

# Just a convenience route: "Who is online?"
@app.route("/online_users", methods=["GET"])
def online_users():
    """
    Return the list of currently online usernames.
    """
    return jsonify({"online_users": list(active_users.keys())}), 200

@app.route("/all_groups", methods=["GET"])
def all_groups():
    """
    Return the list of all groups.
    """
    groups = groups_collection.find({}, {"_id": 0, "group_name": 1})
    group_names = [group["group_name"] for group in groups]
    return jsonify({"groups": group_names}), 200


# ------------
# Socket.IO Events
# ------------

@socketio.on('connect')
def handle_connect():
    print("A user connected.")

@socketio.on('register')
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
    # Optionally broadcast the updated online user list
    socketio.emit('online_users_update', {"online_users": list(active_users.keys())})


@socketio.on('send_message')
def handle_send_message(data):
    """
    Real-time message sending via Socket.IO. 
    If recipient is online, deliver immediately; otherwise, save to DB.
    """
    sender = data['sender']
    recipient = data['recipient']
    encrypted_message = data['message']

    if recipient in active_users:
        emit('receive_message', data, to=active_users[recipient])
    else:
        save_message(sender, recipient, encrypted_message)

    # Add each user to the other's friends list
    add_friend(sender, recipient)
        
@socketio.on('send_group_message')
def handle_send_group_message_socketio(data):
    """
    Real-time group message. If the group members are online, push immediately.
    Otherwise, store it. (This is a simplified approach - no E2E group encryption.)
    """
    group_name = data.get("group_name")
    sender = data.get("sender")
    encrypted_message = data.get("message")
    if not group_name or not sender or not encrypted_message:
        return

    try:
        send_group_message(group_name, sender, encrypted_message)
        # Now broadcast to all online members in that group
        group_doc = groups_collection.find_one({"group_name": group_name})
        if group_doc:
            for member in group_doc["members"]:
                if member in active_users:
                    emit('receive_group_message', data, to=active_users[member])
    except ValueError as e:
        emit('error', {"message": str(e)})

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
    socketio.run(app, debug=True, use_reloader=False)