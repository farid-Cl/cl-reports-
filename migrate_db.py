import sqlite3
import os

db_path = 'instance/reports.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE kpi_definition ADD COLUMN description TEXT")
        conn.commit()
        print("Added 'description' column to kpi_definition table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'description' already exists.")
        else:
            print(f"Error: {e}")
    conn.close()
else:
    print(f"Database {db_path} not found.")
