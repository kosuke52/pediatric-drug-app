import sqlite3
import csv
import json
import os 

# RenderでSQLiteを使うためのパス設定
DATABASE_DIR = '/var/data' if 'RENDER' in os.environ else '.' 
DATABASE_FILE = os.path.join(DATABASE_DIR, 'drug_data.db')

def clear_all_drugs_data(db_filepath=DATABASE_FILE): 
    conn = sqlite3.connect(db_filepath)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM drugs")
    conn.commit()
    conn.close()
    print("既存の薬データを全て削除しました。")

def import_drugs_from_csv(csv_filepath, db_filepath=DATABASE_FILE): 
    conn = None
    try:
        # Render環境の場合、永続ディレクトリを作成
        if not os.path.exists(DATABASE_DIR):
            os.makedirs(DATABASE_DIR)

        conn = sqlite3.connect(db_filepath)
        cursor = conn.cursor()

        columns = [
            'drug_name', 'aliases', 'type', 'dosage_unit',
            'dose_per_kg', 'min_age_months', 'max_age_months',
            'dose_age_specific', 'fixed_dose', 'daily_frequency', 'notes',
            'usage_type', 'timing_options', 'formulation_type',
            'calculated_dose_unit'
        ]

        placeholders = ', '.join(['?' for _ in columns])
        insert_query = f"INSERT INTO drugs ({', '.join(columns)}) VALUES ({placeholders})"

        print(f"CSVファイル '{csv_filepath}' からデータをインport中...")

        with open(csv_filepath, mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)

            if not all(col in csv_reader.fieldnames for col in columns):
                missing_cols = [col for col in columns if col not in csv_reader.fieldnames]
                print(f"警告: CSVファイルのヘッダーに不足しているカラムがあります: {', '.join(missing_cols)}")
                print(f"期待されるカラム: {columns}")
                print(f"CSVのヘッダー: {csv_reader.fieldnames}")

            for row_num, row in enumerate(csv_reader, start=2):
                data_to_insert = []
                for col in columns:
                    value = row.get(col) 

                    if col == 'dose_age_specific' and value:
                        try:
                            value = json.dumps(json.loads(value))
                        except json.JSONDecodeError:
                            print(f"警告: {csv_filepath} の行 {row_num} で '{col}' のJSON形式が不正です: {value}")
                            value = None
                    
                    if col in ['dose_per_kg', 'min_age_months', 'max_age_months', 'fixed_dose']:
                        if value == '':
                            value = None
                        elif value is not None:
                            try:
                                value = float(value) if '.' in str(value) else int(value)
                            except ValueError:
                                print(f"警告: {csv_filepath} の行 {row_num} で '{col}' の数値形式が不正です: {value}")
                                value = None
                    
                    if col == 'usage_type' and (value is None or value.strip() == ''):
                        value = '内服' 
                    
                    data_to_insert.append(value)
                
                try:
                    cursor.execute(insert_query, tuple(data_to_insert))
                    print(f"行 {row_num} のデータ '{row.get('drug_name', '不明な薬名')}' を挿入しました。")
                except sqlite3.IntegrityError:
                    print(f"警告: 行 {row_num} のデータ '{row.get('drug_name', '不明な薬名')}' は既にデータベースに存在するためスキップしました。")
                except Exception as e:
                    print(f"エラー: 行 {row_num} のデータ挿入中に問題が発生しました: {e} (データ: {row})")
        
        conn.commit()
        print("CSVからのデータインポートが完了しました。")

    except FileNotFoundError:
        print(f"エラー: CSVファイル '{csv_filepath}' が見つかりません。")
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    csv_file = 'drugs_data.csv' 
    # ローカルでの開発・テスト時には clear_all_drugs_data() を必要に応じて有効に
    # Render環境で初期データを投入する場合は、RenderのShellやDeploy Hooksで直接実行
    # clear_all_drugs_data() 

    import_drugs_from_csv(csv_file)