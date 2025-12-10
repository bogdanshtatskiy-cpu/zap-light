import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3

# Отключаем предупреждения SSL (для сайта облэнерго)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.zoe.com.ua/графіки-погодинних-стабілізаційних/"

def get_html():
    print(f"📡 Подключаемся к {URL}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    try:
        response = requests.get(URL, headers=headers, timeout=30, verify=False)
        response.encoding = 'utf-8' # Принудительно ставим UTF-8
        return response.text
    except Exception as e:
        print(f"❌ Ошибка сети: {e}")
        return None

def parse_text_stream(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Находим главный контент (обычно это article или div с классом entry-content)
    # Если не находим, берем body целиком
    content = soup.find('article') or soup.find('div', class_='entry-content') or soup.body
    
    if not content:
        print("❌ Не найден контент на странице")
        return []

    # Получаем весь текст построчно, разделяя параграфы
    text = content.get_text(separator="\n")
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    print(f"📄 Прочитано строк: {len(lines)}")

    schedules = []
    current_schedule = None
    
    # 1. Regex для поиска даты (поддерживаем укр. месяцы)
    months = r"(СІЧНЯ|ЛЮТОГО|БЕРЕЗНЯ|КВІТНЯ|ТРАВНЯ|ЧЕРВНЯ|ЛИПНЯ|СЕРПНЯ|ВЕРЕСНЯ|ЖОВТНЯ|ЛИСТОПАДА|ГРУДНЯ)"
    date_pattern = re.compile(rf"(\d{{1,2}})\s+{months}", re.IGNORECASE)
    
    # 2. Regex для поиска очередей (1.1: время)
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)")
    
    # 3. Regex для времени (00:00 - 02:00) с разными тире
    time_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})")

    for line in lines:
        # --- Ищем дату ---
        # Фразы типа "ОНОВЛЕНО ГПВ НА 10 ГРУДНЯ" или "10 ГРУДНЯ ... ГПВ"
        if "ГПВ" in line.upper():
            match = date_pattern.search(line)
            if match:
                day, month = match.groups()
                date_str = f"{day} {month.upper()}"
                
                # Ищем время обновления (оновлено о 10:00)
                time_update = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line)
                updated_at = time_update.group(1) if time_update else None

                # Если у нас уже собирался график, сохраняем его перед началом нового
                if current_schedule and current_schedule['queues']:
                    schedules.append(current_schedule)

                # Начинаем новый график
                current_schedule = {
                    "date": date_str,
                    "updated_at": updated_at,
                    "queues": {}
                }
                print(f"🗓  Найдена дата: {date_str} (Обновлено: {updated_at})")
                continue

        # --- Ищем очереди (только если дата уже найдена) ---
        if current_schedule:
            q_match = queue_pattern.search(line)
            if q_match:
                q_id = q_match.group(1) # 1.1
                times_raw = q_match.group(2) # 00:00 - 03:00, ...
                
                intervals = []
                # Разбиваем по запятой или точке с запятой
                parts = re.split(r"[,;]", times_raw)
                
                for part in parts:
                    t_match = time_pattern.search(part)
                    if t_match:
                        start, end = t_match.groups()
                        # Исправляем 24:00 на 00:00 для корректности (опционально)
                        intervals.append({"start": start, "end": end})
                
                if intervals:
                    current_schedule["queues"][q_id] = intervals

    # Не забываем добавить последний график после цикла
    if current_schedule and current_schedule['queues']:
        schedules.append(current_schedule)

    return schedules

# --- ЗАПУСК ---
if __name__ == "__main__":
    html_content = get_html()
    
    data = []
    if html_content:
        data = parse_text_stream(html_content)
    
    final_json = {
        "last_check": datetime.now().strftime("%d.%m %H:%M"),
        "schedules": data
    }

    # Сохраняем
    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Готово. Сохранено {len(data)} графиков в schedule.json")
    
    # Для отладки покажем первый найденный график
    if data:
        print("Пример последних данных:")
        print(json.dumps(data[0], ensure_ascii=False, indent=2))
    else:
        print("⚠️ Графики не найдены. Проверь структуру сайта.")
