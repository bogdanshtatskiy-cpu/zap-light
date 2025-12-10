import re
import json
import datetime
# Если нужно скачивать с сайта, понадобится requests и beautifulsoup4
# import requests
# from bs4 import BeautifulSoup

def parse_schedule(text):
    data = {
        "date": None,
        "updated_at": None,
        "queues": {}
    }

    # 1. Ищем дату и время обновления (Regex под твои примеры)
    # Пример: ОНОВЛЕНО ГПВ НА 09 ГРУДНЯ (оновлено о 05:34)
    header_match = re.search(r"(?:ОНОВЛЕНО|ДІЯТИМУТЬ) ГПВ.*?(\d{1,2}\s+[А-ЯІЇЄ]+)", text, re.IGNORECASE)
    if header_match:
        data["date"] = header_match.group(1)

    update_time_match = re.search(r"\(оновлено о (\d{2}:\d{2})\)", text)
    if update_time_match:
        data["updated_at"] = update_time_match.group(1)
    else:
        data["updated_at"] = datetime.datetime.now().strftime("%H:%M") # Если не нашли, ставим текущее

    # 2. Парсим очереди (1.1, 1.2 ... 6.2)
    # Ищем строки вида "1.1: 00:00 – 02:00, 06:00 – 11:00"
    queue_pattern = re.compile(r"(\d\.\d):\s*((?:\d{2}:\d{2}\s*–\s*\d{2}:\d{2}(?:,\s*)?)+)")
    
    for line in text.split('\n'):
        match = queue_pattern.search(line)
        if match:
            queue_id = match.group(1)
            times_str = match.group(2)
            
            # Разбиваем интервалы: "00:00 – 02:00, 06:00 – 11:00" -> список объектов
            intervals = []
            for part in times_str.split(','):
                part = part.strip()
                if '–' in part: # Обрати внимание, тут длинное тире, как в твоем тексте
                    start, end = part.split('–')
                    intervals.append({"start": start.strip(), "end": end.strip()})
            
            data["queues"][queue_id] = intervals

    return data

# --- Эмуляция работы ---
# В реальности тут будет:
# response = requests.get('URL_САЙТА_ОБЛЭНЕРГО')
# raw_text = BeautifulSoup(response.text, 'html.parser').get_text()

# Для теста используем твой текст:
raw_text = """
ОНОВЛЕНО ГПВ НА 09 ГРУДНЯ (оновлено о 05:34)
За вказівкою НЕК «Укренерго»...
1.1: 00:00 – 02:00, 06:00 – 11:00, 15:00 – 20:00
1.2: 00:00 – 00:30, 06:00 – 11:00, 15:00 – 20:00
... (остальные строки)
"""

result = parse_schedule(raw_text)

# Сохраняем в JSON (который потом заберет фронтенд)
with open('schedule.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=4)

print("JSON успешно создан!")