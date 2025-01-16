from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
from passlib.hash import bcrypt

# Load environment variables
load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")
db_name = os.getenv("DB_NAME")

# Establish a connection
try:
    client = MongoClient(mongo_uri)
    db = client[db_name]
    print("Connected to MongoDB")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    raise SystemExit("Unable to connect to MongoDB, exiting...")

# Existing collections
users_collection = db['users']
messages_collection = db['messages']

# New for group chat
groups_collection = db['groups']           # { group_name, members: [username1, username2, ...] }
group_messages_collection = db['group_messages']  # store group-based messages

# Create or confirm indexes
try:
    users_collection.create_index("username", unique=True)
    messages_collection.create_index([("recipient", 1), ("delivered", 1)])
    groups_collection.create_index("group_name", unique=True)
    group_messages_collection.create_index("group_name")
    print("Indexes created successfully.")
except Exception as e:
    print(f"Failed to create indexes: {e}")

def create_user(username, password=None, public_key=None, encrypted_private_key=None):
    """
    Create a new user in the database with a hashed password, 
    storing a public key (and optionally an encrypted private key).
    Raises ValueError if user already exists.
    """
    try:
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            raise ValueError("User already exists")

        user_doc = {"username": username}

        # If you have a plaintext password, hash it for secure storage:
        if password:
            user_doc["password_hash"] = bcrypt.hash(password)

        # Store the public key
        if public_key:
            user_doc["public_key"] = public_key

        # Optionally store an encrypted private key
        if encrypted_private_key:
            user_doc["encrypted_private_key"] = encrypted_private_key

        users_collection.insert_one(user_doc)
        print(f"User {username} created successfully.")
    except Exception as e:
        print(f"Failed to create user {username}: {e}")
        raise

def verify_user(username, password):
    """
    Verify a user's password.
    Returns the user document if valid, otherwise None.
    """
    user_doc = users_collection.find_one({"username": username})
    if not user_doc:
        return None

    # If there's no password_hash in the doc, user wasn't created with a password
    if "password_hash" not in user_doc:
        return None

    # Compare the stored hash with the provided password
    if bcrypt.verify(password, user_doc["password_hash"]):
        return user_doc
    return None

def update_public_key(username, new_public_key):
    """
    If you ever need to update the stored public key.
    """
    users_collection.update_one(
        {"username": username},
        {"$set": {"public_key": new_public_key}}
    )

def save_message(sender, recipient, encrypted_message):
    """Save an encrypted message to the database."""
    try:
        message = {
            "sender": sender,
            "recipient": recipient,
            "encrypted_message": encrypted_message,
            "delivered": False,
            "read": False,
            "timestamp": datetime.now(timezone.utc)
        }
        messages_collection.insert_one(message)
        print(f"Message from {sender} to {recipient} saved successfully.")
    except Exception as e:
        print(f"Failed to save message from {sender} to {recipient}: {e}")
        raise

def fetch_undelivered_messages(username):
    """Retrieve undelivered messages for a specific user."""
    try:
        msgs = messages_collection.find({"recipient": username, "delivered": False})
        return [
            {
                "sender": msg["sender"],
                "encrypted_message": msg["encrypted_message"],
                "timestamp": msg.get("timestamp", None),
                "delivered": msg.get("delivered", False),
                "read": msg.get("read", False)
            }
            for msg in msgs
        ]
    except Exception as e:
        print(f"Failed to fetch undelivered messages for {username}: {e}")
        raise

def mark_messages_as_delivered(username):
    """Mark all messages for a user as delivered."""
    try:
        result = messages_collection.update_many(
            {"recipient": username, "delivered": False},
            {"$set": {"delivered": True}}
        )
        print(f"Marked {result.modified_count} messages as delivered for {username}.")
    except Exception as e:
        print(f"Failed to mark messages as delivered for {username}: {e}")
        raise
    
def add_friend(userA, userB):
    """
    Add userB to userA's friends list and vice versa.
    """
    users_collection.update_one(
        {"username": userA},
        {"$addToSet": {"friends": userB}}
    )
    users_collection.update_one(
        {"username": userB},
        {"$addToSet": {"friends": userA}}
    )

# --------------------
# Profile & Groups
# --------------------
def update_profile(username, display_name=None, avatar_url=None):
    """
    Update user profile fields in the DB (display_name, avatar_url, etc.).
    """
    update_data = {}
    if display_name is not None:
        update_data["display_name"] = display_name
    if avatar_url is not None:
        update_data["avatar_url"] = avatar_url
    if not update_data:
        return 0  # nothing to update

    result = users_collection.update_one(
        {"username": username},
        {"$set": update_data}
    )
    return result.modified_count

def get_profile(username):
    """
    Return the user's profile (display_name, avatar_url, etc.).
    """
    user_doc = users_collection.find_one({"username": username})
    if not user_doc:
        return None
    return {
        "username": user_doc["username"],
        "display_name": user_doc.get("display_name"),
        "avatar_url": user_doc.get("avatar_url"),
    }

def create_group(group_name, creator):
    """
    Create a new group with the given name. The creator is automatically joined.
    """
    existing = groups_collection.find_one({"group_name": group_name})
    if existing:
        raise ValueError("Group already exists")

    group_doc = {
        "group_name": group_name,
        "members": [creator],
        "created_at": datetime.now(timezone.utc)
    }
    groups_collection.insert_one(group_doc)
    print(f"Group '{group_name}' created by {creator}.")

def join_group(group_name, username):
    """
    Add a user to the group's member list.
    """
    group_doc = groups_collection.find_one({"group_name": group_name})
    if not group_doc:
        raise ValueError("Group does not exist")

    if username in group_doc["members"]:
        raise ValueError(f"{username} is already in the group")

    groups_collection.update_one(
        {"group_name": group_name},
        {"$push": {"members": username}}
    )
    print(f"{username} joined group '{group_name}'.")

def send_group_message(group_name, sender, encrypted_message):
    """
    Save a group message in the database. 
    In a robust E2E scenario, you'd handle group-based encryption differently.
    """
    group_doc = groups_collection.find_one({"group_name": group_name})
    if not group_doc:
        raise ValueError("Group not found")
    if sender not in group_doc["members"]:
        raise ValueError("Sender not in group")

    msg_doc = {
        "group_name": group_name,
        "sender": sender,
        "encrypted_message": encrypted_message,
        "timestamp": datetime.now(timezone.utc)
    }
    group_messages_collection.insert_one(msg_doc)
    print(f"Group message saved for '{group_name}' from {sender}.")

def fetch_group_messages(group_name, since=None):
    """
    Retrieve all messages for a given group (optionally since a certain time).
    """
    query = {"group_name": group_name}
    if since:
        query["timestamp"] = {"$gt": since}
    cursor = group_messages_collection.find(query).sort("timestamp", 1)
    results = []
    for doc in cursor:
        results.append({
            "sender": doc["sender"],
            "encrypted_message": doc["encrypted_message"],
            "timestamp": doc["timestamp"].isoformat() if doc["timestamp"] else None
        })
    return results