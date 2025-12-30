import re
import json
import requests
import socket
import time
import sys
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote

# ==========================
# ⚙️ НАСТРОЙКИ
# ==========================

CHANNELS = [
    "https://t.me/s/Zaporizhzhyaoblenergo_news",
    "https://t.me/s/info_zp"
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
    """
    Скачивает HTML через веб-прокси, чтобы обойти бан IP GitHub со стороны Telegram.
    """
    # Список зеркал/прокси для обхода блокировки
    # Мы кодируем URL, чтобы передать его как параметр
    proxies = [
        # Вариант 1: corsproxy.io (обычно самый быстрый)
        f"https://corsproxy.io/?{quote(target_url)}",
        # Вариант 2: codetabs (резерв)
        f"https://api.codetabs.com/v1/proxy?quest={quote(target_url)}",
        # Вариант 3: Прямое подключение (на случай, если запущено локально, а не на GitHub)
        target_url
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }

    for url in proxies:
        is_direct = (url == target_url)
        prefix = "DIRECT" if is_direct else "PROXY"
        
        try:
            log(f"   🔄 [{prefix}] Запрос к: {target_url}...")
            
            # Тайм-аут 15 сек
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200 and len(response.text) > 1000:
                log("   ✅ Успешно!")
                return response.text
            else:
                log(f"   ⚠️ Неудачно (Status: {response.status_code}, Len: {len(response.text)})")
                
        except Exception as e:
            log(f"   ❌ Ошибка: {str(e)[:50]}...")
        
        # Небольшая пауза перед следующей попыткой
        time.sleep(1)

    log("   ⛔ Все методы подключения не сработали.")
    return None

def parse_channel(url):
    html = get_html(url)
    if not html: return []

    soup = BeautifulSoup(html, 'html.parser')
    message_wraps = soup.find_all('div', class_='tgme_widget_message_wrap')
    
    found_schedules = []

    months_regex = "|".join(UA_MONTHS.keys())
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    
    # Время: "00:00 - 04:00"
    time_pattern = re.compile(r"(\d{1,2}[:.]\d{2})\s*[-–—−]\s*(\d{1,2}[:.]\d{2})")
    
    # Только конкретные очереди (1.1, 2.1). Групп "1" больше нет.
    specific_queue_pattern = re.compile(r"\b([1-6]\.[12])\b")

    for wrap in reversed(message_wraps):
        text_div = wrap.find('div', class_='tgme_widget_message_text')
        if not text_div: continue
        text = text_div.get_text(separator="\n")

        if not any(k in text.upper() for k in KEYWORDS):
            continue

        time_tag = wrap.find('time')
        post_timestamp = ""
        if time_tag and time_tag.has_attr('datetime'):
            post_timestamp = time_tag['datetime']
        else:
            continue

        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        
        explicit_date_key = None
        updated_at_val = None
        queues_found = {}

        # --- АНАЛИЗ СТРОК ---
        for line in lines:
            if not explicit_date_key:
                match = date_pattern.search(line)
                if match:
                    day, month = match.groups()
                    explicit_date_key = f"{day} {month.upper()}"

            if not updated_at_val:
                time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                if time_upd_match:
                    updated_at_val = time_upd_match.group(1)

            # Ищем время
            time_matches = list(time_pattern.finditer(line))
            
            if time_matches:
                intervals = []
                for tm in time_matches:
                    start, end = tm.groups()
                    start = start.replace('.', ':')
                    end = end.replace('.', ':')
                    intervals.append({"start": start, "end": end})

                # Ищем очереди ТОЛЬКО в тексте ПЕРЕД временем
                text_before_time = line[:time_matches[0].start()]
                
                # Ищем 1.1, 1.2...
                found_sub_queues = specific_queue_pattern.findall(text_before_time)
                
                # Привязываем интервалы к найденным очередям
                for q_id in found_sub_queues:
                    if q_id not in queues_found:
                        queues_found[q_id] = []
                    queues_found[q_id].extend(intervals)

        # --- СОХРАНЕНИЕ ---
        if queues_found:
            # === ОЧИСТКА ДУБЛИКАТОВ ===
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
            # ==========================

            final_date_key = None

            if explicit_date_key:
                final_date_key = explicit_date_key
            else:
                try:
                    dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                    dt_kiev = dt + timedelta(hours=2)

                    if "завтра" in text.lower():
                        dt_kiev += timedelta(days=1)
                        log(f"ℹ️ Маркер 'завтра'. Дата смещена: {dt_kiev.strftime('%d.%m')}")

                    day = dt_kiev.day
                    month_name = UA_MONTHS_REVERSE.get(dt_kiev.month, "ГРУДНЯ")
                    final_date_key = f"{day} {month_name}"
                except Exception as e:
                    log(f"⚠️ Ошибка даты: {e}")
                    continue

            if not updated_at_val:
                try:
                    dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                    dt_kiev = dt + timedelta(hours=2)
                    updated_at_val = dt_kiev.strftime("%H:%M")
                except:
                    updated_at_val = "??:??"

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
        d_key = sch['date']
        if d_key not in merged:
            merged[d_key] = sch
        else:
            existing_ts = merged[d_key]['source_ts']
            new_ts = sch['source_ts']
            if new_ts > existing_ts:
                log(f"🔄 Обновление {d_key} (найден более свежий пост).")
                merged[d_key] = sch
    return list(merged.values())

def main():
    all_found = []
    
    for url in CHANNELS:
        log(f"📡 Парсинг канала: {url}")
        res = parse_channel(url)
        log(f"   Найдено графиков: {len(res)}")
        all_found.extend(res)

    final_list = merge_schedules(all_found)

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
    final_list = final_list[-3:]

    output_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": final_list
    }

    for item in output_json["schedules"]:
        if "source_ts" in item:
            del item["source_ts"]

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    log(f"💾 Сохранено {len(final_list)} дней в schedule.json")

if __name__ == "__main__":
    main()
