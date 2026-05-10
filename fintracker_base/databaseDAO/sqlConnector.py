import os
from contextlib import contextmanager

from dotenv import load_dotenv
from mysql.connector.pooling import MySQLConnectionPool


load_dotenv()


pool = MySQLConnectionPool(
    pool_name="mypool",
    pool_size=1,
    pool_reset_session=True,
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', '3306')),
    user=os.getenv('DB_USER', os.environ.get("MYSQL_USER")),
    password=os.getenv('DB_PASSWORD', os.environ.get("MYSQL_PASSWORD")),
    database=os.getenv('DB_NAME', os.environ.get("MYSQL_DB")),
)

def get_connection():
    return pool.get_connection()

@contextmanager
def db(dictionary=False):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=dictionary)
        yield conn, cursor
        conn.commit()
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()  # returns to pool
            except Exception:
                pass

