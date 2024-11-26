from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone
import os

# Load environment variables
load_dotenv()

# Retrieve MongoDB URI from .env file
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

# Example functions
def create_user(username, public_key):
    """Create a new user in the database, checking for duplicates."""
    try:
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            raise ValueError("User already exists")
        user = {"username": username, "public_key": public_key}
        users_collection.insert_one(user)
        print(f"User {username} created successfully.")
    except Exception as e:
        print(f"Failed to create user {username}: {e}")
        raise

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
        messages = messages_collection.find({"recipient": username, "delivered": False})
        # Convert MongoDB objects to a JSON-serializable format
        return [
            {
                "sender": msg["sender"],
                "encrypted_message": msg["encrypted_message"],
                "timestamp": msg.get("timestamp", None),
                "delivered": msg.get("delivered", False),
                "read": msg.get("read", False)
            }
            for msg in messages
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
