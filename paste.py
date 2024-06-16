import tkinter as tk
from tkinter import messagebox
import pyautogui
import time

def repeat_text():
    # テキストボックスからテキストを取得
    text = text_entry.get("1.0", "end-1c")

    # 入力が空であればエラーメッセージを表示して終了
    if not text:
        messagebox.showerror("Error", "Please enter some text.")
        return

    # テキストの行数を数える
    num_lines = text.count('\n') + 1

    # カウントダウン
    time.sleep(5)

    # テキストを1行ずつ処理
    for i in range(num_lines):
        # クリップボードに現在の行をコピー
        line_start = text_entry.index(f"{i+1}.0")
        line_end = text_entry.index(f"{i+1}.end")
        line_text = text_entry.get(line_start, line_end)
        pyautogui.write(line_text.strip())  # 改行を削除してテキストを貼り付け
        pyautogui.press('enter')  # Enterキーを押す

        # 少し待つ（必要に応じて調整）
        time.sleep(0.7)

# GUIウィンドウの作成
root = tk.Tk()
root.title("Text Repeater")

# テキスト入力用のテキストボックス
text_label = tk.Label(root, text="Enter text:")
text_label.pack()
text_entry = tk.Text(root, height=5, width=40)
text_entry.pack()

# リピートテキストボタン
repeat_button = tk.Button(root, text="Repeat Text", command=repeat_text)
repeat_button.pack()

# GUIループの開始
root.mainloop()
