import sqlite3

def add_daily_dose_columns_to_db(db_filepath='drug_data.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_filepath)
        cursor = conn.cursor()

        columns_to_add = {
            'daily_dose_per_kg': "REAL",
            'daily_fixed_dose': "REAL",
            'daily_dose_age_specific': "TEXT" # JSON形式の文字列
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
                # このfinallyはforループの外に移動しているはずですが、念のため
                pass

    except Exception as e:
        print(f"データベース接続またはメイン処理中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_daily_dose_columns_to_db()