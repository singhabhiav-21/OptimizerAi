import os

from reportlab.lib.pagesizes import letter
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
from fintracker_base.databaseDAO.sqlConnector import get_connection, db
from contextlib import contextmanager
from reportlab.graphics.shapes import Line, String


def get_data(user_id, month):
    if not user_exists(user_id):
        print(f"User with ID {user_id} does not exist!")
        return None

    with db() as (conn, cursor):

        query = """
                SELECT transaction_date,
                       amount,
                       name,
                       description
                FROM transactions
                WHERE user_id = %s \
                  AND DATE_FORMAT(transaction_date, '%Y-%m') = %s
                ORDER BY transaction_date \
                """
        cursor.execute(query, (user_id, month))
        result = cursor.fetchall()

        if not result:
            print("The user has no data!(visual)")
            return None

        df = pd.DataFrame(result, columns=['transaction_date', 'amount', 'name', 'description'])

        # Convert transaction_date to datetime
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])

        # Convert Decimal to float to avoid pandas calculation errors
        df['amount'] = df['amount'].astype(float)

        # Create 'type' column based on amount sign
        # If amount is negative, it's an expense; if positive, it's income
        df['type'] = df['amount'].apply(lambda x: 'expense' if x < 0 else 'income')

        # Convert all amounts to positive for easier calculations
        df['amount'] = df['amount'].abs()

        return df


def user_exists(user_id):
    with db() as (conn, cursor):
        query = "SELECT 1 FROM users WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        return result is not None


def get_merchant_breakdown(df):
    """Get spending by merchant (top 7) - expenses only"""
    expenses_df = df[df['type'] == 'expense']
    if len(expenses_df) == 0:
        return None
    merchant_spending = expenses_df.groupby('name')['amount'].sum().sort_values(ascending=False).head(7)
    return merchant_spending


def get_weekly_breakdown(df):
    """Get spending by week"""
    df['week'] = df['transaction_date'].dt.isocalendar().week
    weekly_spending = df.groupby('week')['amount'].sum()
    return weekly_spending


def get_spending_insights(df):
    """Calculate various insights"""
    # Separate income and expenses
    expenses_df = df[df['type'] == 'expense']
    income_df = df[df['type'] == 'income']

    insights = {
        # Expense insights
        'total_expenses': expenses_df['amount'].sum() if len(expenses_df) > 0 else 0,
        'average_expense': expenses_df['amount'].mean() if len(expenses_df) > 0 else 0,
        'median_expense': expenses_df['amount'].median() if len(expenses_df) > 0 else 0,
        'expense_count': len(expenses_df),
        'min_expense': expenses_df['amount'].min() if len(expenses_df) > 0 else 0,
        'max_expense': expenses_df['amount'].max() if len(expenses_df) > 0 else 0,

        # Income insights
        'total_income': income_df['amount'].sum() if len(income_df) > 0 else 0,
        'average_income': income_df['amount'].mean() if len(income_df) > 0 else 0,
        'income_count': len(income_df),

        # Overall
        'total_count': len(df),
        'net_savings': (income_df['amount'].sum() if len(income_df) > 0 else 0) - (
            expenses_df['amount'].sum() if len(expenses_df) > 0 else 0),
        'days_with_spending': df['transaction_date'].nunique(),
        'avg_daily_expense': expenses_df.groupby('transaction_date')['amount'].sum().mean() if len(
            expenses_df) > 0 else 0
    }

    # Top 3 expense days
    if len(expenses_df) > 0:
        daily_expenses = expenses_df.groupby('transaction_date')['amount'].sum().sort_values(ascending=False)
        insights['top_3_expense_days'] = daily_expenses.head(3)
    else:
        insights['top_3_expense_days'] = pd.Series()

    # Largest expense transaction
    if len(expenses_df) > 0:
        largest_expense = expenses_df.loc[expenses_df['amount'].idxmax()]
        insights['largest_expense'] = {
            'date': largest_expense['transaction_date'],
            'amount': largest_expense['amount'],
            'name': largest_expense['name'],
            'description': largest_expense['description']
        }
    else:
        insights['largest_expense'] = None

    # Smallest expense transaction
    if len(expenses_df) > 0:
        smallest_expense = expenses_df.loc[expenses_df['amount'].idxmin()]
        insights['smallest_expense'] = {
            'date': smallest_expense['transaction_date'],
            'amount': smallest_expense['amount'],
            'name': smallest_expense['name']
        }
    else:
        insights['smallest_expense'] = None

    return insights


