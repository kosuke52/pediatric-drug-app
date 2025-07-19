from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import os 

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# --- データベース接続のヘルパー関数 ---
# Renderの永続ディスクのパスを設定 (Renderの仕様)
# Renderでは '/var/data' が永続ディスクとして推奨されるパス
DATABASE_DIR = '/var/data' if 'RENDER' in os.environ else '.' 
DATABASE_FILE = os.path.join(DATABASE_DIR, 'drug_data.db')

def get_db_connection():
    # Render環境の場合、永続ディレクトリを作成
    # ローカルではカレントディレクトリに作成される
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR)
        
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row 
    return conn

# アプリケーション起動時にDBの初期設定（テーブル作成）を行う
# これにより、データベースファイルが存在しない場合にテーブルが自動作成される
with app.app_context():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_name TEXT NOT NULL UNIQUE,
                aliases TEXT,
                type TEXT,
                dosage_unit TEXT NOT NULL,
                dose_per_kg REAL,
                min_age_months INTEGER,
                max_age_months INTEGER,
                dose_age_specific TEXT,
                fixed_dose REAL,
                daily_frequency TEXT,
                notes TEXT,
                usage_type TEXT DEFAULT '内服',
                timing_options TEXT,
                formulation_type TEXT,
                calculated_dose_unit TEXT
            )
        ''')
        conn.commit()
        print(f"データベーステーブル 'drugs' が {DATABASE_FILE} に存在することを確認（または作成）しました。")
    except Exception as e:
        print(f"データベースの初期化中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()


# --- ルート（URLと関数のマッピング）の定義 ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manage')
def manage_drugs_page():
    return render_template('manage_drugs.html')

@app.route('/search')
def search_drugs_api():
    search_term = request.args.get('q', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT drug_name FROM drugs
        WHERE drug_name LIKE ? OR aliases LIKE ?
        ORDER BY drug_name
    """
    cursor.execute(query, (f'%{search_term}%', f'%{search_term}%'))
    
    results = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in results])

@app.route('/search_by_type')
def search_by_type_api():
    selected_type = request.args.get('type', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if selected_type:
        query = "SELECT drug_name FROM drugs WHERE type = ? ORDER BY drug_name"
        cursor.execute(query, (selected_type,))
    else: 
        query = "SELECT drug_name FROM drugs ORDER BY drug_name"
        cursor.execute(query)
    
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
    if patient_age_years_str:
        try:
            patient_age_years = int(patient_age_years_str)
            if patient_age_years >= 0:
                patient_age_months = patient_age_years * 12
        except ValueError:
            pass 

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM drugs WHERE drug_name = ?", (drug_name,))
    drug_info = cursor.fetchone()
    conn.close()

    if not drug_info:
        return jsonify({"error": "薬の情報が見つかりません。", "drug_data": None}), 404

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


    calculated_single_dose_value = None
    final_dose_unit = "" 

    if drug_info['dosage_unit'] == 'kg':
        if drug_info['dose_per_kg'] is not None:
            calculated_single_dose_value = patient_weight * drug_info['dose_per_kg']
        else:
            return jsonify({"error": f"{drug_name} は体重基準ですが、1kgあたりの用量データが設定されていません。", "drug_data": None}), 400
    elif drug_info['dosage_unit'] == 'age':
        if patient_age_months is None or patient_age_months < 0: 
             return jsonify({"error": f"{drug_name} は年齢基準の薬です。患者年齢を入力してください。", "drug_data": None}), 400

        if drug_info['dose_age_specific']:
            age_doses = json.loads(drug_info['dose_age_specific'])
            for age_range_str, dose in age_doses.items():
                min_age_db, max_age_db = map(int, age_range_str.split('-'))
                if min_age_db <= patient_age_months <= max_age_db:
                    calculated_single_dose_value = dose
                    break
            if calculated_single_dose_value is None:
                return jsonify({"error": f"{drug_name} は年齢基準ですが、入力された年齢 ({patient_age_years}歳) に該当する用量が見つかりません。", "drug_data": None}), 400
        else:
            return jsonify({"error": f"{drug_name} は年齢基準ですが、用量データが設定されていません。", "drug_data": None}), 400
    elif drug_info['dosage_unit'] == 'fixed':
        if drug_info['fixed_dose'] is not None:
            calculated_single_dose_value = drug_info['fixed_dose']
        else:
            return jsonify({"error": f"{drug_name} は固定用量ですが、データが設定されていません。", "drug_data": None}), 400
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
        "calculated_single_dose_value": calculated_single_dose_value,
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


# --- 薬の管理用API (変更なし) ---
@app.route('/search_all_drug_data')
def search_all_drug_data_api():
    search_term = request.args.get('q', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if search_term:
        query = """
            SELECT id, drug_name FROM drugs
            WHERE drug_name LIKE ? OR aliases LIKE ?
            ORDER BY drug_name
        """
        cursor.execute(query, (f'%{search_term}%', f'%{search_term}%'))
    else:
        query = "SELECT id, drug_name FROM drugs ORDER BY drug_name"
        cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in results])

@app.route('/drugs/<int:drug_id>')
def get_drug_by_id(drug_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM drugs WHERE id = ?", (drug_id,))
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
        
        return jsonify(drug_dict)
    return jsonify({"error": "Drug not found"}), 404

@app.route('/drugs', methods=['POST'])
def add_drug():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    drug_name = data.get('drug_name')
    if not drug_name:
        conn.close()
        return jsonify({"error": "薬の品名は必須です。"}), 400

    try:
        cursor.execute('''
            INSERT INTO drugs (
                drug_name, aliases, type, dosage_unit,
                dose_per_kg, min_age_months, max_age_months,
                dose_age_specific, fixed_dose, daily_frequency, notes,
                usage_type, timing_options, formulation_type, calculated_dose_unit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            drug_name,
            data.get('aliases'),
            data.get('type'),
            data.get('dosage_unit'),
            data.get('dose_per_kg'),
            data.get('min_age_months'),
            data.get('max_age_months'),
            json.dumps(data.get('dose_age_specific')) if data.get('dose_age_specific') else None,
            data.get('fixed_dose'),
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
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"'{drug_name}' は既に存在します。"}), 409
    except Exception as e:
        conn.close()
        return jsonify({"error": f"薬の追加中にエラーが発生しました: {str(e)}"}), 500

