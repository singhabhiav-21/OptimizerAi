from contextlib import contextmanager

from fintracker_base.databaseDAO.sqlConnector import get_connection, db
from fintracker_base.databaseDAO.userDAO import hashAgain



def addAccount(userid, name, type, balance, currency, platform_name):
    balance, balance_msg = check_balance(balance)
    if balance is False:
        print(f"Balance validation failed: {balance_msg}")
        return False

    type, type_msg = checkaccountType(type)
    if type is False:
        print(f"Account type validation failed: {type_msg}")
        return False
    with db() as (conn, cursor):
        query = ("INSERT INTO account (user_id, account_name, account_type, account_balance, currency, platform_name) "
                 "VALUES (%s,%s,%s,%s,%s,%s)")
        cursor.execute(query, (userid, name, type, balance, currency, platform_name))
        print(f"Account '{name}' added successfully for user {userid}")
        return True


def check_balance(balance):
    # Accept both int and float
    if not isinstance(balance, (int, float)):
        return False, "The balance must be a number"
    elif balance < 0 or balance > 10000000:
        return False, "The balance should be between 0 and 10,000,000"
    else:
        return float(balance), "Balance valid"


def checkaccountType(actype: str):
    accountType = ["savings",
                   "current",
                   "fixed deposit",
                   "recurring deposit",
                   "joint",
                   "student",
                   "basic/zero-balance",
                   "stocks",
                   "crypto"
                   ]
    if actype.lower() not in accountType:
        return False, f"Invalid account type. Must be one of: {', '.join(accountType)}"
    return actype.lower(), "Account type valid"


def delete_account(current_user_id: int, account_id: int, password: str) -> bool:
    """
    Delete an account after verifying:
    1. The account belongs to the current user
    2. The password is correct for the current user

    Args:
        current_user_id: The logged-in user (from session)
        account_id: The account to delete
        password: Current user's password

    Returns:
        bool: True if deleted successfully, False otherwise
    """

    with db(dictionary=True) as (conn, cursor):
        query = """
                SELECT user_id
                FROM account
                WHERE account_id = %s \
                """
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()

        if not row:
            print(f"No account found with ID {account_id}")
            return False

        account_owner_id = row[0]

        if account_owner_id != current_user_id:
            print(
                f" Security: User {current_user_id} tried to delete account {account_id} owned by user {account_owner_id}")
            return False

        # Step 2: Verify password for the CURRENT user (not the account owner)
        cursor.execute("SELECT password FROM users WHERE user_id = %s", (current_user_id,))
        row = cursor.fetchone()

        if not row:
            print(f"No user found with ID {current_user_id}")
            return False

        stored_pw = row[0]
        salt, real_hash_pw = stored_pw.split(":")
        password_hash = hashAgain(salt, password)

        if real_hash_pw != password_hash:
            print(f"Incorrect password for user {current_user_id}")
            return False

        # Step 3: Delete the account (now safe because we verified ownership)
        query = "DELETE FROM account WHERE account_id = %s AND user_id = %s"
        cursor.execute(query, (account_id, current_user_id))

        if cursor.rowcount == 0:
            print(f"Delete failed, account not found or access denied")
            return False

        print(f"Account {account_id} deleted successfully by user {current_user_id}")
        return True


def update_account(account_id, userid, name=None, accountType=None, balance=None, currency=None, platform_name=None):
    with db() as (conn, cursor):

        cursor.execute(
            "SELECT 1 FROM account WHERE account_id = %s AND user_id = %s",
            (account_id, userid)
        )
        if not cursor.fetchone():
            return False

        update = []
        values = []

        if name is not None:
            update.append("account_name = %s")
            values.append(name)

        if accountType is not None:
            is_valid, normalized_type = checkaccountType(accountType)
            if not is_valid:
                return False
            update.append("account_type = %s")
            values.append(normalized_type)

        if balance is not None:
            normalized_balance, balance_msg = check_balance(balance)
            if normalized_balance is False:
                return False
            update.append("account_balance = %s")
            values.append(normalized_balance)

        if currency is not None:
            update.append("currency = %s")
            values.append(currency)

        if platform_name is not None:
            update.append("platform_name = %s")
            values.append(platform_name)

        if not update:
            return False

        values.extend([account_id, userid])

        query = f"""
        UPDATE account
        SET {', '.join(update)}
        WHERE account_id = %s AND user_id = %s
        """

        cursor.execute(query, tuple(values))

        return cursor.rowcount > 0


def add_money(user_id, account_id, credits: int):
    """Add money to an account"""


    if not isinstance(credits, (int, float)):
        print("Amount must be a number")
        return False

    if credits < 0 or credits > 10000000:
        print("Amount must be between 0 and 10,000,000")
        return False

    with db() as (conn, cursor):
        query = "UPDATE account SET account_balance = account_balance + %s WHERE account_id = %s AND user_id = %s"
        cursor.execute(query, (credits, account_id, user_id))
        conn.commit()
        print(f"Added {credits} to account {account_id}")
        return True


def transfer_money(user_id, account_id1, account_id2, credits: int):

    with db() as (conn, cursor):
        query = "SELECT account_balance FROM account WHERE account_id = %s AND user_id = %s"
        cursor.execute(query, (account_id1, user_id))
        row = cursor.fetchone()

        if not row:
            print(f"Source account {account_id1} not found")
            return False

        balance = row[0]
        if balance < credits:
            print(f"Insufficient funds. Balance: {balance}, Required: {credits}")
            return False

        query1 = "UPDATE account SET account_balance = account_balance - %s WHERE account_id = %s AND user_id = %s"
        cursor.execute(query1, (credits, account_id1, user_id))

        query2 = "UPDATE account SET account_balance = account_balance + %s WHERE account_id = %s AND user_id = %s"
        cursor.execute(query2, (credits, account_id2, user_id))
        print(f"Transferred {credits} from account {account_id1} to {account_id2}")
        return True



def get_all_accounts(current_user_id: int):
    with db(dictionary=True) as (_, cursor):
        cursor.execute(
            "SELECT * FROM account WHERE user_id=%s",
            (current_user_id,)
        )
        rows = cursor.fetchall()
        if not rows:
            return []
        return rows


def get_account(account_id: int, current_user_id: int):
    """
    Get a single account by ID for editing
    Example: GET /accounts/5?user_id=1

    This endpoint is needed for the Update Account feature.
    It fetches one specific account so the edit modal can be pre-filled.
    """

    with db(dictionary=True) as (conn, cursor):
        cursor.execute("""
                           SELECT account_id,
                                  account_name,
                                  account_type,
                                  account_balance,
                                  currency,
                                  platform_name,
                                  created_at
                           FROM account
                           WHERE account_id = %s
                             AND user_id = %s
                           """, (account_id, current_user_id))

        account = cursor.fetchone()

        if not account:
            return None
        return account
