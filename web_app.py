from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import os 
import psycopg2 
import psycopg2.extras 

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = None 
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        cursor_factory_class = psycopg2.extras.DictCursor
    else:
        DATABASE_DIR = '.' 
        if not os.path.exists(DATABASE_DIR):
            os.makedirs(DATABASE_DIR)
        DATABASE_FILE = os.path.join(DATABASE_DIR, 'drug_data.db')
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor_factory_class = None 

    return conn, cursor_factory_class 

# アプリケーション起動時にDBの初期設定（テーブル作成）を行う
with app.app_context():
    conn = None
    try:
        conn_obj, cursor_factory_class = get_db_connection()
        conn = conn_obj

        if DATABASE_URL:
            cursor = conn.cursor(cursor_factory=cursor_factory_class)
        else:
            cursor = conn.cursor()
        
        create_table_sql = '''
            CREATE TABLE IF NOT EXISTS drugs (
                id SERIAL PRIMARY KEY, 
                drug_name TEXT NOT NULL UNIQUE,
                aliases TEXT,
                type TEXT,
                dosage_unit TEXT NOT NULL, -- 'kg', 'age', 'fixed' (基本単位)

                -- 1回あたり用量に関するフィールド (頓服や内服の1回量計算に使用)
                single_dose_per_kg REAL,
                single_fixed_dose REAL,
                single_dose_age_specific TEXT, -- JSON形式: {"min_age-max_age": dose}

                -- 1日総量に関するフィールド (主に内服薬の1日総量計算に使用)
                daily_dose_per_kg REAL,
                daily_fixed_dose REAL,
                daily_dose_age_specific TEXT, -- JSON形式: {"min_age-max_age": dose}
                
                -- 各薬で共通の用量情報
                min_age_months INTEGER,
                max_age_months INTEGER,
                
                daily_frequency TEXT,       -- カンマ区切り例: "1,2,3"
                notes TEXT,
                usage_type TEXT DEFAULT '内服', -- '内服' or '頓服'
                timing_options TEXT,        -- カンマ区切り例: "毎食後,必要時"
                formulation_type TEXT,      -- 剤形 (例: 細粒, テープ, 坐剤)
                calculated_dose_unit TEXT,  -- 最終的な計算結果の単位 (例: mg, ml, g, 個)

                max_daily_fixed_dose REAL,  -- 絶対的な1日最大量 (例: カロナールは4000mg)
                max_daily_times INTEGER     -- 頓服薬の1日最大服用回数 (例: 頓服は1日3回まで)
            );
        '''
        cursor.execute(create_table_sql)
        conn.commit()
        print("データベーステーブル 'drugs' が存在することを確認（または作成）しました。")
    except Exception as e:
        print(f"データベースの初期化中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manage')
def manage_drugs_page():
    return render_template('manage_drugs.html')

@app.route('/search')
def search_drugs_api():
    search_term = request.args.get('q', '').strip()
    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()
    
    limit = 5 
    
    query_placeholder = '%s' if DATABASE_URL else '?'

    query = f"""
        SELECT drug_name FROM drugs
        WHERE drug_name ILIKE {query_placeholder} OR aliases ILIKE {query_placeholder}
        ORDER BY drug_name
        LIMIT {limit}
    """
    cursor.execute(query, (f'%{search_term}%', f'%{search_term}%'))
    
    results = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in results])

@app.route('/search_by_type')
def search_by_type_api():
    selected_type = request.args.get('type', '').strip()
    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()
    
    limit = 5

    query_base = "SELECT drug_name FROM drugs WHERE type = %s ORDER BY drug_name LIMIT %s"
    if not DATABASE_URL: # SQLiteの場合
        query_base = query_base.replace('%s', '?')

    if selected_type:
        cursor.execute(query_base, (selected_type, limit))
    else: 
        return jsonify([]) 

    results = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in results])

