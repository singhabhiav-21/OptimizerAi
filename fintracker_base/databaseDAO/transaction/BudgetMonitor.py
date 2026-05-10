from financial_Tracker.databaseDAO.sqlConnector import get_connection
import pandas as pd


conn = get_connection()
cursor = conn.cursor()


#def set_budget(user_id, category_id, amount, month, year, repeat: bool):
    #query = """
    #INSERT INTO budget(user_id, category_id, amount, month, year) VALUES (%s,%s,%s,%s,%s)
    """
    if amount <= 0:
        print("the amount cannot be less than or equal to 0")
        return False
    if month > 12 and month < 1:
        print("The month cannot be less than 1 or greater than 12")
        return False
    cursor.execute(query, (user_id, category_id, amount, month, year))
    if repeat:
        repeat_budget(user_id, category_id, amount)
    else:
        pass
    return True


def repeat_budget(user_id, category_id, amount, start_m, start_y, duration):
    month = start_m
    year = start_y

    if duration < 0:
        print("The duration cannot be less than 0.")
        return False

    for _ in range(duration):
        cursor.execute("""
        #INSERT INTO budget(user_id, category_id, amount, month, year)
        #VALUES (?,?,?,?,?)
        """, (user_id, category_id, amount, month, year))

        month += 1
        if month > 12:
            month += 1
            year += 1
    return True"""



