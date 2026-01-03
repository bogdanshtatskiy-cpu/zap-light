import re
import json
import requests
import socket
import time
import sys
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

# Оставили только info_zp, как ты и просил
CHANNELS = [
    "https://t.me/s/info_zp?embed=1&discussion=1"
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for url in proxies:
        try:
            log(f"   🔄 Пробуем через: {url[:40]}...")
            response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200 and len(response.text) > 500:
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
    
    message_divs = soup.find_all('div', class_=re.compile(r'(tgme_widget_message_text|js-message_text)'))
    
    log(f"   🔎 Найдено блоков с текстом: {len(message_divs)}")
    
    if len(message_divs) == 0:
        log("   ⚠️ HTML (первые 200 символов):")
        log(f"   {str(soup)[:200]}")
        return []

    found_schedules = []

    months_regex = "|".join(UA_MONTHS.keys())
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    time_pattern = re.compile(r"(\d{1,2}[:.]\d{2})\s*[-–—−]\s*(\d{1,2}[:.]\d{2})")
    specific_queue_pattern = re.compile(r"\b([1-6]\.[12])\b")

    for text_div in message_divs:
        text = text_div.get_text(separator="\n")

        if not any(k in text.upper() for k in KEYWORDS):
            continue

        post_timestamp = datetime.utcnow().isoformat() 

        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        
        explicit_date_key = None
        updated_at_val = None
        queues_found = {}

        for line in lines:
            if not explicit_date_key:
                match = date_pattern.search(line)
                if match:
                    day_raw, month = match.groups()
                    
                    # === ИЗМЕНЕНИЕ: Нормализация даты ===
                    # Превращаем "02" в 2, а потом обратно в строку "2"
                    # Теперь "2 СІЧНЯ" и "02 СІЧНЯ" будут равны "2 СІЧНЯ"
                    day_clean = str(int(day_raw))
                    
                    explicit_date_key = f"{day_clean} {month.upper()}"

            if not updated_at_val:
                time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                if time_upd_match:
                    updated_at_val = time_upd_match.group(1)

            time_matches = list(time_pattern.finditer(line))
            
            if time_matches:
                intervals = []
                for tm in time_matches:
                    start, end = tm.groups()
                    start = start.replace('.', ':')
                    end = end.replace('.', ':')
                    intervals.append({"start": start, "end": end})

                text_before_time = line[:time_matches[0].start()]
                found_sub_queues = specific_queue_pattern.findall(text_before_time)
                
                for q_id in found_sub_queues:
                    if q_id not in queues_found:
                        queues_found[q_id] = []
                    queues_found[q_id].extend(intervals)

        if queues_found:
            for q_id in queues_found:
                unique_intervals = []
                seen = set()
                for interval in queues_found[q_id]:
                    key = f"{interval['start']}-{interval['end']}"
                    if key not in seen:
                        seen.add(key)
                        unique_intervals.append(interval)
                unique_intervals.sort(key=lambda x: x['start'])
                queues_found[q_id] = unique_intervals

            final_date_key = None

            if explicit_date_key:
                final_date_key = explicit_date_key
            else:
                now_kiev = get_kiev_time()
                if "завтра" in text.lower():
                    target_date = now_kiev + timedelta(days=1)
                    log(f"ℹ️ Найден график на ЗАВТРА (по ключевому слову).")
                else:
                    target_date = now_kiev
                
                day = target_date.day
                month_name = UA_MONTHS_REVERSE.get(target_date.month, "ГРУДНЯ")
                final_date_key = f"{day} {month_name}"

            if not updated_at_val:
                updated_at_val = get_kiev_time().strftime("%H:%M")

            found_schedules.append({
                "date": final_date_key,
                "queues": queues_found,
                "updated_at": updated_at_val,
                "source_ts": post_timestamp
            })

    return found_schedules

def merge_schedules(all_schedules):
    merged = {}
    for sch in all_schedules:
        # Теперь ключи всегда нормализованы (без лишних нулей),
        # поэтому дубликаты (02 и 2) сольются в один ключ
        d_key = sch['date']
        merged[d_key] = sch
    return list(merged.values())

def main():
    all_found = []
    
    for url in CHANNELS:
        log(f"📡 Парсинг канала: {url}")
        res = parse_channel(url)
        if res:
            log(f"   ✅ Найдено графиков: {len(res)}")
            all_found.extend(res)
        else:
            log("   ❌ Графиков не найдено.")

    final_list = merge_schedules(all_found)

    # === ПРЕДОХРАНИТЕЛЬ ===
    if not final_list:
        log("\n⚠️ ВНИМАНИЕ: Парсер не нашел новых данных.")
        log("⚠️ Файл schedule.json НЕ БУДЕТ ИЗМЕНЕН, чтобы сохранить ручные данные.")
        return
    # =======================

    def date_sorter(item):
        try:
            parts = item['date'].split()
            day = int(parts[0])
            month_str = parts[1]
            month = UA_MONTHS.get(month_str, 0)
            now = datetime.now()
            year = now.year
            # Логика смены года
            if now.month == 12 and month == 1: year += 1
            elif now.month == 1 and month == 12: year -= 1
            return datetime(year, month, day)
        except:
            return datetime.now()

    final_list.sort(key=date_sorter)
    # Оставляем последние 3 дня
    final_list = final_list[-3:]

    output_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": final_list
    }

    # Чистим служебные поля
    for item in output_json["schedules"]:
        if "source_ts" in item:
            del item["source_ts"]

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    log(f"💾 Сохранено {len(final_list)} дней в schedule.json")

if __name__ == "__main__":
    main()