def prepared_for_chart(df):
    """Prepare separate income and expense data grouped by day"""
    # Separate income and expenses
    expenses_df = df[df['type'] == 'expense'].copy()
    income_df = df[df['type'] == 'income'].copy()

    # Group by date
    daily_expenses = expenses_df.groupby('transaction_date')['amount'].sum().reset_index()
    daily_income = income_df.groupby('transaction_date')['amount'].sum().reset_index()

    # Get all days in the month
    if len(df) > 0:
        first_date = df['transaction_date'].min()
        last_day = pd.Period(first_date, freq='M').days_in_month
        all_days = pd.date_range(start=first_date.replace(day=1),
                                 periods=last_day,
                                 freq='D')
    else:
        return {'expense_amounts': [], 'income_amounts': [], 'day_labels': [], 'dates': []}

    # Create data structure with all days
    expense_amounts = []
    income_amounts = []
    day_labels = []

    for day in all_days:
        expense_val = daily_expenses[daily_expenses['transaction_date'] == day]['amount'].sum()
        income_val = daily_income[daily_income['transaction_date'] == day]['amount'].sum()

        expense_amounts.append(float(expense_val) if expense_val > 0 else 0)
        income_amounts.append(float(income_val) if income_val > 0 else 0)
        day_labels.append(str(day.day))

    return {
        'expense_amounts': expense_amounts,
        'income_amounts': income_amounts,
        'day_labels': day_labels,
        'dates': all_days.tolist()
    }


def create_header_section(month, user_id, styles):
    """Create a professional header with report info"""
    elements = []

    # Title with better styling
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#1a202c'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#718096'),
        alignment=TA_CENTER,
        spaceAfter=15
    )

    elements.append(Paragraph(f"💰 Monthly Financial Report", title_style))

    # Parse month for better formatting
    year, month_num = month.split('-')
    month_name = datetime.strptime(month, '%Y-%m').strftime('%B %Y')

    elements.append(Paragraph(f"{month_name}", subtitle_style))
    elements.append(Paragraph(f"User ID: {user_id} | Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                              subtitle_style))

    # Add a separator line
    elements.append(Spacer(1, 15))

    return elements


def create_executive_summary(insights, styles):
    """Create an executive summary dashboard"""
    elements = []

    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )

    elements.append(Paragraph("📊 Executive Summary", header_style))

    # Create summary cards in a table
    summary_data = [
        ['Metric', 'Value'],
        ['Total Income', f"SEK {insights['total_income']:,.2f}"],
        ['Total Expenses', f"SEK {insights['total_expenses']:,.2f}"],
        ['Net Savings', f"SEK {insights['net_savings']:,.2f}"],
        ['Total Transactions',
         f"{insights['total_count']} ({insights['income_count']} income, {insights['expense_count']} expenses)"],
        ['Avg Expense/Transaction', f"SEK {insights['average_expense']:,.2f}"],
        ['Avg Expense per Day', f"SEK {insights['avg_daily_expense']:,.2f}"],
        ['Days with Activity', f"{insights['days_with_spending']} days"]
    ]

    table = Table(summary_data, colWidths=[220, 200])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4299e1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),

        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2d3748')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('PADDING', (0, 1), (-1, -1), 8),

        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
    ]))

    elements.append(table)
    elements.append(Spacer(1, 15))

    return elements


