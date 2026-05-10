import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fintracker_base.databaseDAO.sqlConnector import get_connection, db


def weekly_expenses(user, weeks=12):
    """Fetch transactions for a user within the specified number of weeks"""
    with db() as (conn, cursor):
        query = """
            SELECT DATE (transaction_date) as date, amount
            FROM transactions
            WHERE user_id = %s
              AND transaction_date >= DATE_SUB(CURDATE() \
                , INTERVAL %s WEEK)
            ORDER BY transaction_date ASC \
            """
        cursor.execute(query, (user, weeks))
        result = cursor.fetchall()

    if not result:
        print("No transactions found for this user!")
        return None

    return result


def incoming_funds(amounts):
    """Calculate total income (positive amounts)"""
    total = 0
    for amount in amounts:
        if amount >= 0:
            total += amount
    return total


def outgoing_funds(amounts):
    """Calculate total expenses (negative amounts as positive values)"""
    total = 0
    for amount in amounts:
        if amount < 0:
            total += abs(amount)  # Convert to positive for display
    return total


def groupPlot_by_week(transactions):
    """Group transactions by week and create a line chart"""

    if not transactions:
        print("No transactions to plot!")
        return

    # Create DataFrame from transactions
    df = pd.DataFrame(transactions, columns=["Date", "Amount"])
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    # Resample by week (starting Monday) and aggregate
    weekly = df.resample('W-MON').agg({
        'Amount': [incoming_funds, outgoing_funds]
    })

    # Reset index first to get the Date column
    weekly = weekly.reset_index()

    # Then rename the aggregated columns
    weekly.columns = ['Date', 'Income', 'Expenses']

    # Create the plot with line chart
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(weekly))

    # Plot lines with markers
    ax.plot(x, weekly['Income'], marker='o', linewidth=2.5, markersize=8,
            label='Income', color='green', alpha=0.8)
    ax.plot(x, weekly['Expenses'], marker='s', linewidth=2.5, markersize=8,
            label='Expenses', color='red', alpha=0.8)


    # Add horizontal line at y=0
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)

    ax.set_xlabel('Week Starting', fontsize=12)
    ax.set_ylabel('Amount (kr)', fontsize=12)
    ax.set_title('Weekly Income vs Expenses Trend', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([date.strftime('%Y-%m-%d') for date in weekly['Date']],
                       rotation=45, ha='right')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_user_weekly_data(user_id, weeks=8):
    """Main function to fetch data and plot for a specific user"""
    print(f"Fetching data for user {user_id} over the last {weeks} weeks...")

    # Fetch transactions
    transactions = weekly_expenses(user_id, weeks)

    if transactions:
        print(f"Found {len(transactions)} transactions")
        # Plot the data
        groupPlot_by_week(transactions)
    else:
        print("No data to display")


# Usage - CORRECTED
if __name__ == "__main__":
    plot_user_weekly_data(user_id=43, weeks=5)