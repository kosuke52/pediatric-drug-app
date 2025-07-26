import sqlite3
import csv
import json
import os 
import psycopg2 

# データベース接続のパス/URL設定
DATABASE_URL = os.environ.get('DATABASE_URL')

# ローカル開発用SQLiteのパス
DATABASE_DIR_SQLITE = '.' 
DATABASE_FILE_SQLITE = os.path.join(DATABASE_DIR_SQLITE, 'drug_data.db')

def get_db_connection_for_import(): 
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
    else:
        DATABASE_DIR = '.' 
        if not os.path.exists(DATABASE_DIR):
            os.makedirs(DATABASE_DIR)
        DATABASE_FILE = os.path.join(DATABASE_DIR, 'drug_data.db')
        conn = sqlite3.connect(DATABASE_FILE)
        
    conn.row_factory = sqlite3.Row 
    return conn

def clear_all_drugs_data():
    conn = None
    try:
        conn = get_db_connection_for_import()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM drugs")
        conn.commit()
        print("既存の薬データを全て削除しました。")
    except Exception as e:
        print(f"データベースクリア中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

def import_drugs_from_csv(csv_filepath_or_data): 
    conn = None
    try:
        conn = get_db_connection_for_import()
        cursor = conn.cursor()

        columns = [
            'drug_name', 'aliases', 'type', 'dosage_unit',
            # 古い用量カラムは読み込まない（またはNoneとして処理）
            'dose_per_kg', 'min_age_months', 'max_age_months',
            'dose_age_specific', 'fixed_dose', 
            # 新しい用量カラム
            'daily_dose_per_kg', 'daily_fixed_dose', 'daily_dose_age_specific',
            'daily_frequency', 'notes', 'usage_type', 'timing_options', 'formulation_type',
            'calculated_dose_unit'
        ]

        insert_placeholders = ', '.join(['%s'] * len(columns)) if DATABASE_URL else ', '.join(['?'] * len(columns))
        insert_query = f"INSERT INTO drugs ({', '.join(columns)}) VALUES ({insert_placeholders})"

        if isinstance(csv_filepath_or_data, list): 
            csv_rows = csv_filepath_or_data
            print("リストデータからデータをインポート中...")
        else: 
            print(f"CSVファイル '{csv_filepath_or_data}' からデータをインポート中...")
            with open(csv_filepath_or_data, mode='r', encoding='utf-8') as file:
                csv_reader_dict = csv.DictReader(file)
                csv_rows = [row for row in csv_reader_dict]

        for row_num, row_dict in enumerate(csv_rows, start=2): 
            data_to_insert = []
            for col in columns:
                value = row_dict.get(col) 

                if col == 'dose_age_specific' and value:
                    try:
                        value = json.dumps(json.loads(value))
                    except json.JSONDecodeError:
                        print(f"警告: 行 {row_num} で '{col}' のJSON形式が不正です: {value}")
                        value = None
                
                # daily_dose_age_specific もJSONとして扱う
                if col == 'daily_dose_age_specific' and value:
                    try:
                        value = json.dumps(json.loads(value))
                    except json.JSONDecodeError:
                        print(f"警告: 行 {row_num} で '{col}' のJSON形式が不正です: {value}")
                        value = None

                # 数値型カラムの処理
                if col in ['dose_per_kg', 'min_age_months', 'max_age_months', 'fixed_dose',
                            'daily_dose_per_kg', 'daily_fixed_dose']: # 新しい数値カラムも追加
                    if value == '':
                        value = None
                    elif value is not None:
                        try:
                            value = float(value) if '.' in str(value) else int(value)
                        except ValueError:
                            print(f"警告: 行 {row_num} で '{col}' の数値形式が不正です: {value}")
                            value = None
                
                if col == 'usage_type' and (value is None or value.strip() == ''):
                    value = '内服' 
                
                data_to_insert.append(value)
            
            try:
                cursor.execute(insert_query, tuple(data_to_insert))
                print(f"行 {row_num} のデータ '{row_dict.get('drug_name', '不明な薬名')}' を挿入しました。")
            except (sqlite3.IntegrityError, psycopg2.IntegrityError): 
                print(f"警告: 行 {row_num} のデータ '{row_dict.get('drug_name', '不明な薬名')}' は既にデータベースに存在するためスキップしました。")
            except Exception as e:
                print(f"エラー: 行 {row_num} のデータ挿入中に問題が発生しました: {e} (データ: {row_dict})")
        
        conn.commit()
        print("CSVからのデータインポートが完了しました。")

    except FileNotFoundError:
        print(f"エラー: CSVファイル '{csv_filepath_or_data}' が見つかりません。")
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    csv_file = 'drugs_data.csv' 
    
    # ローカルでテストインポートする場合のみ clear_all_drugs_data() を有効にする
    # Heroku/Renderのシェルから実行する場合は、環境変数 DATABASE_URL が設定されていれば PostgreSQL に接続する
    # このスクリプトは Render の Web Service デプロイ後に、Render の Shell から実行することを想定
    # clear_all_drugs_data() 

    # ★★★ ここを有効にしてローカルのCSVからインポートしたい場合は以下のようにする ★★★
    # clear_all_drugs_data() 
    # import_drugs_from_csv(csv_file)
    # ★★★ ここまで ★★★

    if os.environ.get('DATABASE_URL'):
        print("このスクリプトはRenderのシェルからは、直接CSVファイルパス指定で実行できません。")
        print("Renderのシェルで実行するには、Python -c コマンドを使ってデータをリストで渡してください。")
    else:
        print(f"ローカルのSQLiteデータベース '{DATABASE_FILE_SQLITE}' にインポートします。")
        # デフォルトでローカルで動作するよう
        clear_all_drugs_data()
        import_drugs_from_csv(csv_file)