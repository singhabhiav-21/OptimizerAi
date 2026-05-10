from fintracker_base.databaseDAO.sqlConnector import get_connection
from mysql.connector import Error
import pandas as pd
import hashlib
from decimal import Decimal, InvalidOperation

from fintracker_base.databaseDAO.transaction.transaction_DAO import register_transaction, add_transaction_batch


class bankImporter:
    def __init__(self, user_id, default_category_id=1):
        self.user_id = user_id
        self.category_id = default_category_id

        # Initialize counters
        self.imported_count = 0
        self.duplicate_count = 0

    def _generate_hash(self, transaction):
        return hashlib.sha256(transaction.encode()).hexdigest()

    def _clean_amount(self, amount):
        if pd.isna(amount):
            raise ValueError("Amount is missing")
        amount_clean = str(amount).replace(',', '').strip()
        return amount_clean

    def import_csv(self, file_path: str):
        try:
            file = pd.read_csv(file_path, sep=None, engine='python', skipinitialspace=True, quotechar='"')

            file.columns = file.columns.str.strip().str.strip('"\'')

            print(f"DEBUG: All CSV columns detected: {list(file.columns)}")
            print(f"DEBUG: Total rows read by pandas: {len(file)}")

            # Show first few rows for debugging
            if len(file) > 0:
                print(f"DEBUG: First row data:")
                print(file.head(1).to_dict('records'))

            # Check for required columns (but allow extra columns)
            required_columns = ['Value date', 'Text', 'Amount']
            missing_columns = []

            for col in required_columns:
                if col not in file.columns:
                    missing_columns.append(col)

            if missing_columns:
                print(f"Error: Missing required columns: {missing_columns}")
                print(f"Available columns: {list(file.columns)}")
                print(f"Expected columns: {required_columns}")
                return None

            print(f"DEBUG: All required columns found! Extra columns will be ignored.")

            # Check for NA values in required columns before dropping
            print(f"DEBUG: NA counts in required columns:")
            for col in required_columns:
                na_count = file[col].isna().sum()
                print(f"  {col}: {na_count} NA values")

            initial_count = len(file)
            file = file.dropna(subset=required_columns)
            dropped_count = initial_count - len(file)

            if dropped_count > 0:
                print(f"DEBUG: Dropped {dropped_count} rows with missing data in required columns")

            print(f"Processing {len(file)} transactions...")

            # Reset counters
            self.imported_count = 0
            self.duplicate_count = 0

            batch = []
            batch_count = 100
            errors = []

            for index, (idx, row) in enumerate(file.iterrows(), start=1):
                try:
                    if pd.isna(row['Text']) or str(row['Text']).strip() == "":
                        errors.append(f"Row {index}: Skipping - missing description")
                        continue
                    description = " ".join(str(row['Text']).lower().split())

                    # Parse amount
                    if pd.isna(row['Amount']):
                        errors.append(f"Row {index}: Skipping - missing amount")
                        continue
                    amount_clean = self._clean_amount(row['Amount'])
                    try:
                        amount = Decimal(str(amount_clean)).quantize(Decimal("0.01"))
                    except (InvalidOperation, ValueError) as e:
                        errors.append(f"Row {index}: Invalid amount - {e}")
                        continue

                    # Parse date
                    if pd.isna(row['Value date']):
                        errors.append(f"Row {index}: Missing date")
                        continue

                    try:
                        transaction_date = pd.to_datetime(row['Value date'], errors="raise").strftime("%Y-%m-%d")
                    except Exception as e:
                        errors.append(f"Row {index}: Invalid date - {e}")
                        continue

                    # Parse balance (optional)
                    try:
                        balance = self._clean_amount(row['Balance']) if 'Balance' in row and not pd.isna(
                            row['Balance']) else 0.0
                    except:
                        balance = 0.0

                    hash_key = f"{self.user_id}|{description}|{amount:.2f}|{transaction_date}"
                    transaction_hash = self._generate_hash(hash_key)

                    if self.imported_count < 5:  # Only show first 5 for testing
                        print(f"\n--- Row {index} ---")
                        print(f"Hash key: {hash_key}")
                        print(f"Hash: {transaction_hash}")

                    batch.append((
                        self.user_id,
                        self.category_id,
                        description[:25],
                        amount,
                        description[:225],
                        transaction_date,
                        balance,
                        transaction_hash,
                    ))

                    if len(batch) >= batch_count:
                        rows_inserted = add_transaction_batch(batch)
                        self.imported_count += rows_inserted

                        duplicates_in_batch = len(batch) - rows_inserted
                        self.duplicate_count += duplicates_in_batch

                        print(f"Processed {self.imported_count + self.duplicate_count}: "
                              f"{rows_inserted} new, {duplicates_in_batch} skipped")
                        batch.clear()
                except Exception as e:
                    errors.append(f"Row {index}: {str(e)}")
                    continue

            if batch:
                rows_inserted = add_transaction_batch(batch)
                duplicates_in_batch = len(batch) - rows_inserted

                self.imported_count += rows_inserted
                self.duplicate_count += duplicates_in_batch

                print(f"Final batch: {rows_inserted} new, {duplicates_in_batch} skipped")

            print(f"\nImport Complete:")
            print(f"  Imported: {self.imported_count} transactions")
            print(f"  Duplicates skipped: {self.duplicate_count}")
            return True

        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            return False

        except Exception as e:
            print(f"Error: {e}")
            raise
