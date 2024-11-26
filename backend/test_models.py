import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from models import create_user, save_message, fetch_undelivered_messages, mark_messages_as_delivered

class TestModels(unittest.TestCase):

    @patch('models.users_collection')
    def test_create_user(self, mock_users_collection):
        """Test creating a new user."""
        mock_users_collection.find_one.return_value = None  # Simulate no duplicate user
        create_user("test_user", "test_public_key")
        mock_users_collection.insert_one.assert_called_once_with({
            "username": "test_user",
            "public_key": "test_public_key"
        })

    @patch('models.messages_collection')
    def test_save_message(self, mock_messages_collection):
        """Test saving an encrypted message."""
        now = datetime.now(timezone.utc)  # Simulate the current timestamp
        with patch('models.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.timezone = timezone

            save_message("sender_user", "recipient_user", "encrypted_message")

            mock_messages_collection.insert_one.assert_called_once_with({
                "sender": "sender_user",
                "recipient": "recipient_user",
                "encrypted_message": "encrypted_message",
                "delivered": False,
                "read": False,
                "timestamp": now  # Ensure timestamp is set correctly
            })

    @patch('models.messages_collection')
    def test_fetch_undelivered_messages(self, mock_messages_collection):
        """Test fetching undelivered messages."""
        # Simulate undelivered messages
        mock_messages_collection.find.return_value = [
            {
                "sender": "sender_user",
                "encrypted_message": "message1",
                "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "delivered": False,
                "read": False
            },
            {
                "sender": "sender_user",
                "encrypted_message": "message2",
                "timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc),
                "delivered": False,
                "read": False
            }
        ]

        messages = fetch_undelivered_messages("recipient_user")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["encrypted_message"], "message1")
        self.assertEqual(messages[0]["timestamp"], datetime(2024, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(messages[0]["delivered"], False)
        self.assertEqual(messages[0]["read"], False)

    @patch('models.messages_collection')
    def test_mark_messages_as_delivered(self, mock_messages_collection):
        """Test marking messages as delivered."""
        mark_messages_as_delivered("recipient_user")
        mock_messages_collection.update_many.assert_called_once_with(
            {"recipient": "recipient_user", "delivered": False},
            {"$set": {"delivered": True}}
        )

if __name__ == "__main__":
    unittest.main()