@app.route('/calculate_dosage', methods=['POST'])
def calculate_dosage_api():
    data = request.get_json()
    drug_name = data.get('drug_name')
    patient_weight_str = data.get('weight')
    patient_age_years_str = data.get('age_years') 

    try:
        patient_weight = float(patient_weight_str) if patient_weight_str else 0.0
        if patient_weight <= 0:
            return jsonify({"error": "患者体重が正しくありません。", "drug_data": None}), 400
    except ValueError:
        return jsonify({"error": "患者体重は数値で入力してください。", "drug_data": None}), 400

    patient_age_months = None
    if not patient_age_years_str or int(patient_age_years_str) < 0: 
        return jsonify({"error": "患者年齢は必須です。正しく入力してください。", "drug_data": None}), 400
    try:
        patient_age_years = int(patient_age_years_str)
        patient_age_months = patient_age_years * 12
    except ValueError:
        return jsonify({"error": "患者年齢は数値で入力してください。", "drug_data": None}), 400


    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()
    
    query_placeholder = '%s' if DATABASE_URL else '?'
    # 新しいカラムも取得するようにSELECT * を使用
    cursor.execute(f"SELECT * FROM drugs WHERE drug_name = {query_placeholder}", (drug_name,))
    drug_info = cursor.fetchone()
    conn.close()

    if not drug_info:
        return jsonify({"error": "薬の情報が見つかりません。", "drug_data": None}), 404

    # 年齢バリデーション
    if patient_age_months is not None: 
        min_age_drug = drug_info['min_age_months']
        max_age_drug = drug_info['max_age_months']

        if min_age_drug is not None and patient_age_months < min_age_drug:
            min_age_years_display = f"{min_age_drug // 12}歳"
            if min_age_drug % 12 > 0:
                min_age_years_display += f"{min_age_drug % 12}ヶ月"
            return jsonify({"error": f"{drug_name} は {min_age_years_display}未満の患者には推奨されません。", "drug_data": None}), 400
        
        if max_age_drug is not None and patient_age_months > max_age_drug:
            max_age_years_display = f"{max_age_drug // 12}歳"
            if max_age_drug % 12 > 0:
                max_age_years_display += f"{max_age_drug % 12}ヶ月"
            return jsonify({"error": f"{drug_name} は {max_age_years_display}を超える患者には推奨されません。", "drug_data": None}), 400

    calculated_dose_for_frontend = None # フロントエンドに返す、計算された用量
    final_dose_unit = "" 
    usage_type = drug_info['usage_type'] if drug_info['usage_type'] else "内服"
    
    # 薬の用法タイプによって計算を分岐
    if usage_type == '頓服':
        # 頓服薬の1回用量を計算
        single_dose_value = None
        if drug_info['dosage_unit'] == 'kg':
            if drug_info['single_dose_per_kg'] is not None:
                single_dose_value = patient_weight * drug_info['single_dose_per_kg']
            else:
                return jsonify({"error": f"{drug_name} (頓服) は体重基準ですが、1回あたりの用量データが設定されていません。", "drug_data": None}), 400
        elif drug_info['dosage_unit'] == 'age':
            if drug_info['single_dose_age_specific']:
                age_doses = json.loads(drug_info['single_dose_age_specific'])
                for age_range_str, dose in age_doses.items():
                    min_age_db, max_age_db = map(int, age_range_str.split('-'))
                    if min_age_db <= patient_age_months <= max_age_db:
                        single_dose_value = dose
                        break
                if single_dose_value is None:
                    return jsonify({"error": f"{drug_name} (頓服) は年齢基準ですが、入力された年齢 ({patient_age_years}歳) に該当する1回用量が見つかりません。", "drug_data": None}), 400
            else:
                return jsonify({"error": f"{drug_name} (頓服) は年齢基準ですが、1回用量データが設定されていません。", "drug_data": None}), 400
        elif drug_info['dosage_unit'] == 'fixed':
            if drug_info['single_fixed_dose'] is not None:
                single_dose_value = drug_info['single_fixed_dose']
            else:
                return jsonify({"error": f"{drug_name} (頓服) は固定用量ですが、1回用量データが設定されていません。", "drug_data": None}), 400
        else:
            return jsonify({"error": f"{drug_name} (頓服) の用量計算の基準が不明です。", "drug_data": None}), 400
        
        calculated_dose_for_frontend = single_dose_value # 頓服の場合、フロントエンドには1回用量を渡す
        
        # 1日最大総量のバリデーション (頓服でも適用される場合)
        max_daily_fixed_dose = drug_info['max_daily_fixed_dose']
        if max_daily_fixed_dose is not None and calculated_dose_for_frontend is not None:
            # 暫定的に1回量がmax_daily_fixed_doseを超えるのはおかしい
            if calculated_dose_for_frontend > max_daily_fixed_dose:
                return jsonify({"error": f"{drug_name} の1回用量 ({calculated_dose_for_frontend:.3f}) が絶対的な1日最大量 ({max_daily_fixed_dose:.3f}) を超えています。", "drug_data": None}), 400

    else: # 内服薬の場合
        # 内服薬の1日総量を計算
        if drug_info['dosage_unit'] == 'kg':
            if drug_info['daily_dose_per_kg'] is not None: 
                calculated_dose_for_frontend = patient_weight * drug_info['daily_dose_per_kg']
            else:
                return jsonify({"error": f"{drug_name} (内服) は体重基準ですが、1日あたりの用量データが設定されていません。", "drug_data": None}), 400
        elif drug_info['dosage_unit'] == 'age':
            if drug_info['daily_dose_age_specific']: 
                age_doses = json.loads(drug_info['daily_dose_age_specific'])
                for age_range_str, dose in age_doses.items():
                    min_age_db, max_age_db = map(int, age_range_str.split('-'))
                    if min_age_db <= patient_age_months <= max_age_db:
                        calculated_dose_for_frontend = dose
                        break
                if calculated_dose_for_frontend is None:
                    return jsonify({"error": f"{drug_name} (内服) は年齢基準ですが、入力された年齢 ({patient_age_years}歳) に該当する1日用量が見つかりません。", "drug_data": None}), 400
            else:
                return jsonify({"error": f"{drug_name} (内服) は年齢基準ですが、1日用量データが設定されていません。", "drug_data": None}), 400
        elif drug_info['dosage_unit'] == 'fixed':
            if drug_info['daily_fixed_dose'] is not None: 
                calculated_dose_for_frontend = drug_info['daily_fixed_dose']
            else:
                return jsonify({"error": f"{drug_name} (内服) は固定用量ですが、1日総量データが設定されていません。", "drug_data": None}), 400
        else:
            return jsonify({"error": f"{drug_name} (内服) の用量計算の基準が不明です。", "drug_data": None}), 400

        # 1日最大総量のバリデーション (内服でも適用される場合)
        max_daily_fixed_dose = drug_info['max_daily_fixed_dose']
        if max_daily_fixed_dose is not None and calculated_dose_for_frontend is not None:
            if calculated_dose_for_frontend > max_daily_fixed_dose:
                return jsonify({"error": f"{drug_name} の1日総量 ({calculated_dose_for_frontend:.3f}) は、絶対的な1日最大量 ({max_daily_fixed_dose:.3f}) を超えています。", "drug_data": None}), 400
    
    # 最終的な単位の設定
    if drug_info['calculated_dose_unit']:
        final_dose_unit = drug_info['calculated_dose_unit']
    else: # calculated_dose_unit が設定されていない場合のフォールバック
        if drug_info['formulation_type'] == '細粒':
            final_dose_unit = "mg" # もしくは g など
            # ここで濃度計算が必要であれば追加
            # 例: もし calculated_dose_for_frontend が mg 単位で、表示は g にしたい場合
            # if drug_info.get('concentration_mg_per_g'):
            #    calculated_dose_for_frontend /= drug_info['concentration_mg_per_g']
            #    final_dose_unit = "g"
        elif drug_info['formulation_type'] == 'シロップ':
            final_dose_unit = "ml"
        elif drug_info['formulation_type'] in ['テープ', '貼付剤', '坐剤']:
            final_dose_unit = "枚" # または 個
        else:
            final_dose_unit = "mg" # デフォルト

    # フロントエンドに返す daily_frequency_options を usage_type に応じて調整
    daily_frequency_options_for_frontend = []
    if usage_type == '内服' and drug_info['daily_frequency']:
        daily_frequency_options_for_frontend = drug_info['daily_frequency'].split(',')
    elif usage_type == '頓服':
        # 頓服の場合は、daily_frequency_options は空にするか、
        # 1日最大服用回数があればそれをオプションとして渡す
        if drug_info['max_daily_times'] is not None:
            daily_frequency_options_for_frontend = [str(i) for i in range(1, drug_info['max_daily_times'] + 1)]
        else:
            daily_frequency_options_for_frontend = [] # 空にしてフロントエンドで「必要時」を推奨

    # フロントエンドに返す timing_options を usage_type に応じて調整
    timing_options_for_frontend = []
    if drug_info['timing_options']:
        all_timing_options = drug_info['timing_options'].split(',')
        if usage_type == '内服':
            # 内服で一般的なタイミングを優先 (例: '毎食後', '朝食後', '夕食後' など)
            general_timings = ['朝食後', '昼食後', '夕食後', '毎食後', '朝', '昼', '夕', '眠前', '就寝前', '食前', '食間', '1日1回', '1日2回', '1日3回', '1日4回']
            timing_options_for_frontend = [t for t in all_timing_options if any(gt in t for gt in general_timings)]
            if not timing_options_for_frontend: # 見つからなければ全て返す
                 timing_options_for_frontend = all_timing_options
        else: # 頓服
            # 頓服で一般的なタイミングを優先 (例: '必要時', '発熱時', '疼痛時' など)
            situational_timings = ['時', '必要時', '頓服', '発熱時', '疼痛時', '嘔吐時', '咳嗽時', '喘息時']
            timing_options_for_frontend = [t for t in all_timing_options if any(st in t for st in situational_timings)]
            if not timing_options_for_frontend: # 見つからなければ「必要時」をデフォルト
                timing_options_for_frontend = ['必要時']
    else: # timing_options がDBにない場合
        if usage_type == '頓服':
            timing_options_for_frontend = ['必要時']
        # 内服の場合は空のまま（フロントエンドで「タイミング候補なし」が表示される）
    

    response_data = {
        "drug_name": drug_info['drug_name'],
        "aliases": drug_info.get('aliases'), # フロントエンドで一般名を使用するため追加
        "calculated_daily_dose_value": calculated_dose_for_frontend, # 名前は daily_dose_value だが、頓服では1回量
        "dose_unit": final_dose_unit,
        "formulation_type": drug_info['formulation_type'] if drug_info['formulation_type'] else "",
        "notes": drug_info['notes'] if drug_info['notes'] else "",
        "daily_frequency_options": daily_frequency_options_for_frontend, # 調整済み
        "timing_options": timing_options_for_frontend,                   # 調整済み
        "initial_usage_type": usage_type,
        "min_age_months": drug_info['min_age_months'], 
        "max_age_months": drug_info['max_age_months'], 
        "max_daily_fixed_dose": drug_info['max_daily_fixed_dose'], # 必要に応じてフロントエンドへ
        "max_daily_times": drug_info['max_daily_times'],           # 頓服の最大回数
    }
    return jsonify(response_data)

