from fintracker_base.databaseDAO.sqlConnector import get_connection
import pandas as pd
import numpy as np

conn = get_connection()
cursor = conn.cursor


def get_weekly_categories(user, weeks=12):
    query = """
        SELECT
            DATE(t.transaction_date) as date, 
            t.amount,
            c.name
        FROM transactions 
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s 
        AND t.transaction_date >= DATE_SUB(CURDATE(), INTERVAL %s WEEK)
        ORDER BY t.transaction_date ASC
        """
    cursor.execure(query,user)
    result = cursor.fetchall
    if not result:
        print("The user is not registered!")
    return result
