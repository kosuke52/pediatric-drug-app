import sqlite3
import json

def insert_sample_data():
    conn = sqlite3.connect('drug_data.db')
    cursor = conn.cursor()

    # 既存のデータをクリア（テスト用、本番では注意）
    # cursor.execute("DELETE FROM drugs")
    # conn.commit()

    # サンプルデータ
    sample_drugs = [
        {
            "drug_name": "カロナール細粒20%",
            "aliases": "アセトアミノフェン,解熱鎮痛剤",
            "type": "解熱鎮痛剤",
            "dosage_unit": "kg",
            "dose_per_kg": 0.005, # 5mg/kg = 0.005g/kg
            "daily_frequency": "1,2,3", # 1日1-3回
            "notes": "頓用、または6時間以上あけて使用"
        },
        {
            "drug_name": "カロナールシロップ2%",
            "aliases": "アセトアミノフェン,解熱鎮痛剤",
            "type": "解熱鎮痛剤",
            "dosage_unit": "fixed", # 固定用量
            "fixed_dose": 5.0, # 例: 5ml
            "daily_frequency": "1,2,3",
            "notes": "1回2.5ml〜10mlを頓用。詳細は年齢と体重で判断。"
        },
        {
        "drug_name": "ワイドシリン細粒10%",
        "aliases": "アモキシシリン,抗生剤",
        "type": "抗生剤",
        "dosage_unit": "kg",
        "dose_per_kg": 0.02, # 20mg/kg = 0.02g/kg
        "daily_frequency": "2,3",
        "notes": "食後投与推奨"
        },
        {
            "drug_name": "アスベリン散10%",
            "aliases": "チペピジンヒベンズ酸塩,鎮咳薬",
            "type": "鎮咳薬",
            "dosage_unit": "kg",
            "dose_per_kg": 0.001, # 1mg/kg = 0.001g/kg
            "daily_frequency": "3",
            "notes": "1日3回"
        },
        {
            "drug_name": "リンデロンシロップ0.01%",
            "aliases": "ベタメタゾン,ステロイド",
            "type": "ステロイド",
            "dosage_unit": "age", # 年齢で用量が決まる薬の例
            "min_age_months": 0,
            "max_age_months": 120, # 10歳まで
            "dose_age_specific": json.dumps({
                "0-12": 0.5,   # 0-12ヶ月: 0.5ml
                "13-36": 1.0,  # 1-3歳: 1.0ml
                "37-72": 1.5,  # 3-6歳: 1.5ml
                "73-120": 2.0  # 6-10歳: 2.0ml
            }),
            "daily_frequency": "1,2",
            "notes": "医師の指示に従う"
        },
        {
            "drug_name": "ムコダインDS50%",
            "aliases": "カルボシステイン,去痰薬",
            "type": "去痰薬",
            "dosage_unit": "kg",
            "dose_per_kg": 0.01, # 10mg/kg = 0.01g/kg
            "daily_frequency": "2,3",
            "notes": "通常、1日2〜3回に分けて経口投与"
        }
    ]

    for drug in sample_drugs:
        try:
            cursor.execute('''
                INSERT INTO drugs (
                    drug_name, aliases, type, dosage_unit,
                    dose_per_kg, min_age_months, max_age_months,
                    dose_age_specific, fixed_dose, daily_frequency, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                drug.get("drug_name"),
                drug.get("aliases"),
                drug.get("type"),
                drug.get("dosage_unit"),
                drug.get("dose_per_kg"),
                drug.get("min_age_months"),
                drug.get("max_age_months"),
                drug.get("dose_age_specific"),
                drug.get("fixed_dose"),
                drug.get("daily_frequency"),
                drug.get("notes")
            ))
        except sqlite3.IntegrityError as e:
            print(f"データの挿入中にエラーが発生しました（既に存在する可能性があります）: {drug.get('drug_name')} - {e}")

    conn.commit()
    conn.close()
    print("サンプルデータが 'drug_data.db' に挿入されました。")

if __name__ == "__main__":
    insert_sample_data()