# --- 薬の管理用API ---
@app.route('/search_all_drug_data')
def search_all_drug_data_api():
    search_term = request.args.get('q', '').strip()
    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()
    
    query_placeholder = '%s' if DATABASE_URL else '?'
    
    query = f"""
        SELECT id, drug_name FROM drugs
        WHERE drug_name ILIKE {query_placeholder} OR aliases ILIKE {query_placeholder}
        ORDER BY drug_name
    """
    cursor.execute(query, (f'%{search_term}%', f'%{search_term}%'))
    
    results = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in results])

@app.route('/drugs/<int:drug_id>')
def get_drug_by_id(drug_id):
    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()
    
    query_placeholder = '%s' if DATABASE_URL else '?'
    cursor.execute(f"SELECT * FROM drugs WHERE id = {query_placeholder}", (drug_id,))
    
    drug = cursor.fetchone()
    conn.close()

    if drug:
        drug_dict = dict(drug)
        if drug_dict['dose_age_specific']:
            try:
                drug_dict['dose_age_specific'] = json.loads(drug_dict['dose_age_specific'])
            except json.JSONDecodeError:
                drug_dict['dose_age_specific'] = {} 
                print(f"警告: データベースID {drug_id} の 'dose_age_specific' が不正なJSON形式です。")
        if drug_dict['daily_dose_age_specific']: 
            try:
                drug_dict['daily_dose_age_specific'] = json.loads(drug_dict['daily_dose_age_specific'])
            except json.JSONDecodeError:
                drug_dict['daily_dose_age_specific'] = {} 
                print(f"警告: データベースID {drug_id} の 'daily_dose_age_specific' が不正なJSON形式です。")
        
        return jsonify(drug_dict)
    return jsonify({"error": "Drug not found"}), 404

