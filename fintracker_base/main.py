from starlette.middleware.sessions import SessionMiddleware
import secrets
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime, timedelta
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import date
import tempfile
import os
from pathlib import Path
import traceback
import re
from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool

# DAO imports
from fintracker_base.databaseDAO.userDAO import logIn, register, update_userinfo, update_password
from fintracker_base.databaseDAO.Account.account_dao import (
    addAccount, delete_account, update_account,
    add_money, transfer_money, get_all_accounts, get_account
)
from fintracker_base.databaseDAO.transaction.transaction_DAO import (
    register_transaction, delete_transaction, update_transaction,
    get_transaction, get_all_transactions
)
from fintracker_base.databaseDAO.transaction.importcsv import bankImporter
from backend.router import router as ai_router

# Currency imports
from fintracker_base.Visuals.ExchangeRates import get_currency_converter
from fintracker_base.databaseDAO.sqlConnector import get_connection
from fintracker_base.Visuals.BarChart import weekly_expenses, incoming_funds, outgoing_funds
import pandas as pd

from fintracker_base.Visuals.Monthly_Report import make_report, get_data, get_reports_service, download_report_service, \
    generate_monthly_report_service, delete_report_service

app = FastAPI()
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not found in environment variables!")

# ==================== MIDDLEWARE  ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  #
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Session second (executes first)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=86400,
    session_cookie="user_session",
    same_site="lax",
    https_only=True,
)
app.include_router(ai_router)
# 3. Debug middleware LAST (executes FIRST, so you see raw requests)
@app.middleware("http")
async def debug_session_middleware(request: Request, call_next):
    print(f"\n{'=' * 60}")
    print(f"📥 REQUEST: {request.method} {request.url.path}")
    print(f"🍪 Incoming Cookies: {request.cookies}")

    response = await call_next(request)

    print(f"📤 RESPONSE: {response.status_code}")
    print(f"🍪 Set-Cookie: {response.headers.get('set-cookie', 'NONE')}")
    print(f"{'=' * 60}\n")

    return response
# ==================== STATIC FILES ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "static")),
    name="static"
)

def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    return user_id


# ==================== PAGE ROUTES ====================
@app.get("/")
async def index_page():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "templates", "index.html"))



@app.get("/dashboard")
async def dashboard_page(request: Request):
    user_id = request.session.get("user_id")

    print(f"🔐 Dashboard access attempt - user_id: {user_id}")

    if not user_id:
        print("❌ No session, redirecting to login")
        return RedirectResponse(url="/", status_code=302)

    print(f"✅ Serving dashboard for user {user_id}")
    return FileResponse(
        os.path.join(BASE_DIR, "frontend", "templates", "dashboard.html")
    )

@app.get("/accounts.html")
async def accounts_page():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "templates", "account.html"))


@app.get("/transactions.html")
async def transactions_page():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "templates", "transaction.html"))


@app.get("/import.html")
async def import_page():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "templates", "csv.html"))


@app.get("/reports.html")
async def reports_page():
    """Serve the reports page"""
    return FileResponse(os.path.join(BASE_DIR, "frontend", "templates", "reports.html"))


# ==================== USER MODELS ====================
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class UpdateUserRequest(BaseModel):
    email: str
    name: Optional[str] = None
    new_email: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    email: str
    old_password: str
    password: str
    re_password: str


# ==================== ACCOUNT MODELS ====================
class AccountCreate(BaseModel):
    name: str
    type: str
    balance: float
    currency: str = "USD"
    platform_name: Optional[str] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    accountType: Optional[str] = None
    balance: Optional[float] = None
    currency: Optional[str] = None
    platform_name: Optional[str] = None


class AccountDelete(BaseModel):
    password: str


class AddMoney(BaseModel):
    amount: float


class MoneyTransfer(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float


# ==================== TRANSACTION MODELS ====================
class TransactionCreate(BaseModel):
    category_id: int
    name: str
    amount: float
    description: Optional[str] = None
    transaction_date: Optional[date] = None
    balance: Optional[float] = None


class TransactionUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None


# ================= REPORT MODEL ===========================
class ReportGenerateRequest(BaseModel):
    month: str  # Format: YYYY-MM


class ReportDeleteRequest(BaseModel):
    user_id: int


# ==================== AUTH ENDPOINTS ====================
@app.get("/auth/status")
async def auth_status(request: Request):
    user_id = request.session.get("user_id")

    print(f"🔍 Session contents: {dict(request.session)}")
    print(f"🔍 user_id: {repr(user_id)}")

    is_authenticated = user_id is not None

    # ✅ Return 401 if not authenticated
    if not is_authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "authenticated": True,
        "user_id": user_id
    }
