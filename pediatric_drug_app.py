import tkinter as tk
from tkinter import ttk # ttkモジュールは、よりモダンな見た目のウィジェットを提供します
import sqlite3
import json

# --- データベース関連関数（以前のスクリプトから抜粋） ---
def get_db_connection():
    conn = sqlite3.connect('drug_data.db')
    conn.row_factory = sqlite3.Row # これにより、カラム名をキーとしてデータにアクセスできるようになります
    return conn

# --- メインアプリケーションクラス ---
class PediatricDrugApp:
    def __init__(self, root):
        self.root = root
        self.root.title("小児薬 用法用量検索ツール")
        self.root.geometry("800x600")

        # レイアウトのためのフレームを作成
        # アプリケーション全体を構造化するために使います
        self.main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # グリッドレイアウトの設定
        # 各列の幅を自動調整するために重み付けをします
        self.main_frame.columnconfigure(1, weight=1) # 2列目を広がるように設定

        # --- 薬名検索エリア ---
        ttk.Label(self.main_frame, text="薬名検索:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.drug_name_entry = ttk.Entry(self.main_frame, width=50)
        self.drug_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        # 後で予測検索（オートコンプリート）機能をここに追加します

        self.search_drug_button = ttk.Button(self.main_frame, text="薬を検索")
        self.search_drug_button.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 検索結果を表示するリストボックス
        ttk.Label(self.main_frame, text="検索結果:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.drug_listbox = tk.Listbox(self.main_frame, height=8, width=70)
        self.drug_listbox.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # スクロールバー
        self.listbox_scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.drug_listbox.yview)
        self.listbox_scrollbar.grid(row=1, column=3, sticky=(tk.N, tk.S, tk.W))
        self.drug_listbox.config(yscrollcommand=self.listbox_scrollbar.set)


        # --- 薬の種類で検索エリア ---
        ttk.Label(self.main_frame, text="薬の種類:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.drug_type_combobox = ttk.Combobox(self.main_frame, width=47,
                                                values=["解熱鎮痛剤", "抗生剤", "鎮咳薬", "去痰薬", "ステロイド", "その他"]) # サンプルでいくつか種類を定義
        self.drug_type_combobox.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        self.search_type_button = ttk.Button(self.main_frame, text="種類で検索")
        self.search_type_button.grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)


        # --- 患者情報入力エリア ---
        ttk.Label(self.main_frame, text="患者体重 (kg):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.patient_weight_entry = ttk.Entry(self.main_frame, width=10)
        self.patient_weight_entry.grid(row=3, column=1, sticky=tk.W, pady=5)

        ttk.Label(self.main_frame, text="患者年齢 (ヶ月):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.patient_age_entry = ttk.Entry(self.main_frame, width=10)
        self.patient_age_entry.grid(row=4, column=1, sticky=tk.W, pady=5)

        # --- 用法用量表示エリア ---
        ttk.Label(self.main_frame, text="計算結果:").grid(row=5, column=0, sticky=tk.W, pady=10)
        self.result_text = tk.Text(self.main_frame, height=5, width=60, wrap=tk.WORD) # wrap=tk.WORD で単語単位で改行
        self.result_text.grid(row=5, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # コピーボタン
        self.copy_button = ttk.Button(self.main_frame, text="結果をコピー")
        self.copy_button.grid(row=6, column=1, sticky=tk.E, pady=5)

        # --- イベントバインディング（後で関数を割り当てます） ---
        self.search_drug_button.config(command=self.search_drugs)
        self.search_type_button.config(command=self.search_by_type)
        self.drug_listbox.bind('<<ListboxSelect>>', self.on_drug_select) # リストボックス選択時にイベントを発生
        self.copy_button.config(command=self.copy_result_to_clipboard)

        # 初期表示のために、すべての薬をリストボックスに表示
        self.display_all_drugs()


    def search_drugs(self):
        """薬名（部分一致または別名）で薬を検索し、リストボックスに表示する"""
        search_term = self.drug_name_entry.get().strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # drug_name または aliases に部分一致するものを検索
        query = """
            SELECT drug_name FROM drugs
            WHERE drug_name LIKE ? OR aliases LIKE ?
            ORDER BY drug_name
        """
        cursor.execute(query, (f'%{search_term}%', f'%{search_term}%'))
        
        results = cursor.fetchall()
        conn.close()

        self.drug_listbox.delete(0, tk.END) # 現在のリストをクリア
        if results:
            for row in results:
                self.drug_listbox.insert(tk.END, row['drug_name'])
        else:
            self.drug_listbox.insert(tk.END, "該当する薬が見つかりませんでした。")

    def search_by_type(self):
        """薬の種類で薬を検索し、リストボックスに表示する"""
        selected_type = self.drug_type_combobox.get().strip()
        if not selected_type:
            self.display_all_drugs() # 種類が選択されていなければ全件表示
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT drug_name FROM drugs WHERE type = ? ORDER BY drug_name"
        cursor.execute(query, (selected_type,))
        
        results = cursor.fetchall()
        conn.close()

        self.drug_listbox.delete(0, tk.END)
        if results:
            for row in results:
                self.drug_listbox.insert(tk.END, row['drug_name'])
        else:
            self.drug_listbox.insert(tk.END, "該当する薬が見つかりませんでした。")

    def display_all_drugs(self):
        """すべての薬をリストボックスに表示する"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT drug_name FROM drugs ORDER BY drug_name")
        results = cursor.fetchall()
        conn.close()

        self.drug_listbox.delete(0, tk.END)
        for row in results:
            self.drug_listbox.insert(tk.END, row['drug_name'])


    def on_drug_select(self, event):
        """リストボックスで薬が選択されたときに用量を計算・表示する"""
        selected_indices = self.drug_listbox.curselection()
        if not selected_indices:
            return

        selected_drug_name = self.drug_listbox.get(selected_indices[0])
        self.calculate_and_display_dosage(selected_drug_name)

    def calculate_and_display_dosage(self, drug_name):
        """選択された薬、体重、年齢に基づいて用量を計算し、表示エリアに表示する"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drugs WHERE drug_name = ?", (drug_name,))
        drug_info = cursor.fetchone()
        conn.close()

        self.result_text.delete(1.0, tk.END) # 結果表示エリアをクリア

        if not drug_info:
            self.result_text.insert(tk.END, "薬の情報が見つかりません。")
            return

        try:
            patient_weight = float(self.patient_weight_entry.get()) if self.patient_weight_entry.get() else 0.0
            patient_age_months = int(self.patient_age_entry.get()) if self.patient_age_entry.get() else -1
        except ValueError:
            self.result_text.insert(tk.END, "体重または年齢の入力が不正です。数値を入力してください。")
            return

        dosage_output = f"薬名: {drug_info['drug_name']}\n"
        calculated_dose = None

        if drug_info['dosage_unit'] == 'kg':
            if patient_weight > 0 and drug_info['dose_per_kg'] is not None:
                calculated_dose = patient_weight * drug_info['dose_per_kg']
                dosage_output += f"1回量: 約{calculated_dose:.3f}g\n"
            else:
                dosage_output += "1回量: 体重が入力されていないか、用量データがありません。\n"
        elif drug_info['dosage_unit'] == 'age':
            if patient_age_months >= 0 and drug_info['dose_age_specific']:
                age_doses = json.loads(drug_info['dose_age_specific'])
                found_dose = False
                for age_range_str, dose in age_doses.items():
                    min_age, max_age = map(int, age_range_str.split('-'))
                    if min_age <= patient_age_months <= max_age:
                        calculated_dose = dose
                        dosage_output += f"1回量: 約{calculated_dose:.1f}ml (年齢基準)\n"
                        found_dose = True
                        break
                if not found_dose:
                    dosage_output += "1回量: この年齢に対する用量が見つかりません。\n"
            else:
                dosage_output += "1回量: 年齢が入力されていないか、年齢基準の用量データがありません。\n"
        elif drug_info['dosage_unit'] == 'fixed':
            if drug_info['fixed_dose'] is not None:
                calculated_dose = drug_info['fixed_dose']
                dosage_output += f"1回量: {calculated_dose}ml (固定用量)\n"
            else:
                dosage_output += "1回量: 固定用量データがありません。\n"
        else:
            dosage_output += "用量計算の基準が不明です。\n"

        # 1日の投与回数の表示
        if drug_info['daily_frequency']:
            frequencies = drug_info['daily_frequency'].split(',')
            freq_str = ", ".join([f"1日{f}回" for f in frequencies])
            dosage_output += f"1日の投与回数候補: {freq_str}\n"
        else:
            dosage_output += "1日の投与回数候補: 不明\n"

        if drug_info['notes']:
            dosage_output += f"備考: {drug_info['notes']}\n"

        self.result_text.insert(tk.END, dosage_output)


    def copy_result_to_clipboard(self):
        """結果表示エリアのテキストをクリップボードにコピーする"""
        text_to_copy = self.result_text.get(1.0, tk.END).strip() # 最初の文字から最後の文字まで取得
        if text_to_copy:
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.root.update() # クリップボードへの反映を強制

# --- アプリケーションの実行 ---
if __name__ == "__main__":
    # データベースが作成されていることを確認
    # create_db.py と insert_sample_data.py を先に実行しておく必要があります
    # ここでは便宜上、get_db_connectionを呼んでいますが、DBが存在しないとエラーになります
    # 最初に create_db.py と insert_sample_data.py を実行してください。

    app_root = tk.Tk()
    app = PediatricDrugApp(app_root)
    app_root.mainloop()