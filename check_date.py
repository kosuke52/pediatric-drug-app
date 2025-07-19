import sqlite3

def check_data():
    conn = sqlite3.connect('drug_data.db')
    cursor = conn.cursor()

    print("\n--- データベース内の全薬データ ---")
    cursor.execute("SELECT * FROM drugs")
    rows = cursor.fetchall() # すべての行を取得

    if not rows:
        print("データがありません。")
    else:
        # カラム名を取得（任意）
        column_names = [description[0] for description in cursor.description]
        print(column_names)
        print("-" * (len(str(column_names)) + 5)) # 見た目を整える線

        for row in rows:
            print(row)

    conn.close()
    print("---------------------------------")

if __name__ == "__main__":
    check_data()