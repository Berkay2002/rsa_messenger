from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
from passlib.hash import bcrypt  # <-- For password hashing

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

# Create indexes
try:
    print("Creating indexes...")
    users_collection.create_index("username", unique=True)  # Ensure unique usernames
    messages_collection.create_index([("recipient", 1), ("delivered", 1)])  # For undelivered message lookups
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
