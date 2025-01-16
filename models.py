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

# Define collections
users_collection = db['users']
messages_collection = db['messages']
friends_collection = db['friends']         # New Collection for Friends
groups_collection = db['groups']           # New Collection for Groups

# Create indexes
try:
    print("Creating indexes...")
    users_collection.create_index("username", unique=True)
    messages_collection.create_index([("recipient", 1), ("delivered", 1)])
    friends_collection.create_index([("user", 1), ("friend", 1)], unique=True)  # Ensure unique friend pairs
    groups_collection.create_index("group_name", unique=True)                    # Ensure unique group names
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


def add_friend(user, friend):
    """
    Add a bidirectional friendship between two users.
    """
    try:
        if user == friend:
            raise ValueError("Cannot add yourself as a friend.")
        
        # Check if both users exist
        user_doc = users_collection.find_one({"username": user})
        friend_doc = users_collection.find_one({"username": friend})
        if not user_doc or not friend_doc:
            raise ValueError("Both users must exist to add as friends.")
        
        # Insert friendship both ways
        friends_collection.insert_one({"user": user, "friend": friend})
        friends_collection.insert_one({"user": friend, "friend": user})
        print(f"Friendship established between {user} and {friend}.")
    except Exception as e:
        print(f"Failed to add friend: {e}")
        raise

def get_friends(username):
    """
    Retrieve a list of friends for a given user.
    """
    try:
        friends = friends_collection.find({"user": username})
        return [friend['friend'] for friend in friends]
    except Exception as e:
        print(f"Failed to fetch friends for {username}: {e}")
        raise

def create_group(group_name, creator, members):
    """
    Create a new group with the specified members.
    """
    try:
        existing_group = groups_collection.find_one({"group_name": group_name})
        if existing_group:
            raise ValueError("Group name already exists.")
        
        # Ensure all members exist
        for member in members:
            user_doc = users_collection.find_one({"username": member})
            if not user_doc:
                raise ValueError(f"User {member} does not exist.")
        
        group_doc = {
            "group_name": group_name,
            "creator": creator,
            "members": members,
            "created_at": datetime.now(timezone.utc)
        }
        groups_collection.insert_one(group_doc)
        print(f"Group '{group_name}' created successfully with members: {members}.")
    except Exception as e:
        print(f"Failed to create group '{group_name}': {e}")
        raise

def add_member_to_group(group_name, username):
    """
    Add a member to an existing group.
    """
    try:
        group = groups_collection.find_one({"group_name": group_name})
        if not group:
            raise ValueError("Group does not exist.")
        
        if username in group['members']:
            raise ValueError(f"User {username} is already a member of the group.")
        
        users_collection.find_one({"username": username})  # Ensure user exists
        groups_collection.update_one(
            {"group_name": group_name},
            {"$push": {"members": username}}
        )
        print(f"User {username} added to group '{group_name}'.")
    except Exception as e:
        print(f"Failed to add member to group: {e}")
        raise

def get_groups(username):
    """
    Retrieve a list of groups that the user is a member of.
    """
    try:
        groups = groups_collection.find({"members": username})
        return [group['group_name'] for group in groups]
    except Exception as e:
        print(f"Failed to fetch groups for {username}: {e}")
        raise

def get_group_members(group_name):
    """
    Retrieve members of a specific group.
    """
    try:
        group = groups_collection.find_one({"group_name": group_name})
        if group:
            return group['members']
        return []
    except Exception as e:
        print(f"Failed to fetch members for group '{group_name}': {e}")
        raise
    
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
