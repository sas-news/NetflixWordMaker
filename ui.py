import requests
from datetime import datetime
import ipywidgets as widgets
from IPython.display import display, clear_output, Markdown

# GitHub APIを使用してsrtフォルダ内のファイル数を取得し、その数を返す
def get_srt_files_count(repo_url):
    response = requests.get(repo_url)
    if response.status_code == 200:
        items = response.json()
        # typeが'file'のもの（ファイル）の数をカウントして返す
        files_count = sum(1 for item in items if item['type'] == 'file')
        return files_count
    else:
        print("Error fetching file count:", response.status_code)
        return 0

def get_srt_folders(repo_url):
  response = requests.get(repo_url)
  if response.status_code == 200:
      items = response.json()
      # typeが'dir'のもの（ディレクトリ）の名前をリストにして返す
      folders = [item['name'] for item in items if item['type'] == 'dir']
      return folders
  else:
      print("Error fetching folders:", response.status_code)
      return []

# srtフォルダ内のフォルダ名を取得
srt_folders_url = 'https://api.github.com/repos/sas-news/NetflixWordMaker/contents/srt/'
folders = get_srt_folders(srt_folders_url)

title_dropdown = widgets.Dropdown(
    options=folders,
    description='タイトル:',
)

# 日付入力欄の数を調整するスライダー
date_pickers_slider = widgets.IntSlider(
    value=1,
    min=1,
    max=10,  # 例として最大値を10に設定
    step=1,
    description='日付:',
)

srt_files_count = 0

def on_title_change(change=None):
    global srt_files_count
    clear_output(wait=True)
    display(title_dropdown)
    if change:
        selected_title = change['new']
    else:
        selected_title = title_dropdown.value
    repo_url = f'https://api.github.com/repos/sas-news/NetflixWordMaker/contents/srt/{selected_title}'
    srt_files_count = get_srt_files_count(repo_url)
    date_pickers_slider.max = 20
    display(date_pickers_slider)
    on_slider_change()  # srt_files_countはグローバル変数として扱われる

def on_slider_change(change=None):
    global srt_files_count
    clear_output(wait=True)
    display(title_dropdown)
    display(Markdown(f"話数: {srt_files_count}"))
    display(date_pickers_slider)
    if change:
        num_date_pickers = change['new']
    else:
        num_date_pickers = date_pickers_slider.value
    # DatePickerとTextウィジェットをHBoxを使って横並びに表示
    for i in range(num_date_pickers):
        date_picker = widgets.DatePicker(description=f'日付 {i+1}:')
        time_input = widgets.Text(value='00:00', description=f'時間 {i+1}:', placeholder='HH:MM')
        hbox = widgets.HBox([date_picker, time_input])  # HBoxでウィジェットを横並びに配置
        display(hbox)

# タイトル選択の変更を監視
title_dropdown.observe(on_title_change, names='value')

# スライダーの値の変更を監視
date_pickers_slider.observe(on_slider_change, names='value')

# 初期表示
on_title_change()