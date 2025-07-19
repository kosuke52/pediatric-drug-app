import sqlite3

def add_usage_type_column_to_db(db_filepath='drug_data.db'):
    conn = sqlite3.connect(db_filepath)
    cursor = conn.cursor()

    try:
        # 新しいカラム 'usage_type' を追加
        # DEFAULT '内服' とすることで、既存のデータにはデフォルト値が設定されます
        cursor.execute("ALTER TABLE drugs ADD COLUMN usage_type TEXT DEFAULT '内服'")
        conn.commit()
        print("カラム 'usage_type' が 'drugs' テーブルに正常に追加されました。")
        print("既存のレコードには '内服' がデフォルト値として設定されます。")
    except sqlite3.OperationalError as e:
        if "duplicate column name: usage_type" in str(e):
            print("カラム 'usage_type' は既に存在します。スキップします。")
        else:
            print(f"カラム追加中にエラーが発生しました: {e}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_usage_type_column_to_db()