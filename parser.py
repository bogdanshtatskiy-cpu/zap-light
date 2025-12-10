import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta # Добавили timedelta для сдвига времени

# URL веб-версии канала
URL = "https://t.me/s/Zaporizhzhyaoblenergo_news"

# Маппинг месяцев для сортировки
UA_MONTHS = {
    "СІЧНЯ": 1, "ЛЮТОГО": 2, "БЕРЕЗНЯ": 3, "КВІТНЯ": 4, "ТРАВНЯ": 5, "ЧЕРВНЯ": 6,
    "ЛИПНЯ": 7, "СЕРПНЯ": 8, "ВЕРЕСНЯ": 9, "ЖОВТНЯ": 10, "ЛИСТОПАДА": 11, "ГРУДНЯ": 12
}

def get_kiev_time():
    """Получает текущее время UTC и добавляет 2 часа (зимнее время)"""
    return datetime.utcnow() + timedelta(hours=2)

def get_html():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Error: {e}")
    return None

def parse_telegram(html):
    soup = BeautifulSoup(html, 'html.parser')
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    
    if not messages:
        return []

    unique_schedules = {} 

    months_regex = "|".join(UA_MONTHS.keys())
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)")
    time_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})")

    # Идем от последнего сообщения к первому
    for msg in reversed(messages):
        text = msg.get_text(separator="\n")
        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        
        current_date_key = None
        current_data = {"queues": {}, "updated_at": None}
        
        # 1. Ищем дату
        for line in lines:
            if "ГПВ" in line.upper():
                match = date_pattern.search(line)
                if match:
                    day, month = match.groups()
                    current_date_key = f"{day} {month.upper()}"
                    
                    # Ищем время обновления в тексте сообщения
                    time_upd = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                    
                    # Если нашли в тексте - берем его. Если нет - берем текущее КИЕВСКОЕ время
                    if time_upd:
                        current_data["updated_at"] = time_upd.group(1)
                    else:
                        current_data["updated_at"] = get_kiev_time().strftime("%H:%M")
                    
                    break
        
        if not current_date_key:
            continue

        if current_date_key in unique_schedules:
            continue

        # 2. Парсим очереди
        for line in lines:
            q_match = queue_pattern.search(line)
            if q_match:
                q_id = q_match.group(1)
                times_raw = q_match.group(2)
                
                intervals = []
                parts = re.split(r"[,;]", times_raw)
                for part in parts:
                    t_match = time_pattern.search(part)
                    if t_match:
                        start, end = t_match.groups()
                        intervals.append({"start": start, "end": end})
                
                if intervals:
                    current_data["queues"][q_id] = intervals
        
        if current_data["queues"]:
            current_data["date"] = current_date_key
            unique_schedules[current_date_key] = current_data

    final_list = list(unique_schedules.values())

    def date_sorter(item):
        parts = item['date'].split()
        day = int(parts[0])
        month_str = parts[1]
        month = UA_MONTHS.get(month_str, 0)
        now = datetime.now()
        year = now.year
        if now.month == 12 and month == 1:
            year += 1
        return datetime(year, month, day)

    final_list.sort(key=date_sorter)
    return final_list[-3:]

if __name__ == "__main__":
    html_content = get_html()
    data = []
    if html_content:
        data = parse_telegram(html_content)
    
    # Тут тоже используем Киевское время для метки "Последняя проверка"
    final_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": data
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Saved {len(data)} schedules.")