def create_enhanced_chart_section(chart_data, insights, styles):
    """Create separate income vs expense charts by day"""
    elements = []

    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )

    elements.append(Paragraph("Daily Income vs Expenses", header_style))
    elements.append(Spacer(1, 8))

    # Create a larger chart to use more space
    drawing = Drawing(500, 320)

    # Create line chart with proper boundaries
    lc = HorizontalLineChart()
    lc.x = 55
    lc.y = 50
    lc.height = 220
    lc.width = 420

    # Two lines: [0] = Expenses (red), [1] = Income (green)
    lc.data = [
        tuple(chart_data['expense_amounts']),
        tuple(chart_data['income_amounts'])
    ]
    lc.joinedLines = 1

    # Expense line styling (red)
    lc.lines[0].strokeColor = colors.HexColor('#f56565')
    lc.lines[0].strokeWidth = 2
    lc.lines[0].symbol = None
    lc.lines[0].name = 'Expenses'

    # Income line styling (green)
    lc.lines[1].strokeColor = colors.HexColor('#48bb78')
    lc.lines[1].strokeWidth = 2
    lc.lines[1].symbol = None
    lc.lines[1].name = 'Income'

    # Category axis (X-axis - days 1-30/31)
    lc.categoryAxis.categoryNames = chart_data['day_labels']
    lc.categoryAxis.labels.fontSize = 7
    lc.categoryAxis.labels.angle = 0
    lc.categoryAxis.strokeColor = colors.HexColor('#cbd5e0')
    lc.categoryAxis.strokeWidth = 1

    # Value axis (Y-axis - amounts)
    all_amounts = chart_data['expense_amounts'] + chart_data['income_amounts']
    max_amount = float(max(all_amounts)) if all_amounts and max(all_amounts) > 0 else 1000
    lc.valueAxis.valueMin = 0
    lc.valueAxis.valueMax = max_amount * 1.2  # Add 20% padding at top
    lc.valueAxis.valueStep = (max_amount * 1.2) / 5  # 5 grid lines
    lc.valueAxis.labels.fontSize = 8
    lc.valueAxis.strokeColor = colors.HexColor('#cbd5e0')
    lc.valueAxis.strokeWidth = 1
    lc.valueAxis.labelTextFormat = 'SEK %0.0f'

    # Add grid lines for better readability
    lc.valueAxis.visibleGrid = 1
    lc.valueAxis.gridStrokeColor = colors.HexColor('#e2e8f0')
    lc.valueAxis.gridStrokeWidth = 0.5

    drawing.add(lc)

    # Legend for Expenses (red line)
    legend_y = 290
    expense_line = Line(70, legend_y, 100, legend_y)
    expense_line.strokeColor = colors.HexColor('#f56565')
    expense_line.strokeWidth = 2.5
    drawing.add(expense_line)
    expense_label = String(105, legend_y - 3, '● Expenses', fontSize=9)
    expense_label.fillColor = colors.HexColor('#2d3748')
    drawing.add(expense_label)

    # Legend for Income (green line)
    income_line = Line(180, legend_y, 210, legend_y)
    income_line.strokeColor = colors.HexColor('#48bb78')
    income_line.strokeWidth = 2.5
    drawing.add(income_line)
    income_label = String(215, legend_y - 3, '● Income', fontSize=9)
    income_label.fillColor = colors.HexColor('#2d3748')
    drawing.add(income_label)

    elements.append(drawing)
    elements.append(Spacer(1, 15))

    return elements


def create_merchant_breakdown_section(df, styles):
    """Create merchant breakdown table only (no pie chart)"""
    merchant_data = get_merchant_breakdown(df)

    if merchant_data is None or len(merchant_data) == 0:
        return []

    elements = []

    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )

    elements.append(Paragraph("🏪 Top Merchants by Spending", header_style))
    elements.append(Spacer(1, 8))

    # Merchant table only
    table_data = [['Rank', 'Merchant', 'Amount', 'Percentage']]
    total = merchant_data.sum()

    for rank, (merchant, amount) in enumerate(merchant_data.items(), 1):
        percentage = (amount / total) * 100
        table_data.append([
            f"#{rank}",
            str(merchant)[:30],
            f"SEK {amount:,.2f}",
            f"{percentage:.1f}%"
        ])

    table = Table(table_data, colWidths=[40, 180, 100, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#48bb78')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('PADDING', (0, 1), (-1, -1), 7),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
    ]))

    elements.append(table)
    elements.append(Spacer(1, 15))

    return elements


