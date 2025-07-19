import sqlite3

def add_calculated_dose_unit_column_to_db(db_filepath='drug_data.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_filepath)
        cursor = conn.cursor()

        column_name = 'calculated_dose_unit'
        column_type = 'TEXT'

        try:
            cursor.execute(f"ALTER TABLE drugs ADD COLUMN {column_name} {column_type}")
            conn.commit()
            print(f"カラム '{column_name}' が 'drugs' テーブルに正常に追加されました。")
        except sqlite3.OperationalError as e:
            if f"duplicate column name: {column_name}" in str(e):
                print(f"カラム '{column_name}' は既に存在します。スキップします。")
            else:
                print(f"カラム追加中にエラーが発生しました: {e}")
        except Exception as e:
            print(f"予期せぬエラーが発生しました: {e}")

    except Exception as e:
        print(f"データベース接続またはメイン処理中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_calculated_dose_unit_column_to_db()