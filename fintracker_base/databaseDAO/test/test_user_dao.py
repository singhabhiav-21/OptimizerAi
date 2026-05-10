import unittest
from financial_Tracker.databaseDAO.userDAO import register, logIn, update_userinfo, update_password, get_connection

class TestUserManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # This runs once before all tests
        cls.conn = get_connection()
        cls.cursor = cls.conn.cursor()
        # Optionally, clear the test users table
        cls.cursor.execute("DELETE FROM users")
        cls.conn.commit()

    def test_register_valid_user(self):
        result = register("AliceTest", "alice@example.com", "Password123!")
        self.assertEqual(result[0], True)

    def test_register_short_name(self):
        result = register("Al", "al@example.com", "Password123!")
        self.assertFalse(result)

    def test_register_invalid_email_duplicate(self):
        register("BobTest", "bob@example.com", "Password123!")
        result = register("BobTest2", "bob@example.com", "Password123!")
        self.assertFalse(result)

    def test_register_invalid_password(self):
        result = register("CharlieTest", "charlie@example.com", "pass")
        self.assertFalse(result)

    def test_login_successful(self):
        register("DaveTest", "dave@example.com", "Password123!")
        result = logIn("dave@example.com", "Password123!")
        self.assertTrue(result)

    def test_login_wrong_password(self):
        register("EveTest", "eve@example.com", "Password123!")
        result = logIn("eve@example.com", "WrongPassword!")
        self.assertFalse(result)

    def test_update_userinfo_name(self):
        register("FrankTest", "frank@example.com", "Password123!")
        result = update_userinfo(email="frank@example.com", name="FrankNew")
        self.assertTrue(result)

    def test_update_userinfo_email(self):
        register("GraceTest", "grace@example.com", "Password123!")
        result = update_userinfo(email="grace@example.com", new_email="grace2@example.com")
        self.assertTrue(result)

    def test_update_password_success(self):
        register("HankTest", "hank@example.com", "Password123!")
        result = update_password("hank@example.com", "Password123!", "NewPassword123!", "NewPassword123!")
        self.assertTrue(result)

    def test_update_password_wrong_old(self):
        register("IvyTest", "ivy@example.com", "Password123!")
        result = update_password("ivy@example.com", "WrongOldPassword!", "NewPassword123!", "NewPassword123!")
        self.assertFalse(result)

    def test_update_password_mismatch(self):
        register("JackTest", "jack@example.com", "Password123!")
        result = update_password("jack@example.com", "Password123!", "NewPassword123!", "Mismatch123!")
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
