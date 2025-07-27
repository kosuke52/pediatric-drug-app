import sqlite3
import csv
import json
import os 
import psycopg2 
import psycopg2.extras # psycopg2.extras を追加

# データベース接続のパス/URL設定
DATABASE_URL = os.environ.get('DATABASE_URL') 

# ローカル開発用SQLiteのパス
DATABASE_DIR_SQLITE = '.' 
DATABASE_FILE_SQLITE = os.path.join(DATABASE_DIR_SQLITE, 'drug_data.db')

def get_db_connection_for_import(): 
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        # PostgreSQLの場合、row_factory は設定しない。DictCursorはカーソル作成時に指定
    else:
        DATABASE_DIR = '.' 
        if not os.path.exists(DATABASE_DIR):
            os.makedirs(DATABASE_DIR)
        DATABASE_FILE = os.path.join(DATABASE_DIR, 'drug_data.db')
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row # SQLiteの場合のみ設定
        
    # ここでは接続オブジェクトだけを返す。カーソルファクトリーは呼び出し元で利用
    return conn

def clear_all_drugs_data():
    conn = None
    try:
        conn = get_db_connection_for_import() # 接続オブジェクトを取得
        # カーソル作成。PostgreSQLの場合は psycopg2.extras.DictCursor を使用
        if DATABASE_URL:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) # DictCursorを指定
        else:
            cursor = conn.cursor()
            
        cursor.execute("DELETE FROM drugs")
        conn.commit()
        print("既存の薬データを全て削除しました。")
    except Exception as e:
        print(f"データベースクリア中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

# 引数から csv_filepath_or_data を受け取るのではなく、内蔵データを使用
def import_drugs_from_embedded_data(): # 関数名を変更
    conn = None
    try:
        conn = get_db_connection_for_import()
        # カーソル作成。PostgreSQLの場合は psycopg2.extras.DictCursor を使用
        if DATABASE_URL:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) # DictCursorを指定
        else:
            cursor = conn.cursor()

        columns = [
            'drug_name', 'aliases', 'type', 'dosage_unit',
            'dose_per_kg', 'min_age_months', 'max_age_months',
            'dose_age_specific', 'fixed_dose', 
            'daily_dose_per_kg', 'daily_fixed_dose', 'daily_dose_age_specific', 
            'daily_frequency', 'notes', 'usage_type', 'timing_options', 'formulation_type',
            'calculated_dose_unit',
            'max_daily_dose_per_kg', 'max_daily_fixed_dose' 
        ]

        insert_placeholders = ', '.join(['%s'] * len(columns)) if DATABASE_URL else ', '.join(['?'] * len(columns))
        insert_query = f"INSERT INTO drugs ({', '.join(columns)}) VALUES ({insert_placeholders})"

        print("内蔵リストデータからデータをインポート中...")

        # 内蔵データを使用
        csv_rows = EMBEDDED_DRUG_DATA 

        for row_num, row_dict in enumerate(csv_rows, start=1): 
            data_to_insert = []
            for col in columns:
                value = row_dict.get(col) 

                if col == 'dose_age_specific' and value:
                    try:
                        value = json.dumps(json.loads(value))
                    except json.JSONDecodeError:
                        print(f"警告: 行 {row_num} で '{col}' のJSON形式が不正です: {value}")
                        value = None
                
                if col == 'daily_dose_age_specific' and value:
                    try:
                        value = json.dumps(json.loads(value))
                    except json.JSONDecodeError:
                        print(f"警告: 行 {row_num} で '{col}' のJSON形式が不正です: {value}")
                        value = None

                if col in ['dose_per_kg', 'min_age_months', 'max_age_months', 'fixed_dose',
                            'daily_dose_per_kg', 'daily_fixed_dose', 
                            'max_daily_dose_per_kg', 'max_daily_fixed_dose']: 
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

    except Exception as e: 
        print(f"致命的なエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # このスクリプトは、Render の Web Service デプロイ後に、Render の Shell から実行することを想定
    # ローカルでテストインポートしたい場合は、以下のコメントアウトを外す
    # clear_all_drugs_data() 
    # import_drugs_from_embedded_data() 
    print("このファイルはRenderのShellから 'python -c \"from import_drugs_from_csv import clear_all_drugs_data, import_drugs_from_embedded_data; clear_all_drugs_data(); import_drugs_from_embedded_data()\"' で実行してください。")