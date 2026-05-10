from financial_Tracker.databaseDAO.transaction.importcsv import bankImporter


def test_import():
    # Use a test user_id
    user_id = 57 # Change this to your test user ID

    # Create importer instance
    importer = bankImporter(user_id=user_id, default_category_id=1)

    # Path to your CSV file
    csv_path = "/Users/abhinavsingh/Money_tracker/financial_Tracker/databaseDAO/test/minkontoutdrag"

    # Run import
    print(f"Starting import for user {user_id}...")
    importer.import_csv(csv_path)



if __name__ == "__main__":
    test_import()