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

# ★★★ データをPythonコード内に直接記述 (ご提供のCSV内容に基づく) ★★★
EMBEDDED_DRUG_DATA = [
    {'drug_name': 'オゼックス細粒15%', 'aliases': 'トスフロキサシントシル酸塩', 'type': '抗菌薬（ニューキノロン系）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': '軟骨障害のリスクがあるため、基本的に他に代替薬がない場合に限る', 'usage_type': '内服', 'timing_options': '朝夕食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.08, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 24.0},
    {'drug_name': 'ワイドシリン細粒10%', 'aliases': 'アモキシシリン水和物100mg/g', 'type': '抗菌薬（ペニシリン系）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2,3', 'notes': '空腹時でも可。しばしば下痢が副作用として出やすい。細菌性中耳炎などで高用量が使用されることあり。', 'usage_type': '内服', 'timing_options': '朝夕食後,毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.3, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 9.0}, # 300mg/kg/日なので0.3g
    {'drug_name': 'ワイドシリン細粒20%', 'aliases': 'アモキシシリン水和物200mg/g', 'type': '抗菌薬（ペニシリン系）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2,3', 'notes': '細粒10%の半量で済むため、服薬量が少なくてすむ。小児に飲ませやすい。下痢に注意。', 'usage_type': '内服', 'timing_options': '朝夕食後,毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.15, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.5}, # 150mg/kg/日なので0.15g
    {'drug_name': 'メイアクトMS小児用細粒10%', 'aliases': 'セフジトレンピボキシル小児用細粒10％', 'type': '抗菌薬（第3世代セフェム系）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2,3', 'notes': '食後投与推奨。湿疹などのアレルギーに注意。味が甘く、服用しやすい。', 'usage_type': '内服', 'timing_options': '朝夕食後,毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.09, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 6.0}, # 90mg/kg/日なので0.09g
    {'drug_name': 'タミフルドライシロップ3%', 'aliases': 'オセルタミビルリン酸塩ドライシロップ３％', 'type': '抗ウイルス薬（抗インフルエンザ）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': '発症48時間以内の投与が有効。粉薬の計量ミスに注意。腸重積の報告あり、服用中は体調変化に注意。', 'usage_type': '内服', 'timing_options': '朝夕食後', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.133, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 2.66},
    {'drug_name': 'クラリスドライシロップ10%', 'aliases': 'クラリスロマイシンドライシロップ10％', 'type': '抗菌薬（マクロライド系）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2,3', 'notes': '味に苦味あり。CYP3A4阻害により薬物相互作用に注意。食後投与が望ましい。', 'usage_type': '内服', 'timing_options': '朝夕食後', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.15, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.0}, # 150mg/kg/日なので0.15g
    {'drug_name': 'ジスロマック細粒10%', 'aliases': 'アジスロマイシン細粒10％', 'type': '抗菌薬（マクロライド系）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '長時間作用型。服用期間は3日だが効果は7～10日持続。空腹時でも可、ただし胃腸症状に注意。\n2日目以降半量', 'usage_type': '内服', 'timing_options': '朝食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.1, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 5.0}, # 100mg/kg/日なので0.1g
    {'drug_name': 'カロナール細粒20%', 'aliases': 'アセトアミノフェン細粒20％', 'type': '解熱鎮痛薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2,3,4', 'notes': '解熱目的では38.5℃以上の発熱時に使用することが多い。使用間隔を空けずに連用すると肝機能障害のリスクがある。乳児でも使用可能で安全性が高いが、過量投与には十分注意する。坐薬との併用時には成分量の重複に注意する。苦味は少なく服用しやすい。', 'usage_type': '内服', 'timing_options': '朝夕食後,毎食後,発熱時', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.0225, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.0}, # 22.5mg/kg/日なので0.0225g
    {'drug_name': 'カロナール細粒50%', 'aliases': 'アセトアミノフェン細粒50％', 'type': '解熱鎮痛薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2,3,4', 'notes': '服用量を減らせるため、体重が重い児に適する。苦味が強くなることがあるため、飲みにくさに注意。少量で済むが誤投与時のリスクがやや上がる。', 'usage_type': '内服', 'timing_options': '朝夕食後,毎食後,発熱時', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.09, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 3.0}, # 90mg/kg/日なので0.09g
    {'drug_name': 'カロナールシロップ2%', 'aliases': 'アセトアミノフェンシロップ2％', 'type': '解熱鎮痛薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2,3', 'notes': '乳児や粉薬を嫌がる児に適する。甘味があり飲みやすいが、糖分が多く虫歯リスクに注意。計量ミス防止のため、スポイトやシリンジを活用。冷蔵保存不要。', 'usage_type': '内服', 'timing_options': '朝夕食後,毎食後,発熱時', 'formulation_type': 'シロップ', 'calculated_dose_unit': 'ml', 'daily_dose_per_kg': 0.3, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 30.0}, # 30mg/kg/日なので0.3ml
    {'drug_name': 'ザイザルシロップ0.05%', 'aliases': 'レボセチリジン塩酸塩シロップ0.05％', 'type': '抗アレルギー薬（第2世代抗ヒスタミン薬）', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 6, 'max_age_months': 191, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1,2', 'notes': '生後6ヵ月以上～1歳未満：1回2.5 mL（1.25 mg）を1日1回経口投与\n腎機能低下時は減量必要 。眠気は少ないが報告あり。季節性アレルギーでは発症前から使用継続が望ましい 。', 'usage_type': '内服', 'timing_options': '眠前,朝食後眠前', 'formulation_type': 'シロップ', 'calculated_dose_unit': 'ml', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"6-11\":1.25, \"12-95\":2.5, \"96-191\":5.0}', 'max_daily_fixed_dose': 20.0}, # 1.25, 2.5, 5mg/日 → 1.25, 2.5, 5ml/日として扱いました
    {'drug_name': 'オノンドライシロップ 10％', 'aliases': 'プランルカスト水和物ドライシロップ10％', 'type': '抗アレルギー薬（ロイコトリエン受容体拮抗薬）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': 18, 'max_age_months': 540, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': '12 kg以上～18 kg未満        0.5 g（プランルカスト水和物として50 mg）\n18 kg以上～25 kg未満        0.7 g（プランルカスト水和物として70 mg）\n25 kg以上～35 kg未満        1.0 g（プランルカスト水和物として100 mg）\n35 kg以上～45 kg未満        1.4 g（プランルカスト水和物として140 mg）\n喘息合併・皮疹対応も可能。瓶・分包あり、服用しやすい。', 'usage_type': '内服', 'timing_options': '朝夕食後', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.07, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.5}, # 70mg/kg/日相当で0.07gと仮定
    {'drug_name': 'ホクナリンテープ0.5mg', 'aliases': 'ツロブテロールテープ0.5 mg', 'type': '気管支拡張薬', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 0, 'max_age_months': 47, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '副作用として頻脈・振戦・発疹などあり。皮膚刺激やかぶれに注意し、貼付部位は毎日変える。貼付部位は胸部・背部・上腕部・下腹部のいずれか。入浴や発汗でも剥がれにくいが、貼付状態は確認する。β2刺激薬による中枢刺激症状（興奮、不眠など）にも注意が必要。貼り忘れに注意し、朝の貼付が一般的。', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': 'テープ', 'calculated_dose_unit': '枚', 'daily_dose_per_kg': None, 'daily_fixed_dose': 0.5, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 1.0}, # 0.5枚/日
    {'drug_name': 'ホクナリンテープ1mg', 'aliases': 'ツロブテロールテープ1 mg', 'type': '気管支拡張薬', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 48, 'max_age_months': 119, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '副作用として頻脈・振戦・発疹などあり。皮膚刺激やかぶれに注意し、貼付部位は毎日変える。貼付部位は胸部・背部・上腕部・下腹部のいずれか。入浴や発汗でも剥がれにくいが、貼付状態は確認する。β2刺激薬による中枢刺激症状（興奮、不眠など）にも注意が必要。貼り忘れに注意し、朝の貼付が一般的。', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': 'テープ', 'calculated_dose_unit': '枚', 'daily_dose_per_kg': None, 'daily_fixed_dose': 1.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 1.0}, # 1.0枚/日
    {'drug_name': 'ホクナリンテープ2mg', 'aliases': 'ツロブテロール2mg', 'type': '気管支拡張薬', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 120, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '副作用として頻脈・振戦・発疹などあり。皮膚刺激やかぶれに注意し、貼付部位は毎日変える。貼付部位は胸部・背部・上腕部・下腹部のいずれか。入浴や発汗でも剥がれにくいが、貼付状態は確認する。β2刺激薬による中枢刺激症状（興奮、不眠など）にも注意が必要。貼り忘れに注意し、朝の貼付が一般的。', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': 'テープ', 'calculated_dose_unit': '枚', 'daily_dose_per_kg': None, 'daily_fixed_dose': 2.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 2.0}, # 2.0枚/日
    {'drug_name': 'サワシリン細粒10%', 'aliases': 'アモキシシリン水和物細粒100 mg/g', 'type': '抗菌薬（ペニシリン系）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '下痢が出やすいため注意。食後の方が胃腸障害が少なくなる傾向がある。甘味があり比較的服用しやすい。', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.3, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 10.0}, # 300mg/kg/日なので0.3g
    {'drug_name': 'サワシリン細粒20%', 'aliases': 'アモキシシリン水和物細粒200 mg/g', 'type': '抗菌薬（ペニシリン系）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '細粒10%の半量で済むため、服薬量が少なくてすむ。小児に飲ませやすい。下痢に注意。', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.15, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 5.0}, # 150mg/kg/日なので0.15g
    {'drug_name': 'アスベリンドライシロップ2%', 'aliases': 'チペピジンクエン酸塩ドライシロップ2％', 'type': '鎮咳薬', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 0, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '甘味があり飲みやすいが、やや粉臭あり。痰が出しにくいタイプの咳に適応。気道分泌を促す作用もあるため、痰を伴う咳に効果的。眠気はほぼない。乳幼児でも使用可能。', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"0-11\":0.5, \"12-47\":1.0, \"48-83\":1.75, \"84-999\":4.0}', 'max_daily_fixed_dose': 6.0}, # 0.5g/日, 1.0g/日, 1.75g/日, 4.0g/日
    {'drug_name': 'アスベリンシロップ0.5%', 'aliases': 'チペピジンクエン酸塩シロップ0.5％', 'type': '鎮咳薬', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 0, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': 'シロップ剤は乳児・幼児に適し、スポイト・シリンジ使用で正確な投与が可能。甘味があり飲みやすいが、糖分が多いため虫歯予防指導が必要。', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': 'シロップ', 'calculated_dose_unit': 'ml', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"0-11\":2.0, \"12-47\":4.0, \"48-83\":6.0, \"84-999\":20.0}', 'max_daily_fixed_dose': 24.0}, # 2ml/日, 4ml/日, 6ml/日, 20ml/日
    {'drug_name': 'アレロック顆粒0.5％', 'aliases': 'オロパタジン塩酸塩顆粒0.5％', 'type': '抗アレルギー薬（第2世代抗ヒスタミン薬）', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 24, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': '効果が認められない場合，1–2週ごとに再評価。漫然長期投与は避ける。', 'usage_type': '内服', 'timing_options': '朝食後眠前', 'formulation_type': '顆粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"24-95\":1.0, \"96-999\":2.0}', 'max_daily_fixed_dose': 2.0}, # 1.0g/日, 2.0g/日
    {'drug_name': 'ケフラール細粒小児用100mg', 'aliases': 'セファクロル水和物細粒100 mg/g', 'type': '抗菌薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '味は比較的良好で、飲みやすい。食事によって吸収が促進されるため、必ず食後に投与。細菌性中耳炎や咽頭炎、皮膚感染症などに適応。下痢や発疹などの副作用に注意。重篤なアレルギー歴がある場合はセフェム系でも慎重投与。', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.09, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 27.0}, # 90mg/kg/日なので0.09g
    {'drug_name': '酸化マグネシウム細粒83%', 'aliases': '酸化マグネシウム', 'type': '下剤', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '腸管からの水分分泌を促して排便を促進する。長期使用で電解質異常（高マグネシウム血症）に注意。乳児にも使用可能で、安全性は比較的高い。牛乳や酸味のある飲料と一緒に服用しない。', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.06, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 2.4}, # 60mg/kg/日なので0.06g
    {'drug_name': 'シングレア細粒4mg', 'aliases': 'モンテルカストナトリウム細粒4 mg「DSEP」', 'type': '抗アレルギー薬（ロイコトリエン受容体拮抗薬）', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 12, 'max_age_months': 71, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '味は甘く服用しやすい。夜間の気管支収縮を抑制。吸入ステロイドと併用されることが多い。まれに興奮・イライラ・不眠などの中枢神経症状に注意が必要。食物と混ぜる場合は水分量に注意し、速やかに服用する。6歳未満', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': '細粒', 'calculated_dose_unit': 'mg', 'daily_dose_per_kg': None, 'daily_fixed_dose': 4.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.0}, # 1.2g/日
    {'drug_name': 'シングレアチュアブル錠5mg', 'aliases': 'モンテルカストナトリウム', 'type': '抗アレルギー薬（ロイコトリエン受容体拮抗薬）', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 72, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '飴状ではないため噛んでから飲み込むことを指導。歯に残るため、就寝前の歯磨きを忘れずに。OD錠ではない。6歳以上', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': '錠', 'calculated_dose_unit': '錠', 'daily_dose_per_kg': None, 'daily_fixed_dose': 1.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 1.0}, # 1錠/日
    {'drug_name': 'セフスパン小児用細粒10%', 'aliases': 'セフィキシムナトリウム細粒100 mg/g', 'type': '抗菌薬（第3世代セフェム系経口）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': '味は比較的良好で、服用しやすい。セフェム系の中でも皮膚感染症や中耳炎などに適応。食事と一緒に服用することで吸収が良好になる。発疹や下痢などの副作用に注意。重篤なペニシリンアレルギー歴がある場合は慎重に使用する。製剤的にはメイアクトと同一成分。\n症状によって増減', 'usage_type': '内服', 'timing_options': '朝夕食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.09, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 7.2}, # 90mg/kg/日なので0.09g
    {'drug_name': 'ゾビラックス顆粒40%', 'aliases': 'アシクロビル顆粒40％', 'type': '抗ウイルス薬（ヘルペスウイルス類）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '4', 'notes': 'できるだけ発疹出現から48時間以内に投与開始が効果的。腎排泄性であり、腎機能障害時は注意が必要。脱水防止も重要。甘味はあるが苦味が残ることもあり、服薬補助の工夫が必要。再発性単純疱疹の抑制には反復投与の必要性あり。', 'usage_type': '内服', 'timing_options': '毎食後眠前', 'formulation_type': '顆粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.2, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 20.0}, # 200mg/kg/日なので0.2g
    {'drug_name': 'カルボシステインシロップ5％', 'aliases': 'カルボシステインシロップ5%', 'type': '去痰薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': None, 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': 'シロップ', 'calculated_dose_unit': 'ml', 'daily_dose_per_kg': 0.6, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.5}, # 600mg/kg/日相当で0.6ml
    {'drug_name': 'カルボシステインドライシロップ50%', 'aliases': 'カルボシステインドライシロップ50%', 'type': '去痰薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '体重30 kgのお子様には標準として、1回0.6 g（カルボシステイン300 mg）を1日3回、総量1.8 g（成分900 mg）を投与します。症状が重い場合には1回0.7〜1.0 g（350〜500 mg）まで増量可ですが、1日総量はおおよそ2.1〜3.0 g（成分1,050〜1,500 mg）を超えない範囲としてください。重大副作用（TEN、肝機能障害、アナフィラキシーなど）や消化器症状にも注意し、異常時には速やかに対応をお願いします', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.06, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 3.0}, # 60mg/kg/日相当で0.06g
    {'drug_name': 'アンブロキソール塩酸塩シロップ小児用0.3％', 'aliases': 'アンブロキソール塩酸塩シロップ小児用0.3％', 'type': '去痰薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '体重30 kgのお子様には、1回9 mL（アンブロキソール塩酸塩27 mg）を1日3回、総量約27 mL（27 g）を目安に用時溶解して投与します。一般的にはこれが標準投与量ですが、症状や耐性を鑑みて増減を行う場合は2〜4日ごとに状態を観察してください。過剰投与による副作用（下痢、腹痛、吐き気など）発生リスクがあるため、慎重に判断してください', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': 'シロップ', 'calculated_dose_unit': 'ml', 'daily_dose_per_kg': 0.9, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 27.0}, # 900mg/kg/日相当で0.9ml
    {'drug_name': 'アンブロキソール塩酸塩DS小児用1.5%', 'aliases': 'アンブロキソール塩酸塩DS小児用1.5%', 'type': '去痰薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '体重30 kgの小児には、1回1.8 g（成分27 mg）を1日3回、総量5.4 g（成分81 mg）を用時に投与します。通常、この標準用量範囲内で十分な去痰効果が期待でき、増量は症状に応じて慎重にご判断ください。重大副作用（ショック、アナフィラキシー、皮膚粘膜眼症候群）発現の可能性があり、投与中は皮膚・呼吸状態に注意し、異常時には速やかに対応をお願いします', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.06, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 5.4}, # 60mg/kg/日相当で0.06g
    {'drug_name': 'アスベリン散10%', 'aliases': 'チペピジンヒベンズ酸塩散10%', 'type': '鎮咳薬', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 0, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': None, 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"0-11\":0.05, \"12-47\":0.18, \"48-83\":0.3, \"84-999\":0.9}', 'max_daily_fixed_dose': 1.2}, # 0.05g, 0.18g, 0.3g, 0.9g
    {'drug_name': '幼児用 PL 配合顆粒', 'aliases': 'サリチルアミド・アセトアミノフェン・無水カフェイン・プロメタジンメチレンジサリチル酸塩配合顆粒', 'type': '解熱鎮痛剤', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 36, 'max_age_months': 143, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '4', 'notes': '体重30 kg程度では、9～11歳相当として**1回3 g、1日4回（総量12 g／日）**が標準量です。ただし、アセトアミノフェンを含むため、重篤な肝障害リスクやサリチル酸系による出血傾向に注意し、同類の薬剤との併用を避けてください。2歳未満には禁忌となりますので、ご注意願います。', 'usage_type': '内服', 'timing_options': '毎食後眠前', 'formulation_type': '顆粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"36-59\":4.0, \"60-107\":8.0, \"108-143\":12.0}', 'max_daily_fixed_dose': 13.0}, # 4g/日, 8g/日, 12g/日
    {'drug_name': 'アルピニー坐剤100mg', 'aliases': 'アセトアミノフェン坐剤100 mg', 'type': '解熱鎮痛剤', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '1回あたり注意。坐剤のため、個数計算必要', 'usage_type': '頓服', 'timing_options': '発熱時', 'formulation_type': '坐剤', 'calculated_dose_unit': 'mg', 'daily_dose_per_kg': 30.0, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 1800.0}, # 30mg/kg/日
    {'drug_name': 'レボセチリジン塩酸塩ドライシロップ0.5％', 'aliases': 'レボセチリジン塩酸塩ドライシロップ0.5％', 'type': '抗アレルギー薬（第2世代抗ヒスタミン薬）', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 6, 'max_age_months': 191, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1,2', 'notes': '6ヵ月以上1歳未満の小児には1回0.25g（レボセチリジン塩酸塩として1.25mg）を1日1回、用時溶解して経口投与する', 'usage_type': '内服', 'timing_options': '眠前,朝食後眠前', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"6-11\":0.25, \"12-95\":0.5, \"96-191\":1.0}', 'max_daily_fixed_dose': 2.0}, # 0.25g, 0.5g, 1.0g
    {'drug_name': 'フェキソフェナジン塩酸塩DS5%', 'aliases': 'フェキソフェナジン塩酸塩DS5%', 'type': '第二世代抗ヒスタミン薬', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 60, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': None, 'usage_type': '内服', 'timing_options': '朝眠前', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"60-359\":0.6, \"360-999\":1.2}', 'max_daily_fixed_dose': 2.5}, # 0.6g, 1.2g
    {'drug_name': 'アレグラ錠60mg', 'aliases': 'フェキソフェナジン塩酸塩錠60mg', 'type': '第二世代抗ヒスタミン薬', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 108, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': None, 'usage_type': '内服', 'timing_options': '朝眠前', 'formulation_type': '錠', 'calculated_dose_unit': 'mg', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"108-155\":60.0, \"156-999\":120.0}', 'max_daily_fixed_dose': 180.0}, # 60mg, 120mg
    {'drug_name': 'クラリチンドライシロップ1％', 'aliases': 'ロラタジンドライシロップ1%', 'type': '抗アレルギー薬', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 48, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': 'クラリチン®ドライシロップは1日1回で済む服用回数の少なさが小児にとって大きな利点です。また、甘味があり飲みやすく調製されており、粉薬が苦手なお子さんにも比較的受け入れられやすい剤形です。水で溶かして速やかに服用するよう保護者へも指導をお願いします。副作用としては眠気が少なく、学童期の集中力への影響も最小限ですが、長期連用時は効果の評価を行ってください', 'usage_type': '内服', 'timing_options': '夕食後', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"48-95\":0.5, \"96-999\":1.0}', 'max_daily_fixed_dose': 1.1}, # 0.5g, 1.0g
    {'drug_name': 'メプチンシロップ5μg/ml', 'aliases': 'プロカテロール塩酸塩水和物シロップ5μg/mL', 'type': '気管支拡張薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': '5ml以上は適宜確認して下さい\nメプチンシロップは1回5 mL×1〜2回/日とシンプルかつ用法が少なく、小児にとって服用しやすい点が大きな利点です。甘味が強すぎず、量も少なめなので嫌がらずに飲ませやすく、親御さんの管理もしやすいです。ただし、β₂刺激薬により動悸や振戦、頻脈の副作用が出やすいため、初回使用時や増量時には注意が必要です。使用中に心拍数の変化や振戦がある場合には、できるだけ少量からスタートするか、服用タイミングを調整するなど配慮をお願いします。使用が長引く場合には、喘息発作時の吸入リリーバー（短時間作用型β₂作動薬）の使用指導も併せて行ったほうが安心です。', 'usage_type': '内服', 'timing_options': '朝眠前', 'formulation_type': 'シロップ', 'calculated_dose_unit': 'ml', 'daily_dose_per_kg': 0.5, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 20.0}, # 0.5ml/kg/日
    {'drug_name': 'メプチンDS0.005%', 'aliases': 'プロカテロール塩酸塩水和物ドライシロップ0.005%', 'type': '気管支拡張薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': 'メプチンDSは、1回0.5 g（25 μg）を用時溶解で1～2回/日と、服薬回数と量がシンプルな点が小児にとって大きなメリットです。甘味があり飲みやすく、少量で済むため服薬を嫌がるお子様でも比較的受け入れやすい剤形です。ただしβ₂刺激薬の特性上、**初回投与時や増量時に動悸や振戦が現れることがあるため、少量から開始して状態をよく観察してください。特に心拍数の変化がある場合は間隔の調整や減量も検討を。使用が長期化する場合には、吸入ステロイド等との併用・吸入リリーバーの併用指導を併せて行うと安心です。', 'usage_type': '内服', 'timing_options': '朝眠前', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.05, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 1.0}, # 0.05g/kg/日
    {'drug_name': 'メプチンエアー10μg吸入100回', 'aliases': 'プロカテロール塩酸塩水和物エアゾール10 μg吸入100回', 'type': '気管支拡張薬', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '4', 'notes': None, 'usage_type': '頓服', 'timing_options': '発作時', 'formulation_type': 'キット', 'calculated_dose_unit': '回', 'daily_dose_per_kg': None, 'daily_fixed_dose': 4.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.0}, # 4回/日
    {'drug_name': 'ミヤBM細粒', 'aliases': '宮入菌末細粒40 mg/g', 'type': '整腸剤', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '添付文書に小児の記載なし', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.6, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 3.0}, # 0.6g/kg/日
    {'drug_name': 'ラックビーR散', 'aliases': '耐性乳酸菌製剤', 'type': '整腸剤', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '添付文書に小児の記載なし', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '散', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.21, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 3.0}, # 0.21g/kg/日
    {'drug_name': 'セルベックス細粒10%', 'aliases': 'テプレノン細粒10%', 'type': '防御因子増強薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '添付文書に小児の記載なし', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.09, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.5}, # 0.09g/kg/日
    {'drug_name': 'ビオフェルミン配合散', 'aliases': 'ビオフェルミン配合散', 'type': '整腸剤', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '生菌剤ですので開封後の湿気に注意し、できるだけ早く使用してください。消化器症状が強い場合は、量を上限（2.16 g/10 kg/日）としながら経過を確認し、効果不十分な場合は診療科へご相談をおすすめします。', 'usage_type': '内服', 'timing_options': '毎食後', 'formulation_type': '散', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.18, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 9.0}, # 0.18g/kg/日
    {'drug_name': 'モビコール配合内用剤LD', 'aliases': 'マクロゴール4000塩化ナトリウム・炭酸水素ナトリウム・塩化カリウム混合製剤', 'type': '便秘症改善薬', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 36, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '効果発現には2日程度かかる目安です。増量は2日以上間隔をあけて行い、便の状態を確認しながら漸増してください。腹痛や下痢がみられた場合は速やかに減量や中止の検討をお願いします。水分摂取を十分に促してください。', 'usage_type': '内服', 'timing_options': '食後', 'formulation_type': '配合剤', 'calculated_dose_unit': '包', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"36-95\":1.0, \"96-155\":2.0, \"156-999\":2.0}', 'max_daily_fixed_dose': 4.0}, # 1包, 2包
    {'drug_name': 'モビコール配合内用剤HD', 'aliases': 'マクロゴール4000塩化ナトリウム・炭酸水素ナトリウム・塩化カリウム混合製剤', 'type': '便秘症改善薬', 'dosage_unit': 'age', 'dose_per_kg': None, 'min_age_months': 36, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': None, 'usage_type': '内服', 'timing_options': '食後', 'formulation_type': '配合剤', 'calculated_dose_unit': '包', 'daily_dose_per_kg': None, 'daily_fixed_dose': None, 'daily_dose_age_specific': '{\"36-95\":1.0, \"96-155\":1.0, \"156-999\":1.0}', 'max_daily_fixed_dose': 3.0}, # 1包
    {'drug_name': 'ナウゼリンドライシロップ1%', 'aliases': 'ドンペリドンドライシロップ1%', 'type': '抗ドパミン薬', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '3', 'notes': '小児では1日1.0〜2.0 mg/kgを3回に分けて食前に服用しますが、6歳以上では最大1.0 mg/kg/日までとし、1日30 mgを超えないよう注意ください。特に乳幼児には錐体外路症状や意識障害のリスクがありますので、3歳以下での長期連用（7日以上）は避けてください。副作用の発現時には減量または中止の検討をお願いします。', 'usage_type': '内服', 'timing_options': '食前', 'formulation_type': 'ドライシロップ', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.002, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 0.03}, # 2mg/kg/日なので0.002g, 最大30mg/日なので0.03g
    {'drug_name': 'シングレア細粒4mg', 'aliases': 'モンテルカストナトリウム細粒4 mg「DSEP」', 'type': '抗アレルギー薬（ロイコトリエン受容体拮抗薬）', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 0, 'max_age_months': 23, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '味は甘く服用しやすい。夜間の気管支収縮を抑制。吸入ステロイドと併用されることが多い。まれに興奮・イライラ・不眠などの中枢神経症状に注意が必要。食物と混ぜる場合は水分量に注意し、速やかに服用する。6歳未満', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': '細粒', 'calculated_dose_unit': 'mg', 'daily_dose_per_kg': None, 'daily_fixed_dose': 4.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 4.0}, # 4mg/日, 最大4mg/日
    {'drug_name': 'シングレアチュアブル錠5mg', 'aliases': 'モンテルカストナトリウム', 'type': '抗アレルギー薬（ロイコトリエン受容体拮抗薬）', 'dosage_unit': 'fixed', 'dose_per_kg': None, 'min_age_months': 72, 'max_age_months': 999, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '1', 'notes': '飴状ではないため噛んでから飲み込むことを指導。歯に残るため、就寝前の歯磨きを忘れずに。OD錠ではない。6歳以上', 'usage_type': '内服', 'timing_options': '眠前', 'formulation_type': '錠', 'calculated_dose_unit': '錠', 'daily_dose_per_kg': None, 'daily_fixed_dose': 1.0, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 1.0}, # 1錠/日, 最大1錠/日
    {'drug_name': 'セフスパン小児用細粒10%', 'aliases': 'セフィキシムナトリウム細粒100 mg/g', 'type': '抗菌薬（第3世代セフェム系経口）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '2', 'notes': '味は比較的良好で、服用しやすい。セフェム系の中でも皮膚感染症や中耳炎などに適応。食事と一緒に服用することで吸収が良好になる。発疹や下痢などの副作用に注意。重篤なペニシリンアレルギー歴がある場合は慎重に使用する。製剤的にはメイアクトと同一成分。\n症状によって増減', 'usage_type': '内服', 'timing_options': '朝夕食後', 'formulation_type': '細粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.09, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 7.2}, # 90mg/kg/日なので0.09g
    {'drug_name': 'ゾビラックス顆粒40%', 'aliases': 'アシクロビル顆粒40％', 'type': '抗ウイルス薬（ヘルペスウイルス類）', 'dosage_unit': 'kg', 'dose_per_kg': None, 'min_age_months': None, 'max_age_months': None, 'dose_age_specific': None, 'fixed_dose': None, 'daily_frequency': '4', 'notes': 'できるだけ発疹出現から48時間以内に投与開始が効果的。腎排泄性であり、腎機能障害時は注意が必要。脱水防止も重要。甘味はあるが苦味が残ることもあり、服薬補助の工夫が必要。再発性単純疱疹の抑制には反復投与の必要性あり。', 'usage_type': '内服', 'timing_options': '毎食後眠前', 'formulation_type': '顆粒', 'calculated_dose_unit': 'g', 'daily_dose_per_kg': 0.2, 'daily_fixed_dose': None, 'daily_dose_age_specific': None, 'max_daily_fixed_dose': 20.0}, # 200mg/kg/日なので0.2g
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
        # カーソル作成。PostgreSQLの場合は psycopg2.extras.DictCursor を使用
        if DATABASE_URL:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 
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