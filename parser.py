import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.zoe.com.ua/графіки-погодинних-стабілізаційних/"

def clean_text(text):
    """Убирает лишние пробелы и неразрывные пробелы"""
    return text.replace('\xa0', ' ').strip()

def parse_zoe_site():
    print(f"Загрузка страницы {URL}...")
    try:
        response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return None

    schedules = []
    
    # Ищем все параграфы <p>
    paragraphs = soup.find_all('p')
    
    for i, p in enumerate(paragraphs):
        text = clean_text(p.get_text())
        
        # 1. Ищем заголовок даты
        # Паттерны: "ОНОВЛЕНО ГПВ НА..." или "...ДІЯТИМУТЬ ГПВ"
        date_match = re.search(r"(\d{1,2}\s+[А-ЯІЇЄа-яіїє]+)", text, re.IGNORECASE)
        is_header = "ГПВ" in text.upper() and date_match
        
        if is_header:
            date_str = date_match.group(1).upper()
            
            # Проверяем, есть ли пометка об обновлении
            update_match = re.search(r"\(оновлено о (\d{2}:\d{2})\)", text)
            updated_at = update_match.group(1) if update_match else None
            
            print(f"Нашли заголовок для даты: {date_str}")

            # 2. Данные обычно лежат в СЛЕДУЮЩЕМ параграфе <p>
            if i + 1 < len(paragraphs):
                next_p = paragraphs[i + 1]
                # Разбиваем содержимое следующего параграфа по тегам <br>
                lines = [clean_text(line) for line in next_p.get_text(separator="\n").split('\n')]
                
                queues_data = {}
                # Регулярка для очередей (1.1: 00:00 - 02:00...)
                queue_pattern = re.compile(r"(\d\.\d)\s*[:]\s*(.*)")
                
                for line in lines:
                    match = queue_pattern.search(line)
                    if match:
                        q_id = match.group(1)
                        times_raw = match.group(2)
                        
                        intervals = []
                        # Разбиваем по запятой
                        for part in times_raw.split(','):
                            # Ищем время ХХ:ХХ - ХХ:ХХ (поддерживаем разные тире)
                            t_match = re.search(r"(\d{2}:\d{2})\s*[-–]\s*(\d{2}:\d{2})", part)
                            if t_match:
                                intervals.append({
                                    "start": t_match.group(1),
                                    "end": t_match.group(2)
                                })
                        
                        if intervals:
                            queues_data[q_id] = intervals
                
                if queues_data:
                    schedules.append({
                        "date": date_str,
                        "updated_at": updated_at,
                        "queues": queues_data
                    })

    return schedules

if __name__ == "__main__":
    data = parse_zoe_site()
    
    final_json = {
        "last_check": datetime.now().strftime("%d.%m %H:%M"),
        "schedules": data if data else []
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)
        
    print(f"Сохранено графиков: {len(data) if data else 0}")
