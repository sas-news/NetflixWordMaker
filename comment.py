import base64
import os
import re
import csv
from datetime import datetime, timedelta
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from wordfreq import zipf_frequency
import random
import requests

nltk.download('punkt')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')

def read_srt_file_from_github(repo, path, file_name):
    url = f'https://api.github.com/repos/{repo}/contents/{path}/{file_name}'
    response = requests.get(url)
    if response.status_code == 200:
        content = response.json()['content']
        srt_content = base64.b64decode(content).decode('utf-8')
        return srt_content
    else:
        print(f"Error fetching {file_name}: {response.status_code}")
        return None
def read_srt_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_subtitle_texts(srt_content):
    subtitle_texts = re.findall(r'\d+\n\d+:\d+:\d+,\d+ --> \d+:\d+:\d+,\d+\n(.*?)\n\n', srt_content, re.DOTALL)
    return subtitle_texts

def extract_subtitle_times(srt_content):
    time_pairs = re.findall(r'(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)', srt_content)
    return time_pairs

def remove_html_tags(text):
    clean_text = re.sub(r'<.*?>', '', text)
    clean_text = clean_text.replace('\n', ' ')
    return clean_text

global_difficult_words = {}

lemmatizer = WordNetLemmatizer()

def get_wordnet_pos(treebank_tag):
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
    hours, minutes, seconds = map(float, re.split('[:,]', srt_time)[:3])
    return hours * 3600 + minutes * 60 + seconds

def extract_difficult_words(sentence, start_time_seconds, min_level, prob_threshold=0.3, word_time=0.75, segment_index=0):
    global global_difficult_words
    
    if not isinstance(start_time_seconds, float):
        start_time_seconds = srt_time_to_seconds(start_time_seconds)
    words = nltk.word_tokenize(sentence)
    tagged_words = nltk.pos_tag(words)

    added_word_count = 0  # CSVに追加された単語の数をカウント

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
                        adjusted_start_time_seconds = start_time_seconds + (added_word_count * word_time * 60)  # 分単位を秒単位に変換
                        global_difficult_words[lemma_lower] = {
                            'word': lemma_lower,
                            'definition': definition,
                            'sentence': sentence,
                            'start_time_seconds': adjusted_start_time_seconds,
                            'count': 1,
                            'segment_index': segment_index
                        }
                        added_word_count += 1  # CSVに追加された単語の数をカウント

    return added_word_count  # CSVに追加された単語の数を返す

def print_data_to_csv(csv_file_path, title, datetime_segments):
    global global_difficult_words
    with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date Added', 'Frequency', 'Word/Expression', 'Definition', 'Source', 'Context', 'Notes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        for word, info in global_difficult_words.items():
            base_datetime = datetime_segments[info['segment_index']]
            word_datetime = base_datetime + timedelta(seconds=info['start_time_seconds'])
            writer.writerow({
                'Date Added': word_datetime.strftime('%Y/%m/%d %H:%M:%S'),
                'Frequency': info['count'],
                'Word/Expression': f'=HYPERLINK("https://www.oxfordlearnersdictionaries.com/definition/english/{word}", "{word}")',
                'Definition': info['definition'],
                'Source': title,
                'Context': info['sentence'],
                'Notes': ''
            })

