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

        # カーソル作成 (psycopg2の場合は cursor_factory を指定)
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
                dosage_unit TEXT NOT NULL,
                dose_per_kg REAL, -- 古いカラム
                min_age_months INTEGER,
                max_age_months INTEGER,
                dose_age_specific TEXT, -- 古いカラム
                fixed_dose REAL, -- 古いカラム
                daily_dose_per_kg REAL, -- 新しいカラム
                daily_fixed_dose REAL, -- 新しいカラム
                daily_dose_age_specific TEXT, -- 新しいカラム
                daily_frequency TEXT, 
                notes TEXT,
                usage_type TEXT DEFAULT '内服',
                timing_options TEXT,
                formulation_type TEXT,
                calculated_dose_unit TEXT
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
    
    # ★★★ 検索結果を5個に制限 ★★★
    limit = 5 
    
    query_placeholder = '%s' if DATABASE_URL else '?'

    # 部分一致検索
    query = f"""
        SELECT drug_name FROM drugs
        WHERE drug_name ILIKE {query_placeholder} OR aliases ILIKE {query_placeholder}
        ORDER BY drug_name
        LIMIT {limit}
    """
    # PostgreSQLでは ILIKE で大文字小文字を無視した検索
    # SQLiteでは LIKE で大文字小文字を無視するため、そのまま

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
    
    # ★★★ 検索結果を5個に制限 ★★★
    limit = 5

    query_base = "SELECT drug_name FROM drugs WHERE type = %s ORDER BY drug_name LIMIT %s"
    if not DATABASE_URL: # SQLiteの場合
        query_base = query_base.replace('%s', '?')

    if selected_type:
        cursor.execute(query_base, (selected_type, limit))
    else: 
        # 全件表示はしない（検索結果を制限するため、ここは使用されない）
        # もし全件表示が必要なら、limitを考慮しないクエリにするか、別のAPIを用意
        return jsonify([]) # タイプ検索で空のタイプが選択されたら何も返さない

    results = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in results])

@app.route('/calculate_dosage', methods=['POST'])
def calculate_dosage_api():
    data = request.get_json()
    drug_name = data.get('drug_name')
    patient_weight_str = data.get('weight')
    patient_age_years_str = data.get('age_years') # 年齢は必須になる

    try:
        patient_weight = float(patient_weight_str) if patient_weight_str else 0.0
        if patient_weight <= 0:
            return jsonify({"error": "患者体重が正しくありません。", "drug_data": None}), 400
    except ValueError:
        return jsonify({"error": "患者体重は数値で入力してください。", "drug_data": None}), 400

    # ★★★ 年齢を必須にするバリデーション ★★★
    patient_age_months = None
    if not patient_age_years_str or int(patient_age_years_str) < 0:
        return jsonify({"error": "患者年齢は必須です。正しく入力してください。", "drug_data": None}), 400
    try:
        patient_age_years = int(patient_age_years_str)
        patient_age_months = patient_age_years * 12
    except ValueError:
        return jsonify({"error": "患者年齢は数値で入力してください。", "drug_data": None}), 400
    # ★★★ ここまで年齢必須バリデーション ★★★


    conn_obj, cursor_factory_class = get_db_connection()
    conn = conn_obj
    cursor = conn.cursor(cursor_factory=cursor_factory_class) if DATABASE_URL else conn.cursor()
    
    query_placeholder = '%s' if DATABASE_URL else '?'
    cursor.execute(f"SELECT * FROM drugs WHERE drug_name = {query_placeholder}", (drug_name,))
    drug_info = cursor.fetchone()
    conn.close()

    if not drug_info:
        return jsonify({"error": "薬の情報が見つかりません。", "drug_data": None}), 404

    # 年齢バリデーション（計算基準とは独立）
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


    calculated_daily_dose_value = None 
    final_dose_unit = "" 
    
    # 1日総量計算ロジック
    if drug_info['dosage_unit'] == 'kg':
        if drug_info['daily_dose_per_kg'] is not None: 
            calculated_daily_dose_value = patient_weight * drug_info['daily_dose_per_kg']
        else:
            return jsonify({"error": f"{drug_name} は体重基準ですが、1日あたりの用量データが設定されていません。", "drug_data": None}), 400
    elif drug_info['dosage_unit'] == 'age':
        if drug_info['daily_dose_age_specific']: 
            age_doses = json.loads(drug_info['daily_dose_age_specific'])
            for age_range_str, dose in age_doses.items():
                min_age_db, max_age_db = map(int, age_range_str.split('-'))
                if min_age_db <= patient_age_months <= max_age_db: # patient_age_months は必須になっている
                    calculated_daily_dose_value = dose
                    break
            if calculated_daily_dose_value is None:
                return jsonify({"error": f"{drug_name} は年齢基準ですが、入力された年齢 ({patient_age_years}歳) に該当する1日用量が見つかりません。", "drug_data": None}), 400
        else:
            return jsonify({"error": f"{drug_name} は年齢基準ですが、1日用量データが設定されていません。", "drug_data": None}), 400
    elif drug_info['dosage_unit'] == 'fixed':
        if drug_info['daily_fixed_dose'] is not None: 
            calculated_daily_dose_value = drug_info['daily_fixed_dose']
        else:
            return jsonify({"error": f"{drug_name} は固定用量ですが、1日総量データが設定されていません。", "drug_data": None}), 400
    else:
        return jsonify({"error": f"{drug_name} の用量計算の基準が不明です。", "drug_data": None}), 400

    if drug_info['calculated_dose_unit']:
        final_dose_unit = drug_info['calculated_dose_unit']
    elif drug_info['dosage_unit'] == 'kg':
        final_dose_unit = "g"
    elif drug_info['dosage_unit'] == 'age' or drug_info['dosage_unit'] == 'fixed':
        final_dose_unit = "ml"

    response_data = {
        "drug_name": drug_info['drug_name'],
        "calculated_daily_dose_value": calculated_daily_dose_value, 
        "dose_unit": final_dose_unit,
        "formulation_type": drug_info['formulation_type'] if drug_info['formulation_type'] else "",
        "notes": drug_info['notes'] if drug_info['notes'] else "",
        "daily_frequency_options": drug_info['daily_frequency'].split(',') if drug_info['daily_frequency'] else [],
        "timing_options": drug_info['timing_options'].split(',') if drug_info['timing_options'] else [],
        "initial_usage_type": drug_info['usage_type'] if drug_info['usage_type'] else "内服",
        "min_age_months": drug_info['min_age_months'], 
        "max_age_months": drug_info['max_age_months'], 
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
    
    # 管理画面の検索結果も制限するならここに LIMIT を追加
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
            'calculated_dose_unit'
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
            data.get('calculated_dose_unit')
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
            usage_type = %s, timing_options = %s, formulation_type = %s, calculated_dose_unit = %s
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
            data.get('calculated_dose_unit')
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