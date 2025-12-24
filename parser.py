import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ==========================
# ⚙️ НАСТРОЙКИ
# ==========================

# Список каналов для парсинга
CHANNELS = [
    "https://t.me/s/Zaporizhzhyaoblenergo_news",  # Официальный
    "https://t.me/s/info_zp"                      # Альтернативный
]

# Ключевые слова (корни слов для поиска)
KEYWORDS = [
    "ГПВ", "ГРАФІК", "ВІДКЛЮЧЕН", "ЕЛЕКТРО", "ЧЕРГ", 
    "ОНОВЛЕН", "ЗМІН", "ОБЛЕНЕРГО", "УКРЕНЕРГО", "СВІТЛ"
]

# Маппинг месяцев (Родительный падеж -> Число)
UA_MONTHS = {
    "СІЧНЯ": 1, "ЛЮТОГО": 2, "БЕРЕЗНЯ": 3, "КВІТНЯ": 4, "ТРАВНЯ": 5, "ЧЕРВНЯ": 6,
    "ЛИПНЯ": 7, "СЕРПНЯ": 8, "ВЕРЕСНЯ": 9, "ЖОВТНЯ": 10, "ЛИСТОПАДА": 11, "ГРУДНЯ": 12
}

# Обратный маппинг (Число -> Название) для формирования ключа даты
UA_MONTHS_REVERSE = {v: k for k, v in UA_MONTHS.items()}

# ==========================
# 🛠 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================

def get_kiev_time():
    """Получает текущее время UTC и добавляет 2 часа"""
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
    # Ищем блоки сообщений Telegram Web
    message_wraps = soup.find_all('div', class_='tgme_widget_message_wrap')
    
    found_schedules = []

    # === РЕГУЛЯРНЫЕ ВЫРАЖЕНИЯ ===
    months_regex = "|".join(UA_MONTHS.keys())
    # Поиск даты: "25 ГРУДНЯ"
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    # Поиск очереди: "1.1: ..."
    queue_pattern = re.compile(r"^(\d\.\d)\s*[:]\s*(.*)")
    # Поиск времени: "00:00 - 04:00" (поддержка разных тире)
    time_pattern = re.compile(r"(\d{1,2}:\d{2})\s*[-–—−]\s*(\d{1,2}:\d{2})")

    # Перебираем сообщения (reversed = снизу вверх, но логика merge потом выберет лучшее)
    for wrap in reversed(message_wraps):
        text_div = wrap.find('div', class_='tgme_widget_message_text')
        if not text_div: continue
        text = text_div.get_text(separator="\n")

        # Отсеиваем лишние посты без ключевых слов
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

        # --- 1. ПАРСИНГ СТРОК ---
        for line in lines:
            # А. Ищем явную дату в тексте (например "25 ГРУДНЯ")
            if not explicit_date_key:
                match = date_pattern.search(line)
                if match:
                    day, month = match.groups()
                    explicit_date_key = f"{day} {month.upper()}"

            # Б. Ищем время обновления (Оновлено о ...)
            if not updated_at_val:
                time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                if time_upd_match:
                    updated_at_val = time_upd_match.group(1)

            # В. Ищем очереди и время
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

        # --- 2. ОБРАБОТКА РЕЗУЛЬТАТОВ ---
        if queues_found:
            final_date_key = None

            if explicit_date_key:
                # Если дата была в тексте — используем её
                final_date_key = explicit_date_key
            else:
                # ФОЛЛБЭК: Если даты нет, используем дату поста
                try:
                    dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                    dt_kiev = dt + timedelta(hours=2) # Конвертация в Киевское время

                    # === ВАЖНОЕ ИСПРАВЛЕНИЕ: Логика "Завтра" ===
                    # Если в тексте есть слово "завтра" (и нет явной даты), 
                    # прибавляем 1 день к дате поста.
                    if "завтра" in text.lower():
                        dt_kiev += timedelta(days=1)
                        print(f"ℹ️ Найден маркер 'завтра'. Дата смещена на {dt_kiev.strftime('%d.%m')}")

                    day = dt_kiev.day
                    month_name = UA_MONTHS_REVERSE.get(dt_kiev.month, "ГРУДНЯ")
                    final_date_key = f"{day} {month_name}"
                except Exception as e:
                    print(f"⚠️ Ошибка вычисления даты: {e}")
                    continue

            # Если время обновления не нашли в тексте, берем время поста
            if not updated_at_val:
                try:
                    dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                    dt_kiev = dt + timedelta(hours=2)
                    updated_at_val = dt_kiev.strftime("%H:%M")
                except:
                    updated_at_val = "??:??"

            # Добавляем найденный график
            found_schedules.append({
                "date": final_date_key,
                "queues": queues_found,
                "updated_at": updated_at_val,
                "source_ts": post_timestamp
            })

    return found_schedules

def merge_schedules(all_schedules):
    """
    Объединяет графики. Если на одну дату есть несколько постов,
    выбирает тот, который был опубликован позже (source_ts).
    """
    merged = {}
    for sch in all_schedules:
        d_key = sch['date']
        if d_key not in merged:
            merged[d_key] = sch
        else:
            # Сравниваем время публикации постов
            existing_ts = merged[d_key]['source_ts']
            new_ts = sch['source_ts']
            
            # Строковое сравнение ISO дат работает корректно
            if new_ts > existing_ts:
                print(f"🔄 Обновляем график на {d_key} из более свежего поста.")
                merged[d_key] = sch
            else:
                pass 

    return list(merged.values())

def main():
    all_found = []
    
    # 1. Парсим все каналы
    for url in CHANNELS:
        print(f"📡 Парсинг {url}...")
        res = parse_channel(url)
        print(f"   Найдено {len(res)} графиков.")
        all_found.extend(res)

    # 2. Объединяем и удаляем дубликаты
    final_list = merge_schedules(all_found)

    # 3. Сортировка по дате
    def date_sorter(item):
        try:
            parts = item['date'].split()
            day = int(parts[0])
            month_str = parts[1]
            month = UA_MONTHS.get(month_str, 0)
            now = datetime.now()
            year = now.year
            
            # Обработка перехода года (Если сейчас Декабрь, а месяц Январь -> след. год)
            if now.month == 12 and month == 1:
                year += 1
            # Если сейчас Январь, а месяц Декабрь -> прошлый год (чтобы не улетел в будущее)
            elif now.month == 1 and month == 12:
                year -= 1
                
            return datetime(year, month, day)
        except:
            return datetime.now()

    final_list.sort(key=date_sorter)
    
    # Берем последние 3 дня (Вчера, Сегодня, Завтра)
    final_list = final_list[-3:]

    # 4. Формируем итоговый JSON
    output_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": final_list
    }

    # Удаляем служебное поле source_ts перед сохранением
    for item in output_json["schedules"]:
        if "source_ts" in item:
            del item["source_ts"]

    # 5. Сохраняем
    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Сохранено {len(final_list)} графиков в schedule.json")

if __name__ == "__main__":
    main()
