from models import users_collection, messages_collection
from datetime import datetime, timezone

# Test user creation
try:
    if users_collection.find_one({"username": "test_user"}):
        print("User 'test_user' already exists!")
    else:
        users_collection.insert_one({"username": "test_user", "public_key": "sample_public_key"})
        print("User created!")
except Exception as e:
    print(f"Failed to create user: {e}")

# Test message creation
try:
    messages_collection.insert_one({
        "sender": "test_user",
        "recipient": "another_user",
        "encrypted_message": "sample_message",
        "delivered": False,
        "read": False,
        "timestamp": datetime.now(timezone.utc)  # Add timestamp field
    })
    print("Message saved!")
except Exception as e:
    print(f"Failed to save message: {e}")
