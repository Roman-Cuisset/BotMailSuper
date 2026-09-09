import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from handlers.admin import broadcast_command

class TestBroadcast(unittest.TestCase):
    def setUp(self):
        self.update = MagicMock()
        self.context = MagicMock()
        self.context.bot.send_message = AsyncMock()
        self.update.effective_user.id = 123456 # Admin ID
        self.update.message.reply_text = AsyncMock()
        self.update.message.reply_to_message = None
        
        # Mock config.ADMIN_IDS
        self.admin_ids_patcher = patch('handlers.admin.ADMIN_IDS', [123456])
        self.admin_ids_patcher.start()

    def tearDown(self):
        self.admin_ids_patcher.stop()

    @patch('handlers.admin.get_db')
    def test_broadcast_text(self, mock_get_db):
        # Mock database users
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            {'user_id': 111},
            {'user_id': 222}
        ]

        # Set args
        self.context.args = ["Hello", "World"]
        
        # Run command
        asyncio.run(broadcast_command(self.update, self.context))

        # Verify send_message called twice
        self.assertEqual(self.context.bot.send_message.call_count, 2)
        self.context.bot.send_message.assert_any_call(chat_id=111, text="Hello World", parse_mode="Markdown")
        self.context.bot.send_message.assert_any_call(chat_id=222, text="Hello World", parse_mode="Markdown")

    @patch('handlers.admin.get_db')
    def test_broadcast_reply(self, mock_get_db):
        # Mock database users
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            {'user_id': 333}
        ]

        # Set reply message
        self.update.message.reply_to_message = MagicMock()
        self.update.message.reply_to_message.copy = AsyncMock()

        # Run command
        asyncio.run(broadcast_command(self.update, self.context))

        # Verify copy called
        self.update.message.reply_to_message.copy.assert_called_with(chat_id=333)

if __name__ == '__main__':
    unittest.main()