def create_top_spending_section(insights, styles):
    """Show top spending days and largest transaction"""
    elements = []

    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=15,
        fontName='Helvetica-Bold'
    )

    elements.append(Paragraph("🔝 Top Expense Highlights", header_style))
    elements.append(Spacer(1, 10))

    # Top 3 expense days
    if len(insights['top_3_expense_days']) > 0:
        table_data = [['Rank', 'Date', 'Total Expenses']]
        for rank, (date, amount) in enumerate(insights['top_3_expense_days'].items(), 1):
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
            table_data.append([
                f"{emoji} #{rank}",
                str(date),
                f"SEK {amount:,.2f}"
            ])

        table = Table(table_data, colWidths=[70, 180, 150])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ed8936')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('PADDING', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fff5f0'), colors.white])
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    # Largest and Smallest expense transactions
    if insights['largest_expense'] and insights['smallest_expense']:
        elements.append(Paragraph("💳 Expense Transaction Extremes", styles['Heading3']))
        elements.append(Spacer(1, 8))

        lt = insights['largest_expense']
        st = insights['smallest_expense']

        extremes_data = [
            ['', '🔺 Largest', '🔻 Smallest'],
            ['Date', str(lt['date']), str(st['date'])],
            ['Merchant', str(lt['name'])[:20], str(st['name'])[:20]],
            ['Amount', f"SEK {lt['amount']:,.2f}", f"SEK {st['amount']:,.2f}"],
        ]

        extremes_table = Table(extremes_data, colWidths=[80, 160, 160])
        extremes_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4299e1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f7fafc')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
        ]))

        elements.append(extremes_table)

    elements.append(Spacer(1, 25))

    return elements


def create_transaction_list_section(df, summary, styles):
    """Enhanced transaction list"""
    elements = []

    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=15,
        fontName='Helvetica-Bold'
    )

    elements.append(PageBreak())
    elements.append(Paragraph("📝 Complete Transaction List", header_style))
    elements.append(Spacer(1, 12))

    table_data = [['Date', 'Merchant', 'Amount', 'Description']]

    for _, row in df.iterrows():
        table_data.append([
            str(row['transaction_date']),
            str(row['name'])[:25],
            f"SEK {row['amount']:,.2f}",
            str(row['description'])[:35] if row['description'] else 'N/A'
        ])

    table = Table(table_data, colWidths=[80, 130, 80, 170])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4299e1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('PADDING', (0, 1), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
    ]))

    elements.append(table)
    return elements


def make_report(user_id, month, output_filename=None):
    if output_filename is None:
        output_filename = f'financial_report_{month}.pdf'

    df = get_data(user_id, month)
    if df is None:
        return False

    # Calculate all insights
    insights = get_spending_insights(df)
    chart_data = prepared_for_chart(df)

    # Create PDF
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    elements = []
    styles = getSampleStyleSheet()

    # Build report sections
    elements.extend(create_header_section(month, user_id, styles))
    elements.extend(create_executive_summary(insights, styles))
    elements.extend(create_enhanced_chart_section(chart_data, insights, styles))
    elements.extend(create_merchant_breakdown_section(df, styles))
    elements.extend(create_top_spending_section(insights, styles))
    elements.extend(create_transaction_list_section(df, insights, styles))

    doc.build(elements)
    print(f" Report generated successfully: {output_filename}")
    return True


def get_reports_by_userid(current_user_id):
    with db(dictionary=True) as (conn, cursor):
        cursor.execute("""
                       SELECT report_id,
                              user_id,
                              report_month,
                              total_spending,
                              transaction_count,
                              generated_at
                       FROM reports
                       WHERE user_id = %s
                       ORDER BY report_month DESC, generated_at DESC
                       """, (current_user_id,))

        return cursor.fetchall()


def get_reports_service(current_user_id):

    reports = get_reports_by_userid(current_user_id)

    return {
        "success": True,
        "user_id": current_user_id,
        "reports": reports,
        "count": len(reports)
    }


def download_report_by_userid(month, current_user_id):
    with db() as (conn, cursor):
        cursor.execute("""
                       SELECT report_id
                       FROM reports
                       WHERE user_id = %s
                         AND report_month = %s
                       """, (current_user_id, month))

        result = cursor.fetchone()

        return result[0] if result else None


