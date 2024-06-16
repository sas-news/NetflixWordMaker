import os
import re
import json
import csv
from datetime import datetime, timedelta
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from wordfreq import zipf_frequency
import random

# 必要なNLTKデータのダウンロード
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')

def read_srt_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_subtitle_texts(srt_content):
    subtitle_texts = re.findall(r'\d+\n\d+:\d+:\d+,\d+ --> \d+:\d+:\d+,\d+\n(.*?)\n\n', srt_content, re.DOTALL)
    return subtitle_texts

def extract_subtitle_times(srt_content):
    """
    字幕ファイルの内容から時間情報を抽出し、それを開始時間と終了時間のペアのリストとして返す。
    """
    time_pairs = re.findall(r'(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)', srt_content)
    return time_pairs

def remove_html_tags(text):
    clean_text = re.sub(r'<.*?>', '', text)
    clean_text = clean_text.replace('\n', ' ')
    return clean_text

global_difficult_words = {} 

# WordNetLemmatizerのインスタンスを作成
lemmatizer = WordNetLemmatizer()

def get_wordnet_pos(treebank_tag):
    """Treebank POSタグをWordNet POSタグに変換"""
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return None

def srt_time_to_seconds(srt_time):
    """SRT形式の時間を秒数に変換"""
    hours, minutes, seconds = map(float, re.split('[:,]', srt_time)[:3])
    return hours * 3600 + minutes * 60 + seconds

def extract_difficult_words(sentence, start_time_seconds, min_level, prob_threshold=0.3, word_time=0.75):
    global global_difficult_words
    # start_time_seconds が float 型でない場合のみ変換を行う
    if not isinstance(start_time_seconds, float):
        start_time_seconds = srt_time_to_seconds(start_time_seconds)  # 字幕の開始時間を秒数に変換
    words = nltk.word_tokenize(sentence)
    tagged_words = nltk.pos_tag(words)

    for word, tag in tagged_words:
        wn_tag = get_wordnet_pos(tag)
        if wn_tag:
            lemma = lemmatizer.lemmatize(word, pos=wn_tag)
        else:
            lemma = lemmatizer.lemmatize(word)

        zipf_value = zipf_frequency(lemma, 'en')
        if zipf_value < min_level:
            if random.random() < prob_threshold:
                lemma_lower = lemma.lower()
                if lemma_lower in global_difficult_words:
                    global_difficult_words[lemma_lower]['count'] += 1
                else:
                    synonyms = wordnet.synsets(lemma_lower)
                    if synonyms:
                        definition = synonyms[0].definition()
                        # 単語が登録される時刻を計算
                        adjusted_start_time_seconds = start_time_seconds + (word_time * len(global_difficult_words))
                        global_difficult_words[lemma_lower] = {
                            'word': lemma_lower,
                            'definition': definition,
                            'sentence': sentence,
                            'start_time_seconds': adjusted_start_time_seconds,  # 単語が取得された時間を更新
                            'count': 1
                        }

def print_data_to_csv(csv_file_path, title, start_datetime):
    global global_difficult_words
    with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date Added', 'Frequency', 'Word/Expression', 'Definition', 'Source', 'Context', 'Notes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        for word, info in global_difficult_words.items():
            added_seconds = info['start_time_seconds']
            date_added = start_datetime + timedelta(seconds=added_seconds)
            writer.writerow({
                'Date Added': date_added.strftime('%Y/%m/%d %H:%M:%S'),
                'Frequency': info['count'],
                'Word/Expression': word,
                'Definition': info['definition'],
                'Source': title,
                'Context': info['sentence'],
                'Notes': ''
            })

def process_srt_files(folder_path, output_csv_path, min_level, title, start_datetime):
    accumulated_seconds = 0  # 加算される秒数を保持する変数
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.srt'):
            srt_file_path = os.path.join(folder_path, file_name)
            srt_content = read_srt_file(srt_file_path)
            subtitle_texts = extract_subtitle_texts(srt_content)
            time_pairs = extract_subtitle_times(srt_content)
            if time_pairs:
                # 最後の字幕の終了時間を取得し、秒数に変換
                last_end_time_srt = time_pairs[-1][1]
                last_end_time_seconds = srt_time_to_seconds(last_end_time_srt)
                # 現在のファイルの終了時間を次のファイルの開始時間として加算
                accumulated_seconds += last_end_time_seconds
            for index, subtitle_text in enumerate(subtitle_texts):
                clean_text = remove_html_tags(subtitle_text)
                start_time_srt = time_pairs[index][0]
                start_time_seconds = srt_time_to_seconds(start_time_srt) + accumulated_seconds  # 加算された時間を考慮
                extract_difficult_words(clean_text, start_time_seconds, min_level, 0.3, word_time)  # 第2引数を start_time_seconds として渡す

    print_data_to_csv(output_csv_path, title, start_datetime)

title = 'One Piece'
folder_path = f'srt/{title}'
output_csv_path = 'output.csv'
min_level = 2.9  # 難しい単語とみなすZipfスケールの最大値を指定
start_datetime = datetime.now()  # 開始日時を現在の日時に設定
word_time = 0.75

# CSVファイルのヘッダーを書き込む
with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Date Added', 'Frequency', 'Word/Expression', 'Definition', 'Source', 'Context', 'Notes']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

# 実行部分の修正
process_srt_files(folder_path, output_csv_path, min_level, title, start_datetime)