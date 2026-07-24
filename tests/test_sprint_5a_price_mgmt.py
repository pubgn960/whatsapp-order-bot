import os
import unittest
from unittest.mock import MagicMock, patch

import config
from app.handlers.order_flow import handle_order_flow_message
from app.services.conversation_state import get_state, set_state
import database


class TestSprint5APriceManagement(unittest.TestCase):
    def setUp(self):
        self.admin_phone = "923346781828"
        self.user_phone = "923000000000"
        config.ADMIN_PHONE = self.admin_phone
        database.ensure_prices_schema()
        set_state(self.admin_phone, {})
        set_state(self.user_phone, {})

    def tearDown(self):
        set_state(self.admin_phone, {})
        set_state(self.user_phone, {})
        # Cleanup any test package 99999 or test additions
        conn = database._get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM prices WHERE package_cp = 99999 OR package_cp = 13000")
        conn.commit()
        conn.close()

    @patch("app.handlers.order_flow.send_text_message")
    def test_unauthorized_non_admin_access(self, mock_send_text):
        message = {"type": "text", "text": {"body": "/price"}}
        handle_order_flow_message(self.user_phone, message)
        mock_send_text.assert_called_once_with(
            self.user_phone, "⛔ You are not authorized to use this command."
        )

    @patch("app.handlers.order_flow.send_interactive_list_message")
    def test_admin_main_menu(self, mock_send_list):
        message = {"type": "text", "text": {"body": "/price"}}
        handle_order_flow_message(self.admin_phone, message)
        mock_send_list.assert_called_once()
        args, kwargs = mock_send_list.call_args
        self.assertEqual(kwargs.get("to"), self.admin_phone)
        self.assertEqual(kwargs.get("body_text"), "💰 Price Management")
        rows = kwargs.get("rows", [])
        titles = [r.get("title") for r in rows]
        self.assertIn("1️⃣ 👀 View Prices", titles)
        self.assertIn("2️⃣ ✏️ Edit Price", titles)
        self.assertIn("3️⃣ ➕ Add Package", titles)
        self.assertIn("4️⃣ ➖ Remove Package", titles)
        self.assertIn("5️⃣ ❌ Cancel", titles)

    @patch("app.handlers.order_flow.send_text_message")
    def test_view_prices(self, mock_send_text):
        message = {
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {"id": "pm_view", "title": "1️⃣ 👀 View Prices"},
            },
        }
        handle_order_flow_message(self.admin_phone, message)
        mock_send_text.assert_called_once()
        args, kwargs = mock_send_text.call_args
        body = args[1]
        self.assertIn("📦 Normal Orders", body)
        self.assertIn("10900 CP — $", body)

    @patch("app.handlers.order_flow.send_text_message")
    def test_edit_price_flow(self, mock_send_text):
        # Step 1: Click Edit Price
        msg1 = {
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {"id": "pm_edit_cat", "title": "2️⃣ ✏️ Edit Price"},
            },
        }
        with patch("app.handlers.order_flow.send_interactive_buttons_message") as mock_buttons:
            handle_order_flow_message(self.admin_phone, msg1)
            mock_buttons.assert_called_once()

        # Step 2: Select Normal Orders Category
        msg2 = {
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "pm_edit_sel_normal_orders", "title": "📦 Normal Orders"},
            },
        }
        with patch("app.handlers.order_flow.send_interactive_list_message") as mock_list:
            handle_order_flow_message(self.admin_phone, msg2)
            mock_list.assert_called_once()

        # Step 3: Select 10900 CP package
        msg3 = {
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {"id": "pm_edit_pkg_10900", "title": "10900 CP - $67"},
            },
        }
        handle_order_flow_message(self.admin_phone, msg3)
        mock_send_text.assert_called()
        self.assertIn("Current Price", mock_send_text.call_args[0][1])

        # Step 4: Admin enters new price 68
        msg4 = {"type": "text", "text": {"body": "68"}}
        handle_order_flow_message(self.admin_phone, msg4)
        last_msg = mock_send_text.call_args[0][1]
        self.assertIn("✅ Price Updated Successfully", last_msg)
        self.assertIn("New Price:\n$68", last_msg)

        # Verify DB updated and customer immediately sees new price
        price_in_db = database.get_price(10900)
        self.assertEqual(float(price_in_db), 68.0)

    @patch("app.handlers.order_flow.send_text_message")
    def test_add_package_flow(self, mock_send_text):
        # Step 1: Select Add Package category
        msg1 = {
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "pm_add_sel_normal_orders", "title": "📦 Normal Orders"},
            },
        }
        handle_order_flow_message(self.admin_phone, msg1)

        # Step 2: Enter CP 13000
        msg2 = {"type": "text", "text": {"body": "13000 CP"}}
        handle_order_flow_message(self.admin_phone, msg2)

        # Step 3: Enter Price 79
        msg3 = {"type": "text", "text": {"body": "79"}}
        handle_order_flow_message(self.admin_phone, msg3)
        last_msg = mock_send_text.call_args[0][1]
        self.assertIn("✅ Package Added Successfully", last_msg)

        # Verify DB contains 13000 CP with price 79
        price_in_db = database.get_price(13000)
        self.assertEqual(float(price_in_db), 79.0)

    @patch("app.handlers.order_flow.send_text_message")
    def test_remove_package_flow(self, mock_send_text):
        # First ensure package 13000 exists
        database.add_package("Normal Orders", 13000, 79)

        # Step 1: Select Remove package 13000
        msg1 = {
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {"id": "pm_remove_pkg_13000", "title": "13000 CP"},
            },
        }
        set_state(self.admin_phone, {"stage": "awaiting_pm_remove_package", "pm_category": "Normal Orders"})
        with patch("app.handlers.order_flow.send_interactive_buttons_message") as mock_buttons:
            handle_order_flow_message(self.admin_phone, msg1)
            mock_buttons.assert_called_once()
            self.assertIn("Confirm Delete", mock_buttons.call_args[1]["body_text"])

        # Step 2: Confirm Delete
        msg2 = {
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "pm_remove_confirm_yes", "title": "✅ Confirm Delete"},
            },
        }
        handle_order_flow_message(self.admin_phone, msg2)
        last_msg = mock_send_text.call_args[0][1]
        self.assertIn("✅ Package Removed Successfully", last_msg)

        # Verify soft deleted in DB
        price_in_db = database.get_price(13000)
        self.assertIsNone(price_in_db)

    @patch("app.handlers.order_flow.send_text_message")
    def test_cancel_flow(self, mock_send_text):
        msg = {
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {"id": "pm_cancel", "title": "5️⃣ ❌ Cancel"},
            },
        }
        handle_order_flow_message(self.admin_phone, msg)
        mock_send_text.assert_called_once_with(self.admin_phone, "❌ Price Management Cancelled.")
        self.assertEqual(get_state(self.admin_phone), {})


if __name__ == "__main__":
    unittest.main()
