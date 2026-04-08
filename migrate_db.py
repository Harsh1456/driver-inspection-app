from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        print("Running comprehensive migration for inspection_edits...")
        
        # List of columns to check/add
        columns = [
            ("page_number", "INTEGER DEFAULT 1"),
            ("signature_data", "TEXT"),
            ("signature_type", "VARCHAR(20)"),
            ("signer_name", "VARCHAR(255)"),
            ("signer_role", "VARCHAR(200)"),
            ("signature_date", "VARCHAR(50)"),
            ("edited_remarks", "TEXT"),
            ("original_remarks", "TEXT"),
            ("canvas_state", "TEXT"),
            ("edited_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for col_name, col_type in columns:
            try:
                db.session.execute(text(f"ALTER TABLE inspection_edits ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                print(f"Ensured column: {col_name}")
            except Exception as col_err:
                print(f"Warning: Could not add column {col_name}: {str(col_err)}")
        
        db.session.commit()
        print("Migration process completed.")
    except Exception as e:
        db.session.rollback()
        print(f"Migration process failed: {str(e)}")