def process_srt_files(folder_path, output_csv_path, min_level, title, datetime_segments, word_time):
    global global_difficult_words
    total_minutes = calculate_total_minutes_from_github(github_repo, srt_path)
    average_minutes_per_segment = total_minutes / len(datetime_segments)
    
    segment_minutes = [random.uniform(average_minutes_per_segment * 0.8, average_minutes_per_segment * 1.2) for _ in datetime_segments]
    segment_seconds = [int(minutes * 60) for minutes in segment_minutes]

    segment_index = 0  
    accumulated_seconds = 0  
    word_time_accumulated = 0

    viewing_times = [0] * len(datetime_segments)
    word_times = [0] * len(datetime_segments)

    # GitHubからファイルリストを取得
    files_url = f'https://api.github.com/repos/{github_repo}/contents/{folder_path}'
    response = requests.get(files_url)
    if response.status_code == 200:
        files = response.json()
        for file_info in files:
            if file_info['name'].endswith('.srt'):
                srt_content = read_srt_file_from_github(github_repo, folder_path, file_info['name'])
                if srt_content:
                    subtitle_texts = extract_subtitle_texts(srt_content)
                    time_pairs = extract_subtitle_times(srt_content)
                    for index, subtitle_text in enumerate(subtitle_texts):
                        clean_text = remove_html_tags(subtitle_text)
                        start_time_srt = time_pairs[index][0]
                        start_time_seconds = srt_time_to_seconds(start_time_srt)
                        total_start_time_seconds = accumulated_seconds + start_time_seconds
                        added_word_count = extract_difficult_words(clean_text, total_start_time_seconds, min_level, 0.3, word_time, segment_index)
                        word_time_accumulated += added_word_count * word_time * 60
                        accumulated_seconds += added_word_count * word_time * 60
                    if time_pairs:
                        last_end_time_srt = time_pairs[-1][1]
                        last_end_time_seconds = srt_time_to_seconds(last_end_time_srt)
                        accumulated_seconds += last_end_time_seconds
                    while segment_index < len(segment_seconds) and accumulated_seconds >= segment_seconds[segment_index]:
                        viewing_times[segment_index] = segment_seconds[segment_index]
                        word_times[segment_index] = word_time_accumulated

                        accumulated_seconds -= segment_seconds[segment_index]
                        word_time_accumulated = 0
                        segment_index += 1

    if segment_index < len(datetime_segments):
        viewing_times[segment_index] += accumulated_seconds
        word_times[segment_index] += word_time_accumulated

    print_data_to_csv(output_csv_path, title, datetime_segments)

    # 各日付の視聴時間と単語時間、合計時間を出力
    for i, date in enumerate(datetime_segments):
        viewing_time = viewing_times[i] if i < len(viewing_times) else 0
        word_time_seconds = word_times[i] if i < len(word_times) else 0
        total_time = viewing_time + word_time_seconds
        viewing_time_minutes = viewing_time / 60
        word_time_minutes = word_time_seconds / 60
        total_time_minutes = total_time / 60
        print(f"Date: {date.strftime('%Y/%m/%d')}, Viewing Time: {viewing_time_minutes:.2f} minutes, Word Time: {word_time_minutes:.2f} minutes, Total Time: {total_time_minutes:.2f} minutes")

def calculate_total_minutes_from_github(repo, path):
    total_seconds = 0
    files_url = f'https://api.github.com/repos/{repo}/contents/{path}'
    response = requests.get(files_url)
    if response.status_code == 200:
        files = response.json()
        for file_info in files:
            if file_info['name'].endswith('.srt'):
                srt_content = read_srt_file_from_github(repo, path, file_info['name'])
                if srt_content:
                    time_pairs = extract_subtitle_times(srt_content)
                    if time_pairs:
                        last_end_time_srt = time_pairs[-1][1]
                        last_end_time_seconds = srt_time_to_seconds(last_end_time_srt)
                        total_seconds += last_end_time_seconds
    total_minutes = total_seconds / 60
    return total_minutes

def calculate_total_minutes(folder_path):
    total_seconds = 0
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.srt'):
            srt_file_path = os.path.join(folder_path, file_name)
            srt_content = read_srt_file(srt_file_path)
            time_pairs = extract_subtitle_times(srt_content)
            if time_pairs:
                last_end_time_srt = time_pairs[-1][1]
                last_end_time_seconds = srt_time_to_seconds(last_end_time_srt)
                total_seconds += last_end_time_seconds
    total_minutes = total_seconds / 60
    return total_minutes

title = 'One Piece'
github_repo = 'sas-news/NetflixWordMaker'
srt_path = f'srt/{title}'
output_csv_path = 'output.csv'
min_level = 2.9
datetime_segments = [datetime(2024, 6, 25, 20, 32), datetime(2024, 6, 26, 18, 16), datetime(2024, 6, 27, 17, 28), datetime(2024, 6, 28, 17, 45), datetime(2024, 6, 30, 10, 15), datetime(2024, 6, 30, 15, 32), datetime(2024, 7, 2, 18, 2), datetime(2024, 7, 3, 17, 2)]

word_time = 0.75

with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Date Added', 'Frequency', 'Word/Expression', 'Definition', 'Source', 'Context', 'Notes']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

process_srt_files(srt_path, output_csv_path, min_level, title, datetime_segments, word_time)
