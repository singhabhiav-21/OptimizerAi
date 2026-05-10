import unittest
from unittest.mock import MagicMock, patch
from financial_Tracker.databaseDAO import sqlConnector, userDAO

from financial_Tracker.databaseDAO.Account import account_dao


class TestAccountFunctions(unittest.TestCase):
    def setUp(self):
        # Mock database connection and cursor
        self.conn_mock = MagicMock()
        self.cursor_mock = MagicMock()
        self.conn_mock.cursor.return_value = self.cursor_mock

        patcher1 = patch('financial_Tracker.databaseDAO.sqlConnector.get_connection', return_value=self.conn_mock)
        patcher2 = patch('financial_Tracker.databaseDAO.userDAO.hashAgain', side_effect=lambda salt, pw: "hashedpassword")
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.mock_get_connection = patcher1.start()
        self.mock_hashAgain = patcher2.start()

        # Rebind connection and cursor in the module to the mocks
        account_dao.conn = self.conn_mock
        account_dao.cursor = self.cursor_mock

    def test_addAccount_success(self):
        result = account_dao.addAccount(1, "My Savings", "savings", 5000, "USD", "Chase")
        self.assertTrue(result)
        self.cursor_mock.execute.assert_called()
        self.conn_mock.commit.assert_called_once()

    def test_add_money_success(self):
        self.cursor_mock.execute.return_value = None
        result = account_dao.add_money(1, 101, 1000)
        self.assertTrue(result)
        self.cursor_mock.execute.assert_called()
        self.conn_mock.commit.assert_called_once()

    def test_transfer_money_success(self):
        # Mock account balance
        self.cursor_mock.fetchone.side_effect = [(5000,), (1000,)]
        result = account_dao.transfer_money(1, 101, 102, 2000)
        self.assertTrue(result)
        self.conn_mock.commit.assert_called_once()

    def test_delete_account_success(self):
        # Mock fetching user_id and password
        self.cursor_mock.fetchone.side_effect = [(1,), ("salt:hashedpassword",)]
        result = account_dao.delete_account(101, "mypassword")
        self.assertTrue(result)
        self.conn_mock.commit.assert_called_once()

if __name__ == "__main__":
    unittest.main()
