import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import locale

# URL веб-версии канала
URL = "https://t.me/s/Zaporizhzhyaoblenergo_news"

# Маппинг месяцев для сортировки
UA_MONTHS = {
    "СІЧНЯ": 1, "ЛЮТОГО": 2, "БЕРЕЗНЯ": 3, "КВІТНЯ": 4, "ТРАВНЯ": 5, "ЧЕРВНЯ": 6,
    "ЛИПНЯ": 7, "СЕРПНЯ": 8, "ВЕРЕСНЯ": 9, "ЖОВТНЯ": 10, "ЛИСТОПАДА": 11, "ГРУДНЯ": 12
}

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

    # Читаем сообщения в ОБРАТНОМ порядке (от новых к старым в HTML, но 
    # soup.find_all обычно отдает сверху вниз, а в телеграме сверху - старые).
    # Нам нужно идти от САМЫХ НОВЫХ постов к старым.
    # В веб-версии t.me последние посты находятся внизу.
    # Поэтому реверсируем список, чтобы сначала обрабатывать свежие посты.
    
    unique_schedules = {} # Словарь { "10 ГРУДНЯ": {данные...} }

    months_regex = "|".join(UA_MONTHS.keys())
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)")
    time_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})")

    # Идем от последнего сообщения (внизу страницы) к первому
    for msg in reversed(messages):
        text = msg.get_text(separator="\n")
        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        
        # Переменные для текущего сообщения
        current_date_key = None
        current_data = {"queues": {}, "updated_at": None}
        
        # 1. Сначала ищем дату в сообщении
        for line in lines:
            if "ГПВ" in line.upper():
                match = date_pattern.search(line)
                if match:
                    day, month = match.groups()
                    current_date_key = f"{day} {month.upper()}"
                    
                    # Ищем время обновления
                    time_upd = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                    current_data["updated_at"] = time_upd.group(1) if time_upd else datetime.now().strftime("%H:%M")
                    break # Дату нашли, идем парсить очереди
        
        # Если в сообщении нет даты ГПВ — пропускаем
        if not current_date_key:
            continue

        # ВАЖНО: Если мы уже нашли график на эту дату (в более новом посте),
        # то этот (более старый) пост мы ПРОПУСКАЕМ.
        if current_date_key in unique_schedules:
            continue

        # 2. Парсим очереди для этой даты
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
        
        # Если нашли хоть какие-то данные очередей, сохраняем
        if current_data["queues"]:
            current_data["date"] = current_date_key
            unique_schedules[current_date_key] = current_data

    # Превращаем словарь в список
    final_list = list(unique_schedules.values())

    # Сортируем список по дате (чтобы шли: Вчера, Сегодня, Завтра)
    def date_sorter(item):
        parts = item['date'].split()
        day = int(parts[0])
        month_str = parts[1]
        month = UA_MONTHS.get(month_str, 0)
        # Хак: добавляем год. Если сейчас Декабрь, а месяц Январь -> это следующий год
        now = datetime.now()
        year = now.year
        if now.month == 12 and month == 1:
            year += 1
        return datetime(year, month, day)

    final_list.sort(key=date_sorter)

    # Оставляем только 3 последние (актуальные) даты
    # Обычно это: Вчера (уже не надо), Сегодня, Завтра.
    # Логичнее взять срез последних, так как сортировка по возрастанию.
    # Если дат много (архив), берем 3 последних.
    return final_list[-3:]

if __name__ == "__main__":
    html_content = get_html()
    data = []
    if html_content:
        data = parse_telegram(html_content)
    
    # Добавляем метку времени Киева (UTC+2/UTC+3)
    # Для простоты в Actions (где UTC) добавляем +2 часа, но лучше делать на JS
    # Просто запишем UTC, фронт разберется
    
    final_json = {
        "updated_at_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "schedules": data
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Saved {len(data)} schedules.")
