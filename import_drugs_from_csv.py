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

# ★★★ データをPythonコード内に直接記述 ★★★
# このリストは、あなたが提供した長いCSVデータの内容をPythonのリスト形式にしたものです。
# もしCSVに変更を加えた場合は、このリストの内容も更新する必要があります。
EMBEDDED_DRUG_DATA = [
    {'drug_name': 'カロナール細粒20%', 'aliases': 'アセトアミノフェン,解熱鎮痛剤', 'type': '解熱鎮痛剤', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1,2,3', 'notes': '発熱時など', 'usage_type': '頓服', 'timing_options': None, 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.015, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 2000.0}, 
    {'drug_name': 'アスベリン散10%', 'aliases': 'チペピジンヒベンズ酸塩,鎮咳薬', 'type': '鎮咳薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '咳時', 'usage_type': '内服', 'timing_options': '朝食後,昼食後,夕食後', 'formulation_type': '散', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.003, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 0.02}, 
    {'drug_name': 'アレロック顆粒0.5%', 'aliases': 'オロパタジン,抗アレルギー薬', 'type': '抗アレルギー薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': 'アレルギー', 'usage_type': '内服', 'timing_options': '朝食後,眠前', 'formulation_type': '顆粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.004, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 0.008}, 
    {'drug_name': 'ムコダインDS50%', 'aliases': 'カルボシステイン,去痰薬', 'type': '去痰薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2,3', 'notes': None, 'usage_type': '内服', 'timing_options': '朝食後,昼食後,夕食後', 'formulation_type': 'DS', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.03, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 0.045}, 
    {'drug_name': 'リンデロンシロップ0.01%', 'aliases': 'ベタメタゾン,ステロイド', 'type': 'ステロイド', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 0, 'max_age_months': 120, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1,2', 'notes': '医師の指示に従う', 'usage_type': '内服', 'timing_options': '朝食後,昼食後', 'formulation_type': 'シロップ', 'calculated_dose_unit': 'ml', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"0-12\": 1.0, \"13-36\": 2.0, \"37-72\": 3.0, \"73-120\": 4.0}', 'max_daily_fixed_dose': 4.0}, 
    {'drug_name': 'ホクナリンテープ0.5mg', 'aliases': 'ツロブテロール', 'type': '気管支拡張薬', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 0, 'max_age_months': 11, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '副作用など', 'usage_type': '内服', 'timing_options': '朝', 'formulation_type': 'テープ', 'calculated_dose_unit': '枚', 'daily_dose_per_kg': None, 'daily_fixed_dose': 0.5, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 2.0}, 
    {'drug_name': 'ホクナリンテープ1mg', 'aliases': 'ツロブテロール', 'type': '気管支拡張薬', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 12, 'max_age_months': 59, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '副作用など', 'usage_type': '内服', 'timing_options': '朝', 'formulation_type': 'テープ', 'calculated_dose_unit': '枚', 'daily_dose_per_kg': None, 'daily_fixed_dose': 1.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 2.0}, 
    {'drug_name': 'ホクナリンテープ2mg', 'aliases': 'ツロブテロール', 'type': '気管支拡張薬', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 60, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '副作用など', 'usage_type': '内服', 'timing_options': '朝', 'formulation_type': 'テープ', 'calculated_dose_unit': '枚', 'daily_dose_per_kg': None, 'daily_fixed_dose': 2.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 2.0}, 
    {'drug_name': 'ステロイド軟膏0.1%', 'aliases': None, 'type': 'ステロイド', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '患部に塗布', 'usage_type': '外用', 'timing_options': '入浴後', 'formulation_type': '軟膏', 'calculated_dose_unit': '本', 'daily_dose_per_kg': None, 'daily_fixed_dose': 1.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 10.0}, 
    {'drug_name': 'アスベリンシロップ0.75%', 'aliases': None, 'type': '鎮咳薬', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': 'シロップ剤は乳児・幼児に適し、スポイト・シリンジ使用で正確な投与が可能。甘味があり飲みやすいが、糖分が多いため虫歯予防指導が必要。', 'usage_type': '内服', 'timing_options': '朝食後,昼食後,夕食後', 'formulation_type': 'シロップ', 'calculated_dose_unit': 'ml', 'daily_dose_per_kg': None, 'daily_fixed_dose': 0.6, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 2.4}, 
    {'drug_name': 'シングレア細粒4mg', 'aliases': 'モンテルカストナトリウム', 'type': '抗アレルギー薬（ロイコトリエン受容体拮抗薬）', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 0, 'max_age_months': 23, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '味は甘く服用しやすい。夜間の気管支収縮を抑制。吸入ステロイドと併用されることが多い。まれに興奮・イライラ・不眠などの中枢神経症状に注意が必要。食物と混ぜる場合は水分量に注意し、速やかに服用する。', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': '細粒', 'calculated_dose_unit': 'mg', 'daily_dose_per_kg': None, 'daily_fixed_dose': 4.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 5.0}, 
    {'drug_name': 'シングレアチュアブル錠5mg', 'aliases': 'モンテルカストナトリウム', 'type': '抗アレルギー薬（ロイコトリエン受容体拮抗薬）', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 60, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '飴状ではないため噛んでから飲み込むことを指導。歯に残るため、就寝前の歯磨きを忘れずに。OD錠ではない。', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': 'チュアブル錠', 'calculated_dose_unit': '錠', 'daily_dose_per_kg': None, 'daily_fixed_dose': 5.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 10.0}
]

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

# 引数から csv_filepath_or_data を受け取るのではなく、内蔵データを使用
def import_drugs_from_embedded_data(): # 関数名を変更
    conn = None
    try:
        conn = get_db_connection_for_import()
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

        for row_num, row_dict in enumerate(csv_rows, start=1): # 行番号を1から開始 (ヘッダーなし)
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
            except (sqlite3.IntegrityError, psycopg2.IntegrityError) as e: 
                print(f"警告: 行 {row_num} のデータ '{row_dict.get('drug_name', '不明な薬名')}' は既にデータベースに存在するためスキップしました。")
            except Exception as e:
                print(f"エラー: 行 {row_num} のデータ挿入中に問題が発生しました: {e} (データ: {row_dict})")
        
        conn.commit()
        print("データインポートが完了しました。")

    except Exception as e: # FileNotFoundErrorは発生しないため削除
        print(f"致命的なエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # このスクリプトは、Render の Web Service デプロイ後に、Render の Shell から実行することを想定
    # ローカルでテストインポートしたい場合は、以下のコメントアウトを外す
    # clear_all_drugs_data() 
    # import_drugs_from_embedded_data() # 内蔵データからインポートする関数を呼び出す
    print("このファイルはRenderのShellから 'python -c \"from import_drugs_from_csv import clear_all_drugs_data, import_drugs_from_embedded_data; clear_all_drugs_data(); import_drugs_from_embedded_data()\"' で実行してください。")