@app.route('/drugs/<int:drug_id>', methods=['PUT'])
def update_drug(drug_id):
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    drug_name = data.get('drug_name')
    if not drug_name:
        conn.close()
        return jsonify({"error": "薬の品名は必須です。"}), 400

    try:
        cursor.execute('''
            UPDATE drugs SET
                drug_name = ?, aliases = ?, type = ?, dosage_unit = ?,
                dose_per_kg = ?, min_age_months = ?, max_age_months = ?,
                dose_age_specific = ?, fixed_dose = ?, daily_frequency = ?, notes = ?,
                usage_type = ?, timing_options = ?, formulation_type = ?, calculated_dose_unit = ?
            WHERE id = ?
        ''', (
            drug_name,
            data.get('aliases'),
            data.get('type'),
            data.get('dosage_unit'),
            data.get('dose_per_kg'),
            data.get('min_age_months'),
            data.get('max_age_months'),
            json.dumps(data.get('dose_age_specific')) if data.get('dose_age_specific') else None,
            data.get('fixed_dose'),
            data.get('daily_frequency'),
            data.get('notes'),
            data.get('usage_type', '内服'),
            data.get('timing_options'),
            data.get('formulation_type'),
            data.get('calculated_dose_unit'),
            drug_id
        ))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "更新する薬が見つかりませんでした。"}), 404
        
        conn.close()
        return jsonify({"message": f"'{drug_name}' を更新しました。"}), 200
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"'{drug_name}' という薬名が既に存在します。"}), 409
    except Exception as e:
        conn.close()
        return jsonify({"error": f"薬の更新中にエラーが発生しました: {str(e)}"}), 500

@app.route('/drugs/<int:drug_id>', methods=['DELETE'])
def delete_drug(drug_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM drugs WHERE id = ?", (drug_id,))
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
    is_production = os.environ.get('FLASK_ENV') == 'production' or 'RENDER' in os.environ # Render環境も考慮
    app.run(debug=not is_production)