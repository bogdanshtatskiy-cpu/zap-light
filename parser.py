import re
import json
import requests
import socket
import time
import sys
import os
import random
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
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

CHANNELS = [
    "https://t.me/s/it_is_zp_tg",
    "https://t.me/s/tvoe_zaporizhzhia",
    "https://t.me/s/zapnovini",
    "https://t.me/s/info_zp",
    "https://t.me/s/zoe_alarm"
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

NO_OUTAGE_PHRASES = [
    "НЕ ВИМИКАЄТЬСЯ", "НЕ ЗАСТОСОВУЮТЬСЯ", "БЕЗ ВІДКЛЮЧЕНЬ", 
    "СКАСОВАНО", "БІЛИЙ", "ЗЕЛЕНИЙ"
]

# ==========================
# 🛠 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================

def get_kiev_time():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def log(msg):
    print(msg)
    sys.stdout.flush()

def get_html(target_url):
    rnd = random.randint(1, 999999)
    proxies = [
        f"https://api.allorigins.win/raw?url={quote(target_url)}&rnd={rnd}",
        f"https://corsproxy.io/?{quote(target_url)}", 
        f"https://api.codetabs.com/v1/proxy?quest={quote(target_url)}&rnd={rnd}"
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    for url in proxies:
        try:
            log(f"   🔄 Пробуем через прокси...")
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200 and len(response.text) > 2000:
                content = response.text
                if "tgme_widget" in content:
                    return content
        except Exception:
            pass
        time.sleep(1)
    return None

def parse_post_date(date_str):
    """Парсит дату поста из HTML (обычно ISO формат)"""
    try:
        # Пример: 2024-01-14T18:00:00+00:00
        dt = datetime.fromisoformat(date_str)
        # Конвертируем в Киевское время (UTC+2 / UTC+3)
        return dt.astimezone(timezone(timedelta(hours=2)))
    except Exception:
        return get_kiev_time()

def determine_date_from_text(text, post_date):
    """
    Определяет дату графика.
    post_date - это datetime публикации сообщения (Киевское время)
    """
    text_upper = text.upper()
    
    # 1. Поиск явной даты (15 СІЧНЯ)
    months_regex = "|".join(UA_MONTHS.keys())
    date_match = re.search(rf"\b(\d{{1,2}})\s+({months_regex})\b", text_upper)
    if date_match:
        day = int(date_match.group(1))
        month_name = date_match.group(2)
        return f"{day} {month_name}"

    # 2. Относительные даты (СЧИТАЕМ ОТ ДАТЫ ПОСТА, А НЕ ОТ ТЕКУЩЕЙ)
    if "ЗАВТРА" in text_upper:
        target_date = post_date + timedelta(days=1)
        day = target_date.day
        month_name = UA_MONTHS_REVERSE.get(target_date.month, "ГРУДНЯ")
        return f"{day} {month_name}"
    
    if "СЬОГОДНІ" in text_upper:
        target_date = post_date
        day = target_date.day
        month_name = UA_MONTHS_REVERSE.get(target_date.month, "ГРУДНЯ")
        return f"{day} {month_name}"

    return None

def parse_channel(url):
    html = get_html(url)
    if not html: return []

    soup = BeautifulSoup(html, 'html.parser')
    page_title = soup.title.string.strip() if soup.title else "Channel"
    log(f"   🔎 Анализ: {page_title}")
    
    # 🔥 Ищем блоки сообщений целиком, чтобы достать и ТЕКСТ, и ДАТУ
    message_wraps = soup.find_all('div', class_='tgme_widget_message')
    
    if not message_wraps:
        # Фоллбэк для старых версий прокси
        return []

    found_schedules = []
    
    # Регулярки
    time_pattern = re.compile(r"(?:з\s*)?(\d{1,2}[:.;]\d{2})\s*(?:[-–—−]|до|по)\s*(\d{1,2}[:.;]\d{2})", re.IGNORECASE)
    queue_pattern = re.compile(r"^\s*(?:Черга\s*)?(\d\.\d)\s*[:)]?\s*(.*)", re.IGNORECASE)

    for msg in message_wraps:
        # 1. Достаем текст
        text_div = msg.find('div', class_='tgme_widget_message_text')
        if not text_div: continue
        text = text_div.get_text(separator="\n")

        if not any(k in text.upper() for k in KEYWORDS):
            continue

        # 2. Достаем дату публикации поста (для фикса "ЗАВТРА")
        post_date = get_kiev_time()
        time_tag = msg.find('time')
        if time_tag and 'datetime' in time_tag.attrs:
            post_date = parse_post_date(time_tag['datetime'])

        # Определяем дату графика на основе даты поста
        final_date_key = determine_date_from_text(text, post_date)
        if not final_date_key:
            continue

        # Формируем метку времени обновления
        # Берем время из поста, если есть "(оновлено 10:00)", иначе время поста
        updated_at_val = post_date.strftime("%d.%m %H:%M")
        time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", text, re.IGNORECASE)
        if time_upd_match:
            # Если есть явное время обновления, берем дату поста + это время
            updated_at_val = f"{post_date.strftime('%d.%m')} {time_upd_match.group(1)}"

        # Парсинг очередей
        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        queues_found = {}

        for line in lines:
            q_match = queue_pattern.search(line)
            if q_match:
                q_id = q_match.group(1)
                content = q_match.group(2).lower()
                
                if any(phrase.lower() in content for phrase in NO_OUTAGE_PHRASES):
                    queues_found[q_id] = [] 
                    continue

                intervals = []
                time_matches = list(time_pattern.finditer(content))
                for tm in time_matches:
                    start, end = tm.groups()
                    start = start.replace('.', ':').replace(';', ':')
                    end = end.replace('.', ':').replace(';', ':')
                    if len(start) == 4: start = "0" + start
                    if len(end) == 4: end = "0" + end
                    intervals.append({"start": start, "end": end})
                
                if intervals:
                    queues_found[q_id] = intervals
                elif not intervals and len(content) < 30:
                     queues_found[q_id] = []

        if queues_found:
            # Удаляем дубликаты интервалов
            for q_id in queues_found:
                unique = []
                seen = set()
                for i in queues_found[q_id]:
                    key = f"{i['start']}-{i['end']}"
                    if key not in seen:
                        seen.add(key)
                        unique.append(i)
                unique.sort(key=lambda x: x['start'])
                queues_found[q_id] = unique

            log(f"   ➕ График на {final_date_key} (из поста от {post_date.strftime('%d.%m %H:%M')})")
            
            found_schedules.append({
                "date": final_date_key,
                "queues": queues_found,
                "updated_at": updated_at_val
            })

    return found_schedules

def load_existing_schedules():
    if os.path.exists('schedule.json'):
        try:
            with open('schedule.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("schedules", [])
        except Exception:
            return []
    return []

def merge_schedules(old_data, new_data):
    merged = {}
    
    # 1. Загружаем старое
    for sch in old_data:
        merged[sch['date']] = sch
    
    # 2. Накладываем новое (приоритет у последних каналов в списке CHANNELS)
    # Важно: если new_data содержит график на 15-е, он перезапишет старый
    for sch in new_data:
        # Простая защита: если в новом графике пусто (0 очередей), а в старом было, не затираем
        # (Хотя логика парсера обычно не возвращает пустые объекты, но на всякий случай)
        if sch['queues'] or sch['date'] not in merged:
            merged[sch['date']] = sch
            
    return list(merged.values())

def main():
    old_schedules = load_existing_schedules()
    log(f"📂 Было записей: {len(old_schedules)}")

    new_found = []
    for url in CHANNELS:
        log(f"📡 {url}")
        res = parse_channel(url)
        if res:
            new_found.extend(res)
        else:
            log("   ⚠️ Пусто.")

    final_list = merge_schedules(old_schedules, new_found)

    # Сортировка по дате
    def date_sorter(item):
        try:
            parts = item['date'].split()
            day = int(parts[0])
            month_str = parts[1]
            month = UA_MONTHS.get(month_str, 0)
            now = datetime.now()
            year = now.year
            # Обработка смены года
            if now.month == 12 and month == 1: year += 1
            elif now.month == 1 and month == 12: year -= 1
            return datetime(year, month, day)
        except:
            return datetime.now()

    final_list.sort(key=date_sorter)
    # Оставляем только 5 актуальных дней, чтобы не копить мусор
    final_list = final_list[-5:]

    output_json = {
        "generated_at": get_kiev_time().strftime("%d.%m %H:%M"), 
        "schedules": final_list
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    dates_in_file = [item['date'] for item in final_list]
    log(f"💾 ИТОГ: {dates_in_file}")

if __name__ == "__main__":
    main()
