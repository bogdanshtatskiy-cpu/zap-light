import re
import json
import requests
import socket
import time
import sys
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote
import requests.packages.urllib3.util.connection as urllib3_cn

# ==========================
# 🔧 ФИКС ДЛЯ GITHUB ACTIONS (IPv4)
# ==========================
def allowed_gai_family():
    return socket.AF_INET

urllib3_cn.allowed_gai_family = allowed_gai_family

# ==========================
# ⚙️ НАСТРОЙКИ
# ==========================

# ВАЖНО: Добавлена /s/ в URL для доступа к веб-версии канала
CHANNELS = [
    "https://t.me/s/svitlo_zaporozhye"
]

KEYWORDS = [
    "ГПВ", "ГРАФІК", "ВІДКЛЮЧЕН", "ЕЛЕКТРО", "ЧЕРГ", 
    "ОНОВЛЕН", "ЗМІН", "ОБЛЕНЕРГО", "УКРЕНЕРГО", "СВІТЛ"
]

UA_MONTHS = {
    "СІЧНЯ": 1, "ЛЮТОГО": 2, "БЕРЕЗНЯ": 3, "КВІТНЯ": 4, "ТРАВНЯ": 5, "ЧЕРВНЯ": 6,
    "ЛИПНЯ": 7, "СЕРПНЯ": 8, "ВЕРЕСНЯ": 9, "ЖОВТНЯ": 10, "ЛИСТОПАДА": 11, "ГРУДНЯ": 12
}
UA_MONTHS_REVERSE = {v: k for k, v in UA_MONTHS.items()}

# ==========================
# 🛠 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================

def get_kiev_time():
    return datetime.utcnow() + timedelta(hours=2)

def log(msg):
    print(msg)
    sys.stdout.flush()

def get_html(target_url):
    proxies = [
        f"https://api.allorigins.win/raw?url={quote(target_url)}",
        f"https://corsproxy.io/?{quote(target_url)}",
        f"https://api.codetabs.com/v1/proxy?quest={quote(target_url)}"
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache'
    }

    for url in proxies:
        try:
            log(f"   🔄 Пробуем через: {url[:40]}...")
            response = requests.get(url, headers=headers, timeout=20)
            
            # Проверяем, что вернулось достаточно данных (страница с постами обычно > 20кб)
            if response.status_code == 200 and len(response.text) > 2000:
                log(f"   ✅ Скачано {len(response.text)} байт.")
                return response.text
            else:
                log(f"   ⚠️ Неудачно (Код: {response.status_code}, Размер: {len(response.text)})")
                
        except Exception as e:
            log(f"   ❌ Ошибка: {str(e)[:50]}...")
        
        time.sleep(1)

    return None

