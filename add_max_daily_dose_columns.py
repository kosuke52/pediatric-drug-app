import sqlite3

def add_max_daily_dose_columns_to_db(db_filepath='drug_data.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_filepath)
        cursor = conn.cursor()

        columns_to_add = {
            'max_daily_dose_per_kg': "REAL",
            'max_daily_fixed_dose': "REAL"
        }

        for column_name, column_type in columns_to_add.items():
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
            finally:
                pass # このfinallyはforループの外に移動しているはずですが、念のため

    except Exception as e:
        print(f"データベース接続またはメイン処理中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_max_daily_dose_columns_to_db()