@app.route('/drugs', methods=['POST'])
def add_drug():
    data = request.get_json()
    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()

    drug_name = data.get('drug_name')
    if not drug_name:
        conn.close()
        return jsonify({"error": "薬の品名は必須です。"}), 400

    try:
        insert_columns = [
            'drug_name', 'aliases', 'type', 'dosage_unit',
            'dose_per_kg', 'min_age_months', 'max_age_months',
            'dose_age_specific', 'fixed_dose', 
            'daily_dose_per_kg', 'daily_fixed_dose', 'daily_dose_age_specific', 
            'daily_frequency', 'notes', 'usage_type', 'timing_options', 'formulation_type',
            'calculated_dose_unit',
            # 'max_daily_dose_per_kg', -- ★★★ この行を削除またはコメントアウト ★★★
            'max_daily_fixed_dose' 
        ]
        insert_placeholders = ', '.join(['%s'] * len(insert_columns)) if DATABASE_URL else ', '.join(['?'] * len(insert_columns))
        
        insert_query = f"INSERT INTO drugs ({', '.join(insert_columns)}) VALUES ({insert_placeholders})"

        cursor.execute(insert_query, (
            drug_name,
            data.get('aliases'),
            data.get('type'),
            data.get('dosage_unit'),
            data.get('dose_per_kg'), 
            data.get('min_age_months'),
            data.get('max_age_months'),
            json.dumps(data.get('dose_age_specific')) if data.get('dose_age_specific') else None, 
            data.get('fixed_dose'), 
            data.get('daily_dose_per_kg'), 
            data.get('daily_fixed_dose'), 
            json.dumps(data.get('daily_dose_age_specific')) if data.get('daily_dose_age_specific') else None, 
            data.get('daily_frequency'),
            data.get('notes'),
            data.get('usage_type', '内服'),
            data.get('timing_options'),
            data.get('formulation_type'),
            data.get('calculated_dose_unit'),
            # data.get('max_daily_dose_per_kg'), -- ★★★ この行を削除またはコメントアウト ★★★
            data.get('max_daily_fixed_dose') 
        ))
        conn.commit()
        conn.close()
        return jsonify({"message": f"'{drug_name}' を追加しました。", "id": cursor.lastrowid}), 201
    except (sqlite3.IntegrityError, psycopg2.IntegrityError) as e: 
        conn.close()
        if "duplicate key value violates unique constraint" in str(e):
             return jsonify({"error": f"'{drug_name}' は既に存在します。"}), 409
        else:
             return jsonify({"error": f"データベースエラーが発生しました: {str(e)}"}), 500
    except Exception as e:
        conn.close()
        return jsonify({"error": f"薬の追加中にエラーが発生しました: {str(e)}"}), 500

