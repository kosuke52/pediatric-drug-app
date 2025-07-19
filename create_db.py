import sqlite3
import json # dose_age_specific カラムでJSON形式を扱うため

def create_database():
    conn = sqlite3.connect('drug_data.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_name TEXT NOT NULL UNIQUE,
            aliases TEXT,
            type TEXT,
            dosage_unit TEXT NOT NULL, -- 'kg' or 'age' or 'fixed'
            dose_per_kg REAL,
            min_age_months INTEGER,
            max_age_months INTEGER,
            dose_age_specific TEXT, -- JSON string for age-specific doses
            fixed_dose REAL,
            daily_frequency TEXT, -- Comma-separated string like "1,2,3"
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("データベース 'drug_data.db' とテーブル 'drugs' が正常に作成されました。")

if __name__ == "__main__":
    create_database()