import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Веб-версія каналу
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
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    
    if not messages:
        print("❌ Повідомлення не знайдені.")
        return []

    print(f"📄 Знайдено повідомлень: {len(messages)}")
    
    all_lines = []
    # Читаем с конца (от старых к новым), но добавляем в начало списка, 
    # чтобы новые строки были первыми для обработки
    for msg in reversed(messages):
        text = msg.get_text(separator="\n")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        all_lines.extend(lines)

    return extract_schedules_from_lines(all_lines)

def extract_schedules_from_lines(lines):
    schedules = []
    current_schedule = None
    
    months = r"(СІЧНЯ|ЛЮТОГО|БЕРЕЗНЯ|КВІТНЯ|ТРАВНЯ|ЧЕРВНЯ|ЛИПНЯ|СЕРПНЯ|ВЕРЕСНЯ|ЖОВТНЯ|ЛИСТОПАДА|ГРУДНЯ)"
    date_pattern = re.compile(rf"(\d{{1,2}})\s+{months}", re.IGNORECASE)
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)")
    time_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})")

    for line in lines:
        clean_line = line.replace('\xa0', ' ')
        
        # 1. Дата
        if "ГПВ" in clean_line.upper():
            match = date_pattern.search(clean_line)
            if match:
                day, month = match.groups()
                date_str = f"{day} {month.upper()}"
                
                # Проверка на дубликаты
                if any(s['date'] == date_str for s in schedules):
                    continue

                time_update = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", clean_line, re.IGNORECASE)
                updated_at = time_update.group(1) if time_update else datetime.now().strftime("%H:%M")

                if current_schedule and current_schedule['queues']:
                    schedules.append(current_schedule)

                current_schedule = {
                    "date": date_str,
                    "updated_at": updated_at,
                    "queues": {}
                }
                print(f"🗓  Знайдено дату: {date_str}")
                continue

        # 2. Очереди
        if current_schedule:
            q_match = queue_pattern.search(clean_line)
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
                    current_schedule["queues"][q_id] = intervals

    if current_schedule and current_schedule['queues']:
        if not any(s['date'] == current_schedule['date'] for s in schedules):
            schedules.append(current_schedule)

    return schedules

if __name__ == "__main__":
    html_content = get_html()
    data = []
    if html_content:
        data = parse_telegram(html_content)
    
    # --- ВАЖНО: БЕРЕМ 7 ПОСЛЕДНИХ ДНЕЙ ---
    data = data[:7]

    final_json = {
        "last_check": datetime.now().strftime("%d.%m %H:%M"),
        "schedules": data
    }

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Готово. Збережено {len(data)} графіків.")
