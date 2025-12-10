import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Веб-версія каналу, який ти скинув (з префіксом /s/ для перегляду в браузері)
URL = "https://t.me/s/Zaporizhzhyaoblenergo_news"

def get_html():
    print(f"📡 З'єднання з {URL}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
        else:
            print(f"❌ Помилка: Статус {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Помилка мережі: {e}")
        return None

def parse_telegram(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Шукаємо всі повідомлення
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    
    if not messages:
        print("❌ Повідомлення не знайдені. Можливо, змінилася верстка.")
        return []

    print(f"📄 Знайдено повідомлень: {len(messages)}")
    
    # Збираємо всі рядки з усіх повідомлень в один список (від нових до старих)
    all_lines = []
    for msg in reversed(messages):
        # Телеграм використовує <br> для перенесення рядків
        text = msg.get_text(separator="\n")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        all_lines.extend(lines)

    return extract_schedules_from_lines(all_lines)

def extract_schedules_from_lines(lines):
    schedules = []
    current_schedule = None
    
    # 1. Регулярка для дати (наприклад "10 ГРУДНЯ" або "НА 09 ГРУДНЯ")
    months = r"(СІЧНЯ|ЛЮТОГО|БЕРЕЗНЯ|КВІТНЯ|ТРАВНЯ|ЧЕРВНЯ|ЛИПНЯ|СЕРПНЯ|ВЕРЕСНЯ|ЖОВТНЯ|ЛИСТОПАДА|ГРУДНЯ)"
    # Шукаємо число і місяць
    date_pattern = re.compile(rf"(\d{{1,2}})\s+{months}", re.IGNORECASE)
    
    # 2. Регулярка для черги (1.1: або 1.1 - ...)
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)")
    
    # 3. Регулярка для часу (00:00 - 02:00) з підтримкою різних тире
    time_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})")

    for line in lines:
        # Прибираємо нерозривні пробіли, які любить Телеграм
        clean_line = line.replace('\xa0', ' ')
        
        # --- Шукаємо дату ---
        # Якщо в рядку є слово "ГПВ" і дата
        if "ГПВ" in clean_line.upper():
            match = date_pattern.search(clean_line)
            if match:
                day, month = match.groups()
                date_str = f"{day} {month.upper()}"
                
                # Перевіряємо, чи не обробляли ми вже цю дату (щоб не дублювати)
                if any(s['date'] == date_str for s in schedules):
                    continue

                # Шукаємо час оновлення (оновлено о 10:00), якщо є
                time_update = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", clean_line, re.IGNORECASE)
                updated_at = time_update.group(1) if time_update else datetime.now().strftime("%H:%M")

                # Якщо у нас вже збирався графік, зберігаємо його
                if current_schedule and current_schedule['queues']:
                    schedules.append(current_schedule)

                # Створюємо нову картку графіка
                current_schedule = {
                    "date": date_str,
                    "updated_at": updated_at,
                    "queues": {}
                }
                print(f"🗓  Знайдено дату: {date_str}")
                continue

        # --- Шукаємо черги ---
        if current_schedule:
            q_match = queue_pattern.search(clean_line)
            if q_match:
                q_id = q_match.group(1) # наприклад "1.1"
                times_raw = q_match.group(2) # "00:00 - 05:00, ..."
                
                intervals = []
                # Розбиваємо рядок по комі або крапці з комою
                parts = re.split(r"[,;]", times_raw)
                for part in parts:
                    t_match = time_pattern.search(part)
                    if t_match:
                        start, end = t_match.groups()
                        intervals.append({"start": start, "end": end})
                
                if intervals:
                    current_schedule["queues"][q_id] = intervals

    # Додаємо останній знайдений графік
    if current_schedule and current_schedule['queues']:
        # Ще одна перевірка на дублікат
        if not any(s['date'] == current_schedule['date'] for s in schedules):
            schedules.append(current_schedule)

    return schedules

# --- ЗАПУСК ---
if __name__ == "__main__":
    html_content = get_html()
    
    data = []
    if html_content:
        data = parse_telegram(html_content)
    
    # Беремо тільки 2 останні актуальні графіки (наприклад, на сьогодні і завтра)
    # Щоб файл не розростався
    data = data[:2]

    final_json = {
        "last_check": datetime.now().strftime("%d.%m %H:%M"),
        "schedules": data
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Готово. Збережено {len(data)} графіків.")
    if len(data) > 0:
        print(f"   Останній: {data[0]['date']}")