@app.post("/login")
async def login_endpoint(request: Request, response: Response, data: LoginRequest):
    success, user_id = logIn(data.email, data.password, )
    if not success:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Clear and update session properly
    request.session.clear()
    request.session.update({  # ← Use .update() instead of direct assignment
        "user_id": user_id,
        "email": data.email
    })

    request.session.update(request.session)  # Triggers save

    print(f"✅ Session created for user {user_id}: {request.session}")
    # ← ADD THIS: Check if session cookie is in response
    print(f"✅ Response cookies: {response.headers}")

    return {
        "success": True,
        "user_id": user_id,
        "message": "Login successful"
    }


@app.get("/me")
async def get_me(request: Request, current_user:int =Depends(get_current_user)):
    return  {
        "user_id": current_user,
        "email": request.session.get("email")
    }


@app.post("/register")
async def register_endpoint(
        data: RegisterRequest,

):
    success, message = register(data.name, data.email, data.password)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@app.put("/update-user")
async def update_user_endpoint(
        request: Request,
        data: UpdateUserRequest, current_user_id: int = Depends(get_current_user)):
    user_email = request.session.get("email")

    result = update_userinfo(user_email, data.name, data.new_email)

    if not result:
        raise HTTPException(status_code=400, detail="Update failed")

    return {"success": True, "message": "User information updated"}


@app.put("/update-password")
async def update_password_endpoint(
        data: UpdatePasswordRequest,
):
    result = update_password(
        data.email, data.old_password, data.password, data.re_password
    )

    if not result:
        raise HTTPException(status_code=400, detail="Password update failed")

    return {"success": True, "message": "Password updated successfully"}


@app.post("/logout")
async def logout_endpoint(request: Request, response: Response):
    """Logout and clear session"""
    request.session.clear()
    response.delete_cookie(
        key="user_session",
        path="/",
    )
    return {"success": True, "message": "Logged out successfully"}