def parse_channel(url):
    html = get_html(url)
    if not html: return []

    soup = BeautifulSoup(html, 'html.parser')
    page_title = soup.title.string.strip() if soup.title else "Без заголовка"
    log(f"   🔎 Заголовок страницы: '{page_title}'")
    
    # Ищем блоки сообщений
    message_divs = soup.find_all('div', class_='tgme_widget_message_text')
    
    if not message_divs:
        # Пробуем альтернативный класс (иногда бывает js-message_text)
        message_divs = soup.find_all('div', class_='js-message_text')
        
    log(f"   🔎 Найдено сообщений для анализа: {len(message_divs)}")
    
    if len(message_divs) == 0:
        return []

    found_schedules = []
    months_regex = "|".join(UA_MONTHS.keys())
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    # Регулярка для времени (учтены разные тире и пробелы)
    time_pattern = re.compile(r"(\d{1,2}[:.]\d{2})\s*[-–—−]\s*(\d{1,2}[:.]\d{2})")
    specific_queue_pattern = re.compile(r"\b([1-6]\.[12])\b")

    for text_div in message_divs:
        text = text_div.get_text(separator="\n")

        if not any(k in text.upper() for k in KEYWORDS):
            continue

        updated_at_val = None
        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        
        explicit_date_key = None
        queues_found = {}

        for line in lines:
            # 1. Поиск даты (08 СІЧНЯ)
            if not explicit_date_key:
                match = date_pattern.search(line)
                if match:
                    day_raw, month = match.groups()
                    day_clean = str(int(day_raw))
                    explicit_date_key = f"{day_clean} {month.upper()}"

            # 2. Поиск времени обновления
            if not updated_at_val:
                time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                if time_upd_match:
                    updated_at_val = time_upd_match.group(1)

            # 3. Поиск интервалов
            time_matches = list(time_pattern.finditer(line))
            
            if time_matches:
                intervals = []
                for tm in time_matches:
                    start, end = tm.groups()
                    start = start.replace('.', ':')
                    end = end.replace('.', ':')
                    # Нормализация (8:00 -> 08:00)
                    if len(start) == 4: start = "0" + start
                    if len(end) == 4: end = "0" + end
                    intervals.append({"start": start, "end": end})

                # Ищем очередь ТОЛЬКО перед временем в той же строке
                # (1.1: 00:00 - 02:00...)
                text_before_time = line[:time_matches[0].start()]
                found_sub_queues = specific_queue_pattern.findall(text_before_time)
                
                for q_id in found_sub_queues:
                    if q_id not in queues_found:
                        queues_found[q_id] = []
                    queues_found[q_id].extend(intervals)

        if queues_found:
            # Удаление дубликатов
            for q_id in queues_found:
                unique_intervals = []
                seen = set()
                for interval in queues_found[q_id]:
                    key = f"{interval['start']}-{interval['end']}"
                    if key not in seen:
                        seen.add(key)
                        unique_intervals.append(interval)
                # Сортировка по времени начала
                unique_intervals.sort(key=lambda x: x['start'])
                queues_found[q_id] = unique_intervals

            final_date_key = None

            if explicit_date_key:
                final_date_key = explicit_date_key
            else:
                # Если даты в тексте нет, пробуем "завтра" или текущую
                now_kiev = get_kiev_time()
                if "завтра" in text.lower():
                    target_date = now_kiev + timedelta(days=1)
                else:
                    target_date = now_kiev
                
                day = target_date.day
                month_name = UA_MONTHS_REVERSE.get(target_date.month, "ГРУДНЯ")
                final_date_key = f"{day} {month_name}"

            if not updated_at_val:
                updated_at_val = get_kiev_time().strftime("%H:%M")

            log(f"   ➕ Найден график на {final_date_key}")
            found_schedules.append({
                "date": final_date_key,
                "queues": queues_found,
                "updated_at": updated_at_val
            })

    return found_schedules

# ==========================
# 💾 ЛОГИКА СОХРАНЕНИЯ
# ==========================

def load_existing_schedules():
    if os.path.exists('schedule.json'):
        try:
            with open('schedule.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("schedules", [])
        except Exception as e:
            log(f"⚠️ Ошибка чтения старого файла: {e}")
    return []

def merge_schedules(old_data, new_data):
    merged = {}
    for sch in old_data:
        merged[sch['date']] = sch
    for sch in new_data:
        merged[sch['date']] = sch
    return list(merged.values())

def main():
    old_schedules = load_existing_schedules()
    log(f"📂 Загружено старых записей: {len(old_schedules)}")

    new_found = []
    for url in CHANNELS:
        log(f"📡 Парсинг канала: {url}")
        res = parse_channel(url)
        if res:
            log(f"   ✅ Всего извлечено графиков: {len(res)}")
            new_found.extend(res)
        else:
            log("   ❌ Графиков не извлечено.")

    final_list = merge_schedules(old_schedules, new_found)

    def date_sorter(item):
        try:
            parts = item['date'].split()
            day = int(parts[0])
            month_str = parts[1]
            month = UA_MONTHS.get(month_str, 0)
            now = datetime.now()
            year = now.year
            if now.month == 12 and month == 1: year += 1
            elif now.month == 1 and month == 12: year -= 1
            return datetime(year, month, day)
        except:
            return datetime.now()

    final_list.sort(key=date_sorter)
    final_list = final_list[-3:] # Храним только 3 последних дня

    output_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": final_list
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    dates_in_file = [item['date'] for item in final_list]
    log(f"💾 Итого в файле: {dates_in_file}")

if __name__ == "__main__":
    main()


