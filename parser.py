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

# Используем embed-версию (она легче и реже блокируется)
CHANNELS = [
    "https://t.me/s/zoe_alarm?embed=1&discussion=1"
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

# Фразы, означающие, что отключений нет
NO_OUTAGE_PHRASES = [
    "НЕ ВИМИКАЄТЬСЯ", "НЕ ЗАСТОСОВУЮТЬСЯ", "БЕЗ ВІДКЛЮЧЕНЬ", 
    "СКАСОВАНО", "БІЛИЙ", "ЗЕЛЕНИЙ"
]

# ==========================
# 🛠 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================

def get_kiev_time():
    return datetime.utcnow() + timedelta(hours=2)

def log(msg):
    print(msg)
    sys.stdout.flush()

def get_html(target_url):
    # 1. Сначала пробуем прямой запрос с "человеческими" заголовками
    # 2. Если не вышло — пробуем через надежный прокси
    
    strategies = [
        {"url": target_url, "type": "DIRECT"},
        {"url": f"https://api.codetabs.com/v1/proxy?quest={quote(target_url)}", "type": "PROXY (CodeTabs)"},
        {"url": f"https://api.allorigins.win/raw?url={quote(target_url)}", "type": "PROXY (AllOrigins)"}
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.google.com/'
    }

    for strategy in strategies:
        url = strategy["url"]
        try:
            log(f"   🔄 Метод: {strategy['type']}...")
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                content = response.text
                # ПРОВЕРКА: Действительно ли это Телеграм?
                if "tgme_widget" in content or "js-message_text" in content:
                    log(f"   ✅ Успешно! (Скачано {len(content)} байт)")
                    return content
                else:
                    log(f"   ⚠️ Скачано, но это не похоже на Телеграм (Заголовок: {content[:100]}...)")
            else:
                log(f"   ⚠️ Ошибка: Код {response.status_code}")
                
        except Exception as e:
            log(f"   ❌ Ошибка сети: {str(e)[:50]}")
        
        time.sleep(2) # Пауза перед следующей попыткой

    return None

def determine_date_from_text(text):
    """
    Строгий поиск даты. Ищет ТОЛЬКО формат '10 СІЧНЯ'.
    """
    text_upper = text.upper()
    now_kiev = get_kiev_time()
    
    months_regex = "|".join(UA_MONTHS.keys())
    
    # 1. Приоритет: Явная дата (напр. "10 СІЧНЯ")
    date_match = re.search(rf"\b(\d{{1,2}})\s+({months_regex})\b", text_upper)
    if date_match:
        day = int(date_match.group(1))
        month_name = date_match.group(2)
        return f"{day} {month_name}"

    # 2. Приоритет: Ключевые слова
    if "ЗАВТРА" in text_upper:
        target_date = now_kiev + timedelta(days=1)
        day = target_date.day
        month_name = UA_MONTHS_REVERSE.get(target_date.month, "ГРУДНЯ")
        return f"{day} {month_name}"
    
    if "СЬОГОДНІ" in text_upper:
        target_date = now_kiev
        day = target_date.day
        month_name = UA_MONTHS_REVERSE.get(target_date.month, "ГРУДНЯ")
        return f"{day} {month_name}"

    return None

def parse_channel(url):
    html = get_html(url)
    if not html: return []

    soup = BeautifulSoup(html, 'html.parser')
    page_title = soup.title.string.strip() if soup.title else "Без заголовка"
    log(f"   🔎 Заголовок: '{page_title}'")
    
    # Ищем блоки сообщений (учитываем классы embed-версии)
    message_divs = soup.find_all('div', class_=re.compile(r'(tgme_widget_message_text|js-message_text)'))
    
    log(f"   🔎 Найдено постов: {len(message_divs)}")
    
    if len(message_divs) == 0:
        return []

    found_schedules = []
    
    # Регулярки
    # Время: 04:30 – 08:00 (разные тире)
    time_pattern = re.compile(r"(\d{1,2}[:.]\d{2})\s*[-–—−]\s*(\d{1,2}[:.]\d{2})")
    # Очередь в начале строки: "1.1: ..."
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)") 

    for text_div in message_divs:
        text = text_div.get_text(separator="\n")

        if not any(k in text.upper() for k in KEYWORDS):
            continue

        # Пытаемся найти дату
        final_date_key = determine_date_from_text(text)
        
        # Если дата не найдена - пропускаем
        if not final_date_key:
            continue

        # Время обновления
        updated_at_val = get_kiev_time().strftime("%H:%M") 
        time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", text, re.IGNORECASE)
        if time_upd_match:
            updated_at_val = time_upd_match.group(1)

        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        queues_found = {}

        for line in lines:
            # Ищем строку вида "1.1: 04:30 – 08:00"
            q_match = queue_pattern.search(line)
            
            if q_match:
                q_id = q_match.group(1)
                content = q_match.group(2).lower()
                
                # Проверка на "не вимикається"
                if any(phrase.lower() in content for phrase in NO_OUTAGE_PHRASES):
                    queues_found[q_id] = [] # Пустой список = свет есть
                    continue

                # Поиск всех интервалов времени
                intervals = []
                time_matches = list(time_pattern.finditer(content))
                
                for tm in time_matches:
                    start, end = tm.groups()
                    start = start.replace('.', ':')
                    end = end.replace('.', ':')
                    # Добавляем ноль (7:30 -> 07:30)
                    if len(start) == 4: start = "0" + start
                    if len(end) == 4: end = "0" + end
                    intervals.append({"start": start, "end": end})
                
                if intervals:
                    queues_found[q_id] = intervals
                elif not intervals and len(content) < 50:
                     # Защита: если строка короткая и времени нет -> свет есть
                     queues_found[q_id] = []

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

            log(f"   ➕ График на {final_date_key} (черг: {len(queues_found)})")
            
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
        except Exception:
            return []
    return []

def merge_schedules(old_data, new_data):
    merged = {}
    for sch in old_data:
        merged[sch['date']] = sch
    # Новые перезаписывают старые
    for sch in new_data:
        merged[sch['date']] = sch
    return list(merged.values())

def main():
    old_schedules = load_existing_schedules()
    log(f"📂 Старых записей: {len(old_schedules)}")

    new_found = []
    for url in CHANNELS:
        log(f"📡 Парсинг: {url}")
        res = parse_channel(url)
        if res:
            new_found.extend(res)
        else:
            log("   ❌ Пусто (возможно, сработала защита Telegram).")

    if not new_found:
        log("⚠️ Новых данных нет. Файл не изменен.")
        return

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
    final_list = final_list[-3:] 

    output_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": final_list
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    dates_in_file = [item['date'] for item in final_list]
    log(f"💾 Сохранено! Даты: {dates_in_file}")

if __name__ == "__main__":
    main()