def download_report_service(month, current_user_id):
    report = download_report_by_userid(month, current_user_id)

    if not report:
        raise ValueError("Report not found in database")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    filename = f'financial_report_{current_user_id}_{month}.pdf'
    reports_dir = os.path.join(BASE_DIR, "reports")
    file_path = os.path.join(reports_dir, filename)

    if not os.path.exists(file_path):
        print(f"PDF missing, regenerating...")
        success = make_report(current_user_id, month, file_path)

        if not success or not os.path.exists(file_path):
            raise FileNotFoundError("Could not generate report file")

    return file_path, filename


def get_report_details(report_id, current_user_id):
    with db(dictionary=True) as (conn, cursor):
        cursor.execute("""
                       SELECT report_id,
                              user_id,
                              report_month,
                              total_spending,
                              transaction_count,
                              generated_at
                       FROM reports
                       WHERE report_id = %s
                         AND user_id = %s
                       """, (report_id, current_user_id))

        return cursor.fetchone()


def get_reports_details_service(report_id, current_user_id):
        report = get_report_details(report_id, current_user_id)
        if not report:
            raise ValueError("Report not found")

        return {
            "success": True,
            **report
        }


def generate_report_by_userid(current_user_id, month, total_spending, transaction_count):
    with db() as (conn, cursor):
        cursor.execute("""
                       INSERT INTO reports (user_id, report_month, total_spending, transaction_count)
                       VALUES (%s, %s, %s, %s) ON DUPLICATE KEY
                       UPDATE
                           total_spending =
                       VALUES (total_spending), transaction_count =
                       VALUES (transaction_count), generated_at = CURRENT_TIMESTAMP
                       """, (current_user_id, month, total_spending, transaction_count))

        conn.commit()

        if cursor.lastrowid:
            return cursor.lastrowid

        cursor.execute("""
                       SELECT report_id
                       FROM reports
                       WHERE user_id = %s
                         AND report_month = %s
                       """, (current_user_id, month))

        row = cursor.fetchone()
        return row[0] if row else None


def generate_monthly_report_service(user_id, month):
    df = get_data(user_id, month)
    if len(month) != 7 or month[4] != "-":
        raise ValueError("Invalid month format. Use YYYY-MM")

    total_spending = float(df["amount"].sum())
    transaction_count = len(df)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    reports_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"financial_report_{user_id}_{month}.pdf"
    output_path = os.path.join(reports_dir, filename)

    success = make_report(user_id, month, output_path)
    if not success:
        raise LookupError("No transaction data found or report generation failed")

    report_id = generate_report_by_userid(
        current_user_id=user_id,
        month=month,
        total_spending=total_spending,
        transaction_count=transaction_count
    )
    return {
        "report_id": report_id,
        "filename": filename,
        "total_spending": round(total_spending, 2),
        "transaction_count": transaction_count
    }


def get_report_month(report_id: int, user_id: int) -> str | None:
    with db(dictionary=True) as (conn, cursor):
        cursor.execute("""
            SELECT report_month
            FROM reports
            WHERE report_id = %s
              AND user_id = %s
        """, (report_id, user_id))

        row = cursor.fetchone()
        return row["report_month"] if row else None


def delete_report_by_id(report_id: int, user_id: int) -> int:
    with db() as (conn, cursor):
        cursor.execute("""
            DELETE FROM reports
            WHERE report_id = %s
              AND user_id = %s
        """, (report_id, user_id))

        return cursor.rowcount


def delete_report_service(report_id: int, user_id: int):
    month = get_report_month(report_id, user_id)
    if not month:
        raise ValueError("Report not found")

    deleted = delete_report_by_id(report_id, user_id)
    if deleted == 0:
        raise ValueError("Report not found")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    filename = f"financial_report_{user_id}_{month}.pdf"
    reports_dir = os.path.join(BASE_DIR, "reports")
    file_path = os.path.join(reports_dir, filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    return {
        "report_id": report_id,
        "filename": filename
    }