# ==================== ACCOUNT ENDPOINTS ====================
@app.post("/accounts")
async def create_account(data: AccountCreate, current_user_id: int = Depends(get_current_user)):
    ok = await run_in_threadpool(
        addAccount,
        current_user_id,
        data.name,
        data.type,
        data.balance,
        data.currency,
        data.platform_name
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Account creation failed")
    return {"success": True}


@app.get("/accounts")
async def get_accounts(current_user_id: int = Depends(get_current_user)):
    return await run_in_threadpool(get_all_accounts, current_user_id)


@app.get("/accounts/{account_id}")
async def get_account_by_id(account_id: int, current_user_id: int = Depends(get_current_user)):
    account = await run_in_threadpool(get_account, account_id, current_user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or access denied")
    return account


@app.put("/accounts/{account_id}")
async def update_account_endpoint(
    account_id: int,
    data: AccountUpdate,
    current_user_id: int = Depends(get_current_user)
):
    ok = await run_in_threadpool(
        update_account,
        account_id,
        current_user_id,
        data.name,
        data.accountType,
        data.balance,
        data.currency,
        data.platform_name
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Update failed")
    return {"success": True}


@app.delete("/accounts/{account_id}")
async def delete_account_endpoint(
    account_id: int,
    data: AccountDelete,
    current_user_id: int = Depends(get_current_user)
):
    ok = await run_in_threadpool(
        delete_account,
        current_user_id,
        account_id,
        data.password
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Delete failed")
    return {"success": True, "message": "Account deleted successfully"}

#Not been implemented yet!
"""@app.post("/accounts/{account_id}/add-money")
async def add_money_endpoint(
    account_id: int,
    data: AddMoney,
    current_user_id: int = Depends(get_current_user)
):
    if not add_money(current_user_id, account_id, int(data.amount)):
        raise HTTPException(status_code=400, detail="Add money failed")
    return {"success": True}


@app.post("/accounts/transfer")
async def transfer_money_endpoint(
    data: MoneyTransfer,
    current_user_id: int = Depends(get_current_user)
):
    if not transfer_money(
        current_user_id,
        data.from_account_id,
        data.to_account_id,
        int(data.amount)
    ):
        raise HTTPException(status_code=400, detail="Transfer failed")
    return {"success": True}"""


# ==================== TRANSACTION ENDPOINTS ====================
@app.post("/transactions")
async def create_transaction(data: TransactionCreate, current_user_id: int = Depends(get_current_user)):
    ok = await run_in_threadpool(
        register_transaction,
        current_user_id,
        data.category_id,
        data.name,
        data.amount,
        data.description,
        data.transaction_date,
        data.balance
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Transaction failed")
    return {"success": True}


@app.get("/transactions")
async def get_transactions(current_user_id: int = Depends(get_current_user)):
    return await run_in_threadpool(get_all_transactions, current_user_id)


@app.get("/transactions/{transaction_id}")
async def get_transaction_endpoint(transaction_id: int, current_user_id: int = Depends(get_current_user)):
    tx = await run_in_threadpool(get_transaction, transaction_id, current_user_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@app.put("/transactions/{transaction_id}")
async def update_transaction_endpoint(
    transaction_id: int,
    data: TransactionUpdate,
    current_user_id: int = Depends(get_current_user)
):
    ok = await run_in_threadpool(
        update_transaction,
        transaction_id,
        current_user_id,
        data.category_id,
        data.name,
        data.amount,
        data.description
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Update failed")
    return {"success": True}


@app.delete("/transactions/{transaction_id}")
async def delete_transaction_endpoint(transaction_id: int, current_user_id: int = Depends(get_current_user)):
    ok = await run_in_threadpool(delete_transaction, transaction_id, current_user_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Delete failed")
    return {"success": True}


@app.get("/api/weekly-chart")
async def get_weekly_chart_data(current_user_id: int = Depends(get_current_user), weeks: int = 8, base_currency: str = "USD"):
    """
    Get weekly income/expense data using BarChart.py logic
    Processes data exactly like your Python visualization
    Example: GET /api/weekly-chart/43?weeks=8&base_currency=USD
    """
    try:
        transactions = weekly_expenses(current_user_id, weeks)

        if not transactions:
            return {
                'success': False,
                'error': 'No transactions found for this user',
                'user_id': current_user_id,
                'weeks': weeks
            }

        df = pd.DataFrame(transactions, columns=["Date", "Amount"])
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)

        weekly = df.resample('W-MON').agg({
            'Amount': [incoming_funds, outgoing_funds]
        })

        weekly = weekly.reset_index()

        weekly.columns = ['Date', 'Income', 'Expenses']

        weekly['Net'] = weekly['Income'] - weekly['Expenses']

        converter = get_currency_converter()
        needs_conversion = base_currency != 'SEK'

        # Convert to list of dicts for JSON response
        weekly_data = []
        for _, row in weekly.iterrows():
            income = float(row['Income'])
            expenses = float(row['Expenses'])
            net = float(row['Net'])

            # Convert from SEK to base_currency if needed
            if needs_conversion:
                income = converter.convert(income, 'SEK', base_currency)
                expenses = converter.convert(expenses, 'SEK', base_currency)
                net = converter.convert(net, 'SEK', base_currency)

            # FIXED: Use 'date' instead of 'week_start' to match frontend
            # Format date properly as ISO string
            weekly_data.append({
                'date': row['Date'].strftime('%Y-%m-%d'),  # Changed from 'week_start'
                'income': round(income, 2),
                'expenses': round(expenses, 2),
                'net': round(net, 2)
            })

        total_income = sum(w['income'] for w in weekly_data)
        total_expenses = sum(w['expenses'] for w in weekly_data)
        total_net = total_income - total_expenses

        if weekly_data:
            start_date = weekly_data[0]['date']
            end_date = weekly_data[-1]['date']
        else:
            start_date = end_date = None

        return {
            'success': True,
            'user_id': current_user_id,
            'weeks': weeks,
            'base_currency': base_currency,
            'source_currency': 'SEK',
            'conversion_applied': needs_conversion,
            'weekly_data': weekly_data,
            'summary': {
                'total_income': round(total_income, 2),
                'total_expenses': round(total_expenses, 2),
                'total_net': round(total_net, 2),
                'average_weekly_income': round(total_income / len(weekly_data), 2) if weekly_data else 0,
                'average_weekly_expenses': round(total_expenses / len(weekly_data), 2) if weekly_data else 0
            },
            'total_weeks': len(weekly_data),
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        }

    except Exception as e:
        print(f"❌ Error in weekly chart: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CURRENCY ENDPOINTS (NEW!) ====================
@app.get("/api/currency/dashboard")
async def get_dashboard_converted(current_user_id: int = Depends(get_current_user), base_currency: str = "USD"):
    """
    Get dashboard with all accounts converted to base currency
    Example: GET /api/currency/dashboard?base_currency=USD
    """
    accounts = get_all_accounts(current_user_id)

    transactions = get_all_transactions(current_user_id)

    converter = get_currency_converter()

    conversion_result = converter.convert_accounts(accounts, base_currency)

    if not conversion_result['success']:
        raise HTTPException(status_code=500, detail=conversion_result.get('error'))

    total_income = sum(float(t['amount']) for t in transactions if float(t['amount']) > 0)
    total_expenses = sum(abs(float(t['amount'])) for t in transactions if float(t['amount']) < 0)

    recent_transactions = transactions[:5]

    return {
            'success': True,
            'user_id': current_user_id,
            'base_currency': base_currency,
            'statistics': {
                'total_balance': conversion_result['total_balance'],
                'total_income': round(total_income, 2),
                'total_expenses': round(total_expenses, 2),
                'account_count': len(accounts)
            },
            'accounts': conversion_result['accounts'],
            'recent_transactions': recent_transactions,
            'timestamp': conversion_result['timestamp']
        }


@app.get("/api/currency/accounts/converted")
async def get_accounts_converted(current_user_id: int = Depends(get_current_user), base_currency: str = "USD"):
    """
    Get accounts with currency conversion
    Example: GET /api/currency/accounts/1/converted?base_currency=EUR
    """
    accounts = get_all_accounts(current_user_id)

    converter = get_currency_converter()
    result = converter.convert_accounts(accounts, base_currency)
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error'))

    return result


@app.get("/api/currency/rates")
async def get_exchange_rates(base_currency: str = "USD"):
    """
    Get current exchange rates
    Example: GET /api/currency/rates?base_currency=USD
    """
    try:
        converter = get_currency_converter()
        rates = converter.get_rates(base_currency)

        if not rates:
            raise HTTPException(status_code=500, detail="Could not fetch rates")

        return {
            'success': True,
            'base_currency': base_currency,
            'rates': rates,
            'count': len(rates)
        }

    except Exception as e:
        print(f"❌ Rates error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CSV IMPORT ENDPOINT ====================
# Security constants for file upload
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'.csv'}
ALLOWED_MIME_TYPES = {'text/csv', 'application/vnd.ms-excel', 'text/plain', 'application/csv'}


def validate_file_security(file: UploadFile) -> tuple[bool, str]:
    """
    Validates file for security issues
    Returns: (is_valid, error_message)
    """
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, "Invalid file type. Only CSV files allowed."

    # Check MIME type (some browsers don't send MIME type, so allow empty)
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        return False, f"Invalid MIME type: {file.content_type}"

    # Check filename for suspicious patterns
    suspicious_chars = ['..', '\0', '<', '>', ':', '"', '|', '?', '*']
    if any(char in file.filename for char in suspicious_chars):
        return False, "Invalid filename format"

    # Check filename length
    if len(file.filename) > 255:
        return False, "Filename too long"

    return True, ""


def normalize_column_name(col: str) -> str:
    """Normalize column name for flexible matching"""
    return re.sub(r'[\s_-]', '', col.lower().strip())


def validate_csv_columns(header_line: str) -> tuple[bool, str]:
    """
    Validate CSV has required columns with flexible matching
    Returns: (is_valid, error_message)
    """
    # Split by common delimiters and normalize
    header_cols = re.split(r'[,;\t]', header_line.lower())
    normalized_cols = [normalize_column_name(col.strip('"\'')) for col in header_cols]

    print(f"DEBUG: Header line: {header_line[:200]}")
    print(f"DEBUG: Parsed columns: {header_cols[:10]}")
    print(f"DEBUG: Normalized columns: {normalized_cols[:10]}")

    # Required columns (normalized)
    required = ['valuedate', 'text', 'amount']

    # Check each required column
    missing = []
    for req in required:
        found = any(req in norm or norm in req for norm in normalized_cols)
        if not found:
            missing.append(req)

    if missing:
        return False, f"Missing required columns: {', '.join(missing)}. Found: {', '.join(header_cols[:5])}"

    return True, ""


@app.post("/import-csv")
async def import_csv_transactions(
        file: UploadFile = File(...),
        current_user_id=Depends(get_current_user)
):
    """
    Endpoint to import transactions from CSV file
    Security features:
    - File type validation
    - File size limits
    - Temporary file handling
    - Automatic cleanup
    """
    print(f"\n{'=' * 60}")
    print(f"CSV IMPORT REQUEST")
    print(f"User ID: {current_user_id}")
    print(f"Filename: {file.filename}")
    print(f"Content Type: {file.content_type}")
    print(f"{'=' * 60}\n")


    # Security validation
    is_valid, error_msg = validate_file_security(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    temp_file_path = None

    try:
        # Read file content
        content = await file.read()

        print(f"File size: {len(content)} bytes")

        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024):.1f} MB"
            )

        # Check for empty file
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Additional security: Check for null bytes
        if b'\x00' in content:
            raise HTTPException(status_code=400, detail="File contains invalid characters")

        # Decode and validate CSV structure
        try:
            text_content = content.decode('utf-8-sig')  # Handle BOM
            print("Successfully decoded as UTF-8")
        except UnicodeDecodeError:
            try:
                text_content = content.decode('latin-1')  # Fallback encoding
                print("Successfully decoded as Latin-1")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Unable to decode file. Please ensure it's a valid CSV."
                )

        # Validate CSV has content
        lines = [line for line in text_content.split('\n') if line.strip()]

        if len(lines) < 2:
            raise HTTPException(status_code=400, detail="CSV file is too short or empty")

        print(f"Total lines in CSV: {len(lines)}")
        print(f"First line (header): {lines[0][:200]}")
        if len(lines) > 1:
            print(f"Second line (first data row): {lines[1][:200]}")

        # Fix quoted lines issue - if lines are wrapped in quotes, remove them
        fixed_lines = []
        for i, line in enumerate(lines):
            # Check if entire line is wrapped in quotes
            if line.startswith('"') and line.endswith('"') and line.count('"') == 2:
                fixed_line = line[1:-1]  # Remove first and last character (the quotes)
                if i == 0:
                    print(f"Detected quoted header line, removing outer quotes...")
                    print(f"Fixed header: {fixed_line}")
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)

        text_content = '\n'.join(fixed_lines)

        # Validate CSV columns with flexible matching
        is_valid, error_msg = validate_csv_columns(fixed_lines[0])
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        print("CSV column validation passed!")

        # Create secure temporary file
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.csv',
                delete=False,
                encoding='utf-8'
        ) as temp_file:
            temp_file.write(text_content)
            temp_file_path = temp_file.name

        print(f"Temporary file created: {temp_file_path}")

        # Process the file using bankImporter
        print(f"\nStarting import process for user {current_user_id}...")
        importer = bankImporter(user_id=current_user_id, default_category_id=1)

        # Call import_csv
        result = importer.import_csv(temp_file_path)

        print(f"\nImport process completed!")
        print(f"Imported: {importer.imported_count}")
        print(f"Duplicates: {importer.duplicate_count}")

        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"Temporary file deleted: {temp_file_path}")

        # Return results
        response_data = {
            "message": "Import completed successfully",
            "imported": importer.imported_count,
            "duplicates": importer.duplicate_count,
            "total": importer.imported_count + importer.duplicate_count,
            "user_id": current_user_id
        }

        print(f"\nReturning response: {response_data}\n")

        return JSONResponse(
            status_code=200,
            content=response_data
        )

    except HTTPException:
        # Clean up temp file on HTTP exceptions
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass
        raise

    except Exception as e:
        # Clean up temp file on any other exception
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass
        print(f"\nERROR processing CSV import: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

    finally:
        # Ensure file is closed
        await file.close()


# ==================== REPORT ENDPOINTS ====================

@app.get("/api/reports")
async def get_reports(current_user_id=Depends(get_current_user)):
    return await run_in_threadpool(get_reports_service, current_user_id)


@app.get("/api/reports/download")
async def download_report(month: str, current_user_id: int = Depends(get_current_user)):
    try:
        # Get file path from service (blocking operation)
        file_path, filename = await run_in_threadpool(
            download_report_service,
            month,
            current_user_id
        )

        # Return file (this is API-layer responsibility)
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/pdf'
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{report_id}")
async def get_report_details(report_id: int, current_user_id: int = Depends(get_current_user)):
    try:
        return await run_in_threadpool(
            get_report_details,
            report_id,
            current_user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error fetching report details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/generate")
async def generate_report(data: ReportGenerateRequest, current_user_id: int = Depends(get_current_user)):
    try:
        result = await run_in_threadpool(generate_monthly_report_service, user_id=current_user_id, month=data.month)
        return {
            "success": True,
            "message": f"Report generated successfully for {data.month}",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: int, current_user_id: int = Depends(get_current_user)):
    try:
            result = await run_in_threadpool(delete_report_service, report_id, current_user_id)

            return {
                "success": True,
                "message": "Report deleted successfully",
                **result
            }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/ai")
async def ai_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)
    return FileResponse(os.path.join(BASE_DIR, "frontend", "templates", "fin_ai.html"))
