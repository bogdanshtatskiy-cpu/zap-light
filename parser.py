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
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.astimezone(timezone(timedelta(hours=2)))
    except Exception:
        return get_kiev_time()

def determine_date_from_text(text, post_date):
    text_upper = text.upper()
    
    # 1. Поиск явной даты в тексте (например, "21 ЛЮТОГО")
    months_regex = "|".join(UA_MONTHS.keys())
    date_match = re.search(rf"\b(\d{{1,2}})\s+({months_regex})\b", text_upper)
    if date_match:
        day = int(date_match.group(1))
        month_name = date_match.group(2)
        return f"{day} {month_name}"

    # Если явной даты нет, анализируем только начало текста (первые 250 символов),
    # чтобы избежать ложных срабатываний слова "завтра" в конце поста.
    header_text = text_upper[:250]

    # 2. Если это экстренное обновление, то это 100% график на СЕГОДНЯ
    if re.search(r"\b(ОНОВЛЕНО|ОНОВЛЕННЯ|ЗМІНИ|ЗМІНЕНО|ТЕРМІНОВО|ЗНОВУ|СЬОГОДНІ)\b", header_text):
        return f"{post_date.day} {UA_MONTHS_REVERSE.get(post_date.month, 'ГРУДНЯ')}"

    # 3. Прямое указание, что график на завтра
    if "ЗАВТРА" in header_text:
        target_date = post_date + timedelta(days=1)
        return f"{target_date.day} {UA_MONTHS_REVERSE.get(target_date.month, 'ГРУДНЯ')}"

    # 4. Фоллбек: если нет никаких дат, но есть график, считаем что это на день публикации поста (сегодня)
    return f"{post_date.day} {UA_MONTHS_REVERSE.get(post_date.month, 'ГРУДНЯ')}"

def parse_channel(url):
    html = get_html(url)
    if not html: return []

    soup = BeautifulSoup(html, 'html.parser')
    page_title = soup.title.string.strip() if soup.title else "Channel"
    log(f"   🔎 Анализ: {page_title}")
    
    message_wraps = soup.find_all('div', class_='tgme_widget_message')
    if not message_wraps: return []

    found_schedules = []
    
    time_pattern = re.compile(r"(?:з\s*)?(\d{1,2}[:.;]\d{2})\s*(?:[-–—−]|до|по)\s*(\d{1,2}[:.;]\d{2})", re.IGNORECASE)
    queue_line_pattern = re.compile(r"^\s*(?:Черга\s*|▪️\s*)?((?:\d\.\d\s*(?:[\/,+&]|і|та)?\s*)+)(?:\s*[:)])?\s*(.*)", re.IGNORECASE)

    for msg in message_wraps:
        text_div = msg.find('div', class_='tgme_widget_message_text')
        if not text_div: continue
        text = text_div.get_text(separator="\n")

        if not any(k in text.upper() for k in KEYWORDS): continue

        post_date = get_kiev_time()
        time_tag = msg.find('time')
        if time_tag and 'datetime' in time_tag.attrs:
            post_date = parse_post_date(time_tag['datetime'])

        final_date_key = determine_date_from_text(text, post_date)
        if not final_date_key: continue

        updated_at_val = post_date.strftime("%d.%m %H:%M")
        time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", text, re.IGNORECASE)
        if time_upd_match:
            updated_at_val = f"{post_date.strftime('%d.%m')} {time_upd_match.group(1)}"

        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        queues_found = {}

        for line in lines:
            match = queue_line_pattern.search(line)
            if match:
                queues_part = match.group(1)
                content = match.group(2).lower()
                found_ids = re.findall(r"\d\.\d", queues_part)
                is_no_outage = any(phrase.lower() in content for phrase in NO_OUTAGE_PHRASES)

                intervals = []
                if not is_no_outage:
                    time_matches = list(time_pattern.finditer(content))
                    for tm in time_matches:
                        start, end = tm.groups()
                        start = start.replace('.', ':').replace(';', ':')
                        end = end.replace('.', ':').replace(';', ':')
                        if len(start) == 4: start = "0" + start
                        if len(end) == 4: end = "0" + end
                        intervals.append({"start": start, "end": end})
                
                for q_id in found_ids:
                    if is_no_outage: queues_found[q_id] = []
                    elif intervals: queues_found[q_id] = intervals
                    elif not intervals and len(content) < 30: queues_found[q_id] = []

        if queues_found:
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
                "updated_at": updated_at_val,
                "_post_timestamp": post_date.timestamp() # Сохраняем точное время для сортировки
            })

    return found_schedules

def load_existing_schedules():
    if os.path.exists('schedule.json'):
        try:
            with open('schedule.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("schedules", [])
        except Exception: return []
    return []

def merge_schedules(old_data, new_data):
    merged = {}
    
    # Сначала загружаем старые данные
    for sch in old_data: 
        merged[sch['date']] = sch
        
    # Сортируем новые данные по времени публикации (от старых постов к самым новым)
    # Это гарантирует, что самое свежее обновление перезапишет все предыдущие
    new_data.sort(key=lambda x: x.get('_post_timestamp', 0))
    
    for sch in new_data:
        clean_sch = {k: v for k, v in sch.items() if k != '_post_timestamp'}
        # Перезаписываем, если нашли график, или если для этой даты еще нет данных
        if clean_sch['queues'] or clean_sch['date'] not in merged:
            merged[clean_sch['date']] = clean_sch
            
    return list(merged.values())

def clean_old_schedules(schedules):
    """Видаляє графіки старіші за 2 дні"""
    today = get_kiev_time().date()
    cutoff_date = today - timedelta(days=2)
    
    cleaned = []
    for item in schedules:
        try:
            parts = item['date'].split()
            day = int(parts[0])
            month_str = parts[1]
            month = UA_MONTHS.get(month_str, 0)
            now = get_kiev_time()
            year = now.year
            if now.month == 12 and month == 1: year += 1
            elif now.month == 1 and month == 12: year -= 1
            
            item_date = datetime(year, month, day).date()
            if item_date >= cutoff_date:
                cleaned.append(item)
        except:
            cleaned.append(item)
    return cleaned

def main():
    old_schedules = load_existing_schedules()
    log(f"📂 Было записей: {len(old_schedules)}")

    new_found = []
    for url in CHANNELS:
        log(f"📡 {url}")
        res = parse_channel(url)
        if res: new_found.extend(res)
        else: log("   ⚠️ Пусто.")

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
        except: return datetime.now()

    final_list.sort(key=date_sorter)
    
    # Очистка старых + лимит
    final_list = clean_old_schedules(final_list)
    final_list = final_list[-35:] 

    output_json = {
        "generated_at": get_kiev_time().strftime("%d.%m %H:%M"), 
        "schedules": final_list
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    dates_in_file = [item['date'] for item in final_list]
    log(f"💾 ИТОГ ({len(dates_in_file)} дн): {dates_in_file}")

if __name__ == "__main__":
    main()
