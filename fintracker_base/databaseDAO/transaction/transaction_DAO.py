from fintracker_base.databaseDAO.sqlConnector import get_connection, db


def register_transaction(user_id, category_id, name, amount, description, transaction_date=None, balance=None, transaction_hash = None):
    query = "INSERT INTO transactions (user_id, category_id, name, amount, description, transaction_date,balance,transaction_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    with db() as (conn, cursor):
        cursor.execute(query, (user_id, category_id, name, amount, description, transaction_date,balance, transaction_hash))
    print("transaction registered!")
    return True


def delete_transaction(transaction_id, user_id):

    query = "DELETE FROM transactions WHERE transaction_id = %s AND user_id = %s"
    with db() as (conn, cursor):
        cursor.execute(query, (transaction_id, user_id,))
    return True


def update_transaction(transaction_id, user_id, category_id=None, name=None, amount=None, description=None):

    updates = []
    values = []

    if category_id is not None:
        updates.append("category_id = %s")
        values.append(category_id)
    if name is not None:
        updates.append("name = %s")
        values.append(name)
    if amount is not None:
        if not isinstance(amount, (int, float)):
            print("Invalid amount.")
            return False
        updates.append("amount = %s")
        values.append(amount)
    if description is not None:
        updates.append("description = %s")
        values.append(description)

    if not updates:
        print("No changes were provided!")
        return False

    query = f"UPDATE transactions SET {', '.join(updates)} WHERE transaction_id = %s AND user_id = %s"
    values.extend([transaction_id, user_id])

    with db() as (conn, cursor):
        cursor.execute(query, tuple(values))
    return True


def get_all_transactions(user_id):
    query = "SELECT * FROM transactions WHERE user_id = %s"
    with db(dictionary=True) as (conn, cursor):
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        if not rows:
            return []
        return rows


def get_transaction(transaction_id, user_id):
    query = "SELECT name, amount, description, created_at FROM transactions WHERE transaction_id = %s AND user_id = %s"

    with db() as (conn, cursor):
        cursor.execute(query, (transaction_id, user_id))
        row = cursor.fetchone()
        if not row:
            return False
    return row


def add_transaction_batch(batch):
    if not batch:
        return 0

    query = """
    INSERT IGNORE INTO transactions 
        (user_id, category_id, name, amount, description, transaction_date,balance,transaction_hash) 
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """

    with db() as (conn, cursor):
        cursor.executemany(query, batch)
        rows_affected = cursor.rowcount
    return rows_affected
