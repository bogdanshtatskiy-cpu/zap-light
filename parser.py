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

# Ключевые слова (используем корни слов для надежности)
# ГПВ - стандарт
# ГРАФІК - ловит "графік", "графіку", "графіки"
# ВІДКЛЮЧЕН - ловит "відключення", "відключено"
# ЕЛЕКТРО - ловит "електропостачання", "електроенергія"
# ЧЕРГ - ловит "черга", "черги", "чергам", "по чергах"
# ОНОВЛЕН - ловит "оновлено", "оновлення" (важно для info_zp)
# ЗМІН - ловит "зміни", "змінено"
# ОБЛЕНЕРГО - часто пишут в заголовке
KEYWORDS = [
    "ГПВ", "ГРАФІК", "ВІДКЛЮЧЕН", "ЕЛЕКТРО", "ЧЕРГ", 
    "ОНОВЛЕН", "ЗМІН", "ОБЛЕНЕРГО", "УКРЕНЕРГО", "СВІТЛ"
]

# Маппинг месяцев
UA_MONTHS = {
    "СІЧНЯ": 1, "ЛЮТОГО": 2, "БЕРЕЗНЯ": 3, "КВІТНЯ": 4, "ТРАВНЯ": 5, "ЧЕРВНЯ": 6,
    "ЛИПНЯ": 7, "СЕРПНЯ": 8, "ВЕРЕСНЯ": 9, "ЖОВТНЯ": 10, "ЛИСТОПАДА": 11, "ГРУДНЯ": 12
}
# Обратный маппинг (Число -> Название) для формирования ключа даты из timestamp
UA_MONTHS_REVERSE = {v: k for k, v in UA_MONTHS.items()}

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
    message_wraps = soup.find_all('div', class_='tgme_widget_message_wrap')
    
    found_schedules = []

    # Регулярки
    months_regex = "|".join(UA_MONTHS.keys())
    # Ищем дату (число + месяц)
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    # Ищем очереди (1.1: время)
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)")
    # Ищем время (поддержка дефиса, тире, минуса)
    time_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–—−]\s*(\d{1,2}:\d{2})")

    for wrap in reversed(message_wraps):
        text_div = wrap.find('div', class_='tgme_widget_message_text')
        if not text_div: continue
        text = text_div.get_text(separator="\n")

        # Проверка на ключевые слова
        # Теперь ищет вхождения корней (например "ОНОВЛЕН" найдет в "Оновлення")
        if not any(k in text.upper() for k in KEYWORDS):
            continue

        # Получаем время публикации (timestamp)
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

        # 1. Сначала парсим очереди и ищем явную дату в тексте
        for line in lines:
            # Ищем дату в тексте (например "13 ГРУДНЯ")
            if not explicit_date_key:
                match = date_pattern.search(line)
                if match:
                    day, month = match.groups()
                    explicit_date_key = f"{day} {month.upper()}"

            # Ищем время обновления (Оновлено о ...)
            if not updated_at_val:
                time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                if time_upd_match:
                    updated_at_val = time_upd_match.group(1)

            # Парсим очереди
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
                    queues_found[q_id] = intervals

        # 2. Если мы нашли очереди (ГЛАВНОЕ УСЛОВИЕ), сохраняем график
        # Даже если ключевое слово было "Ви не повірите", но внутри есть "1.1: 00-04", мы это берем.
        if queues_found:
            final_date_key = None

            if explicit_date_key:
                # Если в тексте была дата - берем её
                final_date_key = explicit_date_key
            else:
                # ФОЛЛБЭК: Если даты в тексте нет (посты типа "Оновлено графік"),
                # берем дату из timestamp сообщения (по Киевскому времени)
                try:
                    dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                    dt_kiev = dt + timedelta(hours=2)
                    day = dt_kiev.day
                    month_name = UA_MONTHS_REVERSE.get(dt_kiev.month, "ГРУДНЯ")
                    final_date_key = f"{day} {month_name}"
                except Exception as e:
                    print(f"⚠️ Date fallback error: {e}")
                    continue

            # Если время обновления не нашли в тексте, берем время поста
            if not updated_at_val:
                try:
                    dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                    dt_kiev = dt + timedelta(hours=2)
                    updated_at_val = dt_kiev.strftime("%H:%M")
                except:
                    updated_at_val = "??:??"

            # Сохраняем результат
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
            # Если дата совпадает, берем более свежий пост
            existing_ts = merged[d_key]['source_ts']
            new_ts = sch['source_ts']
            if new_ts > existing_ts:
                print(f"🔄 Updated {d_key} from newer post.")
                merged[d_key] = sch
    return list(merged.values())

def main():
    all_found = []
    
    for url in CHANNELS:
        print(f"📡 Parsing {url}...")
        res = parse_channel(url)
        print(f"   Found {len(res)} schedules.")
        all_found.extend(res)

    final_list = merge_schedules(all_found)

    # Сортировка по дате
    def date_sorter(item):
        try:
            parts = item['date'].split()
            day = int(parts[0])
            month_str = parts[1]
            month = UA_MONTHS.get(month_str, 0)
            now = datetime.now()
            year = now.year
            # Переход года (декабрь -> январь)
            if now.month == 12 and month == 1:
                year += 1
            return datetime(year, month, day)
        except:
            return datetime.now()

    final_list.sort(key=date_sorter)
    final_list = final_list[-3:]

    output_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": final_list
    }

    # Чистим служебные поля
    for item in output_json["schedules"]:
        if "source_ts" in item:
            del item["source_ts"]

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Saved {len(final_list)} schedules.")

if __name__ == "__main__":
    main()
