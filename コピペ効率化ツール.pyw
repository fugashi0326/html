import tkinter as tk
from tkinter import messagebox
import json
import os


# 拡張ライブラリのインポートチェック
try:
    from tkinterdnd2 import DND_TEXT, TkinterDnD
except ImportError:
    messagebox.showerror("エラー", "ライブラリが見つかりません。\n'pip install tkinterdnd2' を実行してください。")
    exit()

SETTINGS_FILE = "settings.json"

class CopyPasteTool:
    def __init__(self, root):
        self.root = root
        self.root.title("無限コピペツール")
        self.root.geometry("420x400") # スクロールバーの分少し幅広に
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- 全体のレイアウト構成 ---
        
        # 1. 下部（追加ボタン）エリア
        # ※packは下から順に配置するとレイアウト崩れしにくい
        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.add_button = tk.Button(self.bottom_frame, text="＋ 行を追加", command=lambda: self.add_row(), bg="#dddddd")
        self.add_button.pack(fill=tk.X)

        # 2. メインエリア（Canvas + Scrollbar）
        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        
        # キャンバスの中に「行を並べるためのフレーム(inner_frame)」を配置
        self.scrollable_frame = tk.Frame(self.canvas)

        # スクロール動作の設定
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # キャンバスの中にフレームを描画
        self.canvas_frame_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # キャンバス自体のリサイズに合わせて内部フレームの幅を調整
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # マウスホイールでスクロールできるようにする
        self.bind_mouse_scroll(self.canvas)
        self.bind_mouse_scroll(self.scrollable_frame)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # データの読み込み
        self.load_settings()

    def on_canvas_configure(self, event):
        """ウィンドウサイズ変更時に中のフレーム幅を合わせる"""
        self.canvas.itemconfig(self.canvas_frame_id, width=event.width)

    def bind_mouse_scroll(self, widget):
        """マウスホイールイベントをバインド（Windows/Mac対応）"""
        widget.bind_all("<MouseWheel>", self.on_mousewheel)
        # Linuxなどは <Button-4>, <Button-5> の場合があるが今回はWindows想定

    def on_mousewheel(self, event):
        """マウスホイールの処理"""
        # スクロール可能な範囲がある場合のみスクロール
        if self.canvas.bbox("all")[3] > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def add_row(self, initial_text=""):
        # 行は self.scrollable_frame に追加していく
        row_frame = tk.Frame(self.scrollable_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # 1. 削除ボタン (左)
        btn_delete = tk.Button(row_frame, text="×", width=3, fg="red", command=lambda: self.delete_row(row_frame))
        btn_delete.pack(side=tk.LEFT, padx=(0, 5))

        # 2. ハンドル (右)
        lbl_handle = tk.Label(row_frame, text="≡", cursor="hand2", width=4, bg="#e0e0e0", relief="raised")
        lbl_handle.pack(side=tk.RIGHT, padx=(5, 0))

        # 3. テキストボックス
        entry = tk.Entry(row_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.insert(0, initial_text)

        # ハンドル設定
        self.setup_handle(lbl_handle, entry)
        
        # 追加したとき一番下までスクロールしてあげる（お好みで）
        self.root.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def setup_handle(self, handle_widget, entry_widget):
        handle_widget.drag_source_register(1, DND_TEXT)

        def on_action(event=None):
            text = entry_widget.get()
            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update()
                
                original_bg = handle_widget.cget("bg")
                handle_widget.config(bg="#aaffaa")
                self.root.after(200, lambda: handle_widget.config(bg=original_bg))
            
            return ('copy', DND_TEXT, text)

        handle_widget.dnd_bind('<<DragInitCmd>>', on_action)
        handle_widget.bind("<Button-1>", on_action)

    def delete_row(self, frame_widget):
        frame_widget.destroy()
        # 削除後にスクロール範囲を再計算させる
        self.root.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "geometry" in data:
                    self.root.geometry(data["geometry"])
                saved_texts = data.get("texts", [])
                if saved_texts:
                    for text in saved_texts:
                        self.add_row(text)
                else:
                    self.add_row()
            except Exception:
                self.add_row()
        else:
            self.add_row()

    def on_close(self):
        geometry = self.root.geometry()
        texts = []
        # scrollable_frame の中を探すように変更
        for row in self.scrollable_frame.winfo_children():
            for widget in row.winfo_children():
                if isinstance(widget, tk.Entry):
                    texts.append(widget.get())
                    break
        
        save_data = {"geometry": geometry, "texts": texts}
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = CopyPasteTool(root)
    root.mainloop()