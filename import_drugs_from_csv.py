import sqlite3
import csv
import json
import os 
import psycopg2 

# データベース接続のパス/URL設定
DATABASE_URL = os.environ.get('DATABASE_URL') # Heroku PostgresのURL
# Renderの永続ディスクは使わない方針になったため、DATABASE_DIR_SQLITE はローカルのみで使用

def get_db_connection_for_import(): 
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
    else:
        # ローカル開発用にSQLiteをデフォルトにする
        # ローカルで drug_data.db を使用する場合、ディレクトリを作成
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

def import_drugs_from_csv(csv_filepath_or_data): # 引数をファイルパスまたは直接データに変更
    conn = None
    try:
        conn = get_db_connection_for_import()
        cursor = conn.cursor()

        columns = [
            'drug_name', 'aliases', 'type', 'dosage_unit',
            'dose_per_kg', 'min_age_months', 'max_age_months',
            'dose_age_specific', 'fixed_dose', 'daily_frequency', 'notes',
            'usage_type', 'timing_options', 'formulation_type',
            'calculated_dose_unit'
        ]

        insert_placeholders = ', '.join(['%s'] * len(columns)) if DATABASE_URL else ', '.join(['?'] * len(columns))
        insert_query = f"INSERT INTO drugs ({', '.join(columns)}) VALUES ({insert_placeholders})"

        # CSVデータを直接受け取るか、ファイルパスから読み込むか
        if isinstance(csv_filepath_or_data, list): # リスト形式でデータが渡された場合
            csv_rows = csv_filepath_or_data
            print("リストデータからデータをインポート中...")
        else: # ファイルパスが渡された場合
            print(f"CSVファイル '{csv_filepath_or_data}' からデータをインポート中...")
            with open(csv_filepath_or_data, mode='r', encoding='utf-8') as file:
                csv_reader_dict = csv.DictReader(file)
                csv_rows = [row for row in csv_reader_dict]

        # ヘッダーチェックはDictReaderが自動で行うため、ここでは省略

        for row_num, row_dict in enumerate(csv_rows, start=2): # DictReaderからの辞書を想定
            data_to_insert = []
            for col in columns:
                value = row_dict.get(col) # 辞書から直接値を取得

                if col == 'dose_age_specific' and value:
                    try:
                        value = json.dumps(json.loads(value))
                    except json.JSONDecodeError:
                        print(f"警告: 行 {row_num} で '{col}' のJSON形式が不正です: {value}")
                        value = None
                
                if col in ['dose_per_kg', 'min_age_months', 'max_age_months', 'fixed_dose']:
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
        print("データインポートが完了しました。")

    except FileNotFoundError:
        print(f"エラー: CSVファイル '{csv_filepath_or_data}' が見つかりません。")
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    csv_file = 'drugs_data.csv' 
    
    # ローカルでテストインポートする場合のみ有効にする
    # clear_all_drugs_data() 
    # import_drugs_from_csv(csv_file)

    # Heroku/Renderのシェルから直接Pythonを叩くための例
    # 環境変数 DATABASE_URL が設定されていれば PostgreSQL に接続する
    # このスクリプトは Render の Web Service デプロイ後に、Render の Shell から実行することを想定
    if 'DATABASE_URL' in os.environ:
        # Heroku/Render 上での初期データ投入
        # CSVデータをPythonコード内に直接記述するか、Webからダウンロードするように変更が必要
        # 今はテストのため何もしない（Shellで手動実行を想定）
        print("このスクリプトはローカル開発用です。Heroku/RenderではShellから手動でデータを投入してください。")
        print("例: python -c \"from import_drugs_from_csv import clear_all_drugs_data, import_drugs_from_csv; import_drugs_from_csv(あなたのCSVデータをPythonリストでここに記述);\"")