@app.route('/drugs/<int:drug_id>', methods=['PUT'])
def update_drug(drug_id):
    data = request.get_json()
    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()

    drug_name = data.get('drug_name')
    if not drug_name:
        conn.close()
        return jsonify({"error": "薬の品名は必須です。"}), 400

    try:
        update_set_clause = '''
            drug_name = %s, aliases = %s, type = %s, dosage_unit = %s,
            dose_per_kg = %s, min_age_months = %s, max_age_months = %s,
            dose_age_specific = %s, fixed_dose = %s, 
            daily_dose_per_kg = %s, daily_fixed_dose = %s, daily_dose_age_specific = %s,
            daily_frequency = %s, notes = %s,
            usage_type = %s, timing_options = %s, formulation_type = %s, calculated_dose_unit = %s,
            -- max_daily_dose_per_kg = %s, -- ★★★ この行を削除またはコメントアウト ★★★
            max_daily_fixed_dose = %s 
        '''
        if not DATABASE_URL: # SQLiteの場合
            update_set_clause = update_set_clause.replace('%s', '?')

        values = (
            drug_name,
            data.get('aliases'),
            data.get('type'),
            data.get('dosage_unit'),
            data.get('dose_per_kg'), 
            data.get('min_age_months'),
            data.get('max_age_months'),
            json.dumps(data.get('dose_age_specific')) if data.get('dose_age_specific') else None, 
            data.get('fixed_dose'), 
            data.get('daily_dose_per_kg'), 
            data.get('daily_fixed_dose'), 
            json.dumps(data.get('daily_dose_age_specific')) if data.get('daily_dose_age_specific') else None, 
            data.get('daily_frequency'),
            data.get('notes'),
            data.get('usage_type', '内服'),
            data.get('timing_options'),
            data.get('formulation_type'),
            data.get('calculated_dose_unit'),
            # data.get('max_daily_dose_per_kg'), -- ★★★ この行を削除またはコメントアウト ★★★
            data.get('max_daily_fixed_dose') 
        )
        
        where_placeholder = '%s' if DATABASE_URL else '?'

        cursor.execute(f'''
            UPDATE drugs SET
                {update_set_clause}
            WHERE id = {where_placeholder}
        ''', values + (drug_id,)) 

        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "更新する薬が見つかりませんでした。"}), 404
        
        conn.close()
        return jsonify({"message": f"'{drug_name}' を更新しました。"}), 200
    except (sqlite3.IntegrityError, psycopg2.IntegrityError) as e: 
        conn.close()
        if "duplicate key value violates unique constraint" in str(e):
             return jsonify({"error": f"'{drug_name}' という薬名が既に存在します。"}), 409
        else:
             return jsonify({"error": f"データベースエラーが発生しました: {str(e)}"}), 500
    except Exception as e:
        conn.close()
        return jsonify({"error": f"薬の更新中にエラーが発生しました: {str(e)}"}), 500

@app.route('/drugs/<int:drug_id>', methods=['DELETE'])
def delete_drug(drug_id):
    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()
    try:
        query_placeholder = '%s' if DATABASE_URL else '?'
        cursor.execute(f"DELETE FROM drugs WHERE id = {query_placeholder}", (drug_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "削除する薬が見つかりませんでした。"}), 404
        conn.close()
        return jsonify({"message": "薬を削除しました。"}), 200
    except Exception as e:
        conn.close()
        return jsonify({"error": f"薬の削除中にエラーが発生しました: {str(e)}"}), 500

if __name__ == '__main__':
    is_production = os.environ.get('FLASK_ENV') == 'production' or 'RENDER' in os.environ 
    app.run(debug=not is_production)