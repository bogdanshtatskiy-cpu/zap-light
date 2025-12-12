import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# === НАСТРОЙКИ ===
# Список каналов для парсинга
CHANNELS = [
    "https://t.me/s/Zaporizhzhyaoblenergo_news",  # Официальный
    "https://t.me/s/info_zp"                      # Альтернативный
]

# Ключевые слова, чтобы понять, что пост про график
KEYWORDS = ["ГПВ", "ГРАФІК", "ВІДКЛЮЧЕННЯ", "ЕЛЕКТРОПОСТАЧАННЯ", "ЧЕРГАМ"]

# Маппинг месяцев
UA_MONTHS = {
    "СІЧНЯ": 1, "ЛЮТОГО": 2, "БЕРЕЗНЯ": 3, "КВІТНЯ": 4, "ТРАВНЯ": 5, "ЧЕРВНЯ": 6,
    "ЛИПНЯ": 7, "СЕРПНЯ": 8, "ВЕРЕСНЯ": 9, "ЖОВТНЯ": 10, "ЛИСТОПАДА": 11, "ГРУДНЯ": 12
}

def get_kiev_time():
    """Получает текущее время UTC и добавляет 2 часа (зимнее время)"""
    return datetime.utcnow() + timedelta(hours=2)

def get_html(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def parse_channel(url):
    html = get_html(url)
    if not html: return []

    soup = BeautifulSoup(html, 'html.parser')
    # Ищем блоки сообщений
    message_wraps = soup.find_all('div', class_='tgme_widget_message_wrap')
    
    found_schedules = []

    # Регулярки
    months_regex = "|".join(UA_MONTHS.keys())
    # Ищем дату (число + месяц)
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    # Ищем очереди (1.1: время)
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)")
    # Ищем время (00:00 - 05:00)
    time_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})")

    for wrap in reversed(message_wraps):
        # 1. Получаем текст сообщения
        text_div = wrap.find('div', class_='tgme_widget_message_text')
        if not text_div: continue
        text = text_div.get_text(separator="\n")

        # Проверка на ключевые слова (отсеиваем мусор)
        if not any(k in text.upper() for k in KEYWORDS):
            continue

        # 2. Получаем время публикации (timestamp)
        # Это критически важно для определения "свежести"
        time_tag = wrap.find('time')
        post_timestamp = ""
        if time_tag and time_tag.has_attr('datetime'):
            post_timestamp = time_tag['datetime'] # ISO format string
        else:
            continue # Без времени пост нам не нужен

        lines = [line.strip().replace('\xa0', ' ') for line in text.split('\n') if line.strip()]
        
        current_date_key = None
        schedule_data = {"queues": {}, "updated_at": None, "source_ts": post_timestamp}

        # 3. Ищем дату в тексте
        for line in lines:
            match = date_pattern.search(line)
            if match:
                day, month = match.groups()
                current_date_key = f"{day} {month.upper()}"
                
                # Пытаемся найти время обновления в тексте (иногда пишут "Оновлено о 10:00")
                time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                if time_upd_match:
                    schedule_data["updated_at"] = time_upd_match.group(1)
                break
        
        if not current_date_key:
            continue # Дата не найдена

        # Если updated_at не нашли в тексте, берем время поста (конвертируем в HH:MM)
        if not schedule_data["updated_at"]:
            try:
                # post_timestamp example: 2023-12-13T08:00:00+00:00
                dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                # Конвертируем в Киев (+2)
                dt_kiev = dt + timedelta(hours=2)
                schedule_data["updated_at"] = dt_kiev.strftime("%H:%M")
            except:
                schedule_data["updated_at"] = "??:??"

        # 4. Парсим очереди
        for line in lines:
            q_match = queue_pattern.search(line)
            if q_match:
                q_id = q_match.group(1)
                times_raw = q_match.group(2)
                
                intervals = []
                # Разбиваем по запятой или точке с запятой
                parts = re.split(r"[,;]", times_raw)
                for part in parts:
                    t_match = time_pattern.search(part)
                    if t_match:
                        start, end = t_match.groups()
                        intervals.append({"start": start, "end": end})
                
                if intervals:
                    schedule_data["queues"][q_id] = intervals

        # Если нашли очереди, добавляем в список
        if schedule_data["queues"]:
            schedule_data["date"] = current_date_key
            found_schedules.append(schedule_data)

    return found_schedules

def merge_schedules(all_schedules):
    """
    Объединяет графики из разных источников.
    Если есть дубликаты по дате, выбирает тот, у которого 'source_ts' (время поста) новее.
    """
    merged = {}

    for sch in all_schedules:
        d_key = sch['date']
        
        # Если такой даты еще нет - добавляем
        if d_key not in merged:
            merged[d_key] = sch
        else:
            # КОНФЛИКТ: Дата уже есть. Сравниваем время публикации.
            existing_ts = merged[d_key]['source_ts']
            new_ts = sch['source_ts']
            
            # Строковое сравнение ISO дат работает корректно (2025-12-13T10... > 2025-12-13T09...)
            if new_ts > existing_ts:
                print(f"🔄 Replacing schedule for {d_key} with newer version from another source.")
                merged[d_key] = sch
            else:
                # Старый график свежее или такой же
                pass

    return list(merged.values())

def main():
    all_found = []
    
    # 1. Парсим все каналы
    for url in CHANNELS:
        print(f"📡 Parsing {url}...")
        res = parse_channel(url)
        print(f"   Found {len(res)} schedules.")
        all_found.extend(res)

    # 2. Объединяем и выбираем самые свежие
    final_list = merge_schedules(all_found)

    # 3. Сортируем по дате (чтобы шли: Вчера, Сегодня, Завтра)
    def date_sorter(item):
        parts = item['date'].split()
        day = int(parts[0])
        month_str = parts[1]
        month = UA_MONTHS.get(month_str, 0)
        now = datetime.now()
        year = now.year
        # Если сейчас Декабрь, а месяц Январь -> это следующий год
        if now.month == 12 and month == 1:
            year += 1
        return datetime(year, month, day)

    final_list.sort(key=date_sorter)
    
    # Берем последние 3 (на случай если спарсилось много старого)
    final_list = final_list[-3:]

    # 4. Формируем итоговый JSON
    output_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": final_list
    }

    # Удаляем служебное поле source_ts перед сохранением (оно нужно было только для логики)
    for item in output_json["schedules"]:
        if "source_ts" in item:
            del item["source_ts"]

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Saved {len(final_list)} unique schedules to schedule.json")

if __name__ == "__main__":
    main()
