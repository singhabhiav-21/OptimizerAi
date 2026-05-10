import unittest
from unittest.mock import MagicMock, patch
from financial_Tracker.databaseDAO.transaction.transaction_DAO import (
    register_transaction,
    delete_transaction,
    update_transaction,
    get_transactions,
    get_transaction
)


class TestTransactionDAO(unittest.TestCase):

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_register_transaction_success(self, mock_conn, mock_cursor):
        result = register_transaction(
            user_id=1,
            category_id=2,
            name="Grocery",
            amount=50.00,
            description="Weekly groceries",
            transaction_date="2025-10-15"
        )

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        self.assertTrue(result)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_register_transaction_without_date(self, mock_conn, mock_cursor):
        result = register_transaction(
            user_id=1,
            category_id=2,
            name="Grocery",
            amount=50.00,
            description="Weekly groceries"
        )

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        self.assertTrue(result)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_delete_transaction_success(self, mock_conn, mock_cursor):
        result = delete_transaction(transaction_id=1, user_id=1)

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        self.assertTrue(result)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_update_transaction_success(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (1, 1, 2, "Old Name", 50.00, "Old desc", "2025-10-15", "2025-10-15")

        result = update_transaction(
            transaction_id=1,
            user_id=1,
            name="New Name",
            amount=75.00
        )

        self.assertTrue(result)
        mock_conn.commit.assert_called()

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_update_transaction_not_found(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = None

        result = update_transaction(
            transaction_id=999,
            user_id=1,
            name="New Name"
        )

        self.assertFalse(result)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_update_transaction_no_changes(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (1, 1, 2, "Name", 50.00, "desc", "2025-10-15", "2025-10-15")

        result = update_transaction(
            transaction_id=1,
            user_id=1
        )

        self.assertFalse(result)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_update_transaction_invalid_amount(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = (1, 1, 2, "Name", 50.00, "desc", "2025-10-15", "2025-10-15")

        result = update_transaction(
            transaction_id=1,
            user_id=1,
            amount="invalid"
        )

        self.assertFalse(result)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_get_transactions_success(self, mock_conn, mock_cursor):
        mock_cursor.fetchall.return_value = [
            (1, 1, 2, "Grocery", 50.00, "Weekly", "2025-10-15", "2025-10-15"),
            (2, 1, 3, "Gas", 40.00, "Fuel", "2025-10-14", "2025-10-14")
        ]

        result = get_transactions(user_id=1)

        self.assertEqual(len(result), 2)
        self.assertNotEqual(result, False)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_get_transactions_not_found(self, mock_conn, mock_cursor):
        mock_cursor.fetchall.return_value = None

        result = get_transactions(user_id=999)

        self.assertFalse(result)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_get_transaction_success(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = ("Grocery", 50.00, "Weekly groceries", "2025-10-15")

        result = get_transaction(transaction_id=1, user_id=1)

        self.assertEqual(result[0], "Grocery")
        self.assertEqual(result[1], 50.00)
        self.assertNotEqual(result, False)

    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.cursor')
    @patch('financial_Tracker.databaseDAO.transaction.transaction_DAO.conn')
    def test_get_transaction_not_found(self, mock_conn, mock_cursor):
        mock_cursor.fetchone.return_value = None

        result = get_transaction(transaction_id=999, user_id=1)

        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()