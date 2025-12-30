import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ==========================
# ⚙️ НАСТРОЙКИ
# ==========================

# Список каналов
CHANNELS = [
    "https://t.me/s/Zaporizhzhyaoblenergo_news",  # Официальный
    "https://t.me/s/info_zp"                      # Альтернативный
]

# Ключевые слова для поиска постов
KEYWORDS = [
    "ГПВ", "ГРАФІК", "ВІДКЛЮЧЕН", "ЕЛЕКТРО", "ЧЕРГ", 
    "ОНОВЛЕН", "ЗМІН", "ОБЛЕНЕРГО", "УКРЕНЕРГО", "СВІТЛ"
]

# Маппинг месяцев
UA_MONTHS = {
    "СІЧНЯ": 1, "ЛЮТОГО": 2, "БЕРЕЗНЯ": 3, "КВІТНЯ": 4, "ТРАВНЯ": 5, "ЧЕРВНЯ": 6,
    "ЛИПНЯ": 7, "СЕРПНЯ": 8, "ВЕРЕСНЯ": 9, "ЖОВТНЯ": 10, "ЛИСТОПАДА": 11, "ГРУДНЯ": 12
}
UA_MONTHS_REVERSE = {v: k for k, v in UA_MONTHS.items()}

# Маппинг полных очередей на под-очереди
# Если напишут "1 черга", это значит и 1.1, и 1.2
QUEUE_GROUPS = {
    "1": ["1.1", "1.2"],
    "2": ["2.1", "2.2"],
    "3": ["3.1", "3.2"],
    "4": ["4.1", "4.2"],
    "5": ["5.1", "5.2"],
    "6": ["6.1", "6.2"]
}

# ==========================
# 🛠 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================

def get_kiev_time():
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
    date_pattern = re.compile(rf"(\d{{1,2}})\s+({months_regex})", re.IGNORECASE)
    
    # Поиск времени: "00:00 - 04:00" (поддержка разных тире и точек 00.00)
    time_pattern = re.compile(r"(\d{1,2}[:.]\d{2})\s*[-–—−]\s*(\d{1,2}[:.]\d{2})")
    
    # Поиск конкретных очередей (1.1, 2.1)
    specific_queue_pattern = re.compile(r"\b([1-6]\.[12])\b")
    
    # Поиск общих очередей (Черга 1, 1 черга, просто 1:)
    general_queue_pattern = re.compile(r"(?:черг[аиy]\s*)?(\d)\b")

    for wrap in reversed(message_wraps):
        text_div = wrap.find('div', class_='tgme_widget_message_text')
        if not text_div: continue
        text = text_div.get_text(separator="\n")

        if not any(k in text.upper() for k in KEYWORDS):
            continue

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

        # --- АНАЛИЗ СТРОК ---
        for line in lines:
            # 1. Ищем дату
            if not explicit_date_key:
                match = date_pattern.search(line)
                if match:
                    day, month = match.groups()
                    explicit_date_key = f"{day} {month.upper()}"

            # 2. Ищем время обновления
            if not updated_at_val:
                time_upd_match = re.search(r"\(оновлено.*(\d{2}:\d{2})\)", line, re.IGNORECASE)
                if time_upd_match:
                    updated_at_val = time_upd_match.group(1)

            # 3. Ищем графики
            # Стратегия: если в строке есть ВРЕМЯ (00:00 - 04:00), значит в ней должны быть и ОЧЕРЕДИ
            time_matches = list(time_pattern.finditer(line))
            
            if time_matches:
                # Нашли временные интервалы в этой строке
                intervals = []
                for tm in time_matches:
                    start, end = tm.groups()
                    # Заменяем точки на двоеточия если нужно (09.00 -> 09:00)
                    start = start.replace('.', ':')
                    end = end.replace('.', ':')
                    intervals.append({"start": start, "end": end})

                # Теперь ищем какие очереди в этой строке (ДО времени)
                # Берем часть строки до первого времени
                text_before_time = line[:time_matches[0].start()]
                
                # А. Ищем явные под-очереди (1.1, 1.2...)
                found_sub_queues = specific_queue_pattern.findall(text_before_time)
                
                # Б. Ищем общие очереди (1, 2...), если явных не нашли или они смешаны
                found_general_queues = []
                # Ищем просто цифры 1-6, которые похожи на перечисление очередей
                # Например: "1 черга:", "Черги 1, 2:"
                possible_generals = general_queue_pattern.findall(text_before_time)
                for g in possible_generals:
                    if 1 <= int(g) <= 6:
                        found_general_queues.append(g)

                # Заполняем результат
                target_queues = set()
                
                # Если нашли конкретные (1.1), добавляем их
                for q in found_sub_queues:
                    target_queues.add(q)
                
                # Если нашли общие (1), разворачиваем их в (1.1, 1.2)
                # Но только если эта "1" не является частью "1.1" (regex \b должен был это обработать, но подстрахуемся)
                for g in found_general_queues:
                    # Если мы уже нашли 1.1 и 1.2, то "1" нам не нужна. 
                    # Но если нашли только "1", значит это группа.
                    # Простая логика: добавляем всё из группы
                    for sub in QUEUE_GROUPS[g]:
                        # Если этой под-очереди еще нет в списке (чтобы не дублировать, если было написано "1.1 и 1 черга")
                        if sub not in found_sub_queues: 
                            target_queues.add(sub)

                # Привязываем интервалы к найденным очередям
                for q_id in target_queues:
                    if q_id not in queues_found:
                        queues_found[q_id] = []
                    queues_found[q_id].extend(intervals)

        # --- ОБРАБОТКА РЕЗУЛЬТАТОВ ---
        if queues_found:
            final_date_key = None

            if explicit_date_key:
                final_date_key = explicit_date_key
            else:
                try:
                    dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                    dt_kiev = dt + timedelta(hours=2)

                    # Логика "Завтра"
                    if "завтра" in text.lower():
                        dt_kiev += timedelta(days=1)
                        print(f"ℹ️ Маркер 'завтра'. Дата: {dt_kiev.strftime('%d.%m')}")

                    day = dt_kiev.day
                    month_name = UA_MONTHS_REVERSE.get(dt_kiev.month, "ГРУДНЯ")
                    final_date_key = f"{day} {month_name}"
                except Exception as e:
                    print(f"⚠️ Date error: {e}")
                    continue

            if not updated_at_val:
                try:
                    dt = datetime.fromisoformat(post_timestamp.replace('Z', '+00:00'))
                    dt_kiev = dt + timedelta(hours=2)
                    updated_at_val = dt_kiev.strftime("%H:%M")
                except:
                    updated_at_val = "??:??"

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
            existing_ts = merged[d_key]['source_ts']
            new_ts = sch['source_ts']
            if new_ts > existing_ts:
                print(f"🔄 Обновление {d_key} (свежий пост).")
                merged[d_key] = sch
    return list(merged.values())

def main():
    all_found = []
    
    for url in CHANNELS:
        print(f"📡 Парсинг {url}...")
        res = parse_channel(url)
        print(f"   Найдено {len(res)} графиков.")
        all_found.extend(res)

    final_list = merge_schedules(all_found)

    def date_sorter(item):
        try:
            parts = item['date'].split()
            day = int(parts[0])
            month_str = parts[1]
            month = UA_MONTHS.get(month_str, 0)
            now = datetime.now()
            year = now.year
            if now.month == 12 and month == 1: year += 1
            elif now.month == 1 and month == 12: year -= 1
            return datetime(year, month, day)
        except:
            return datetime.now()

    final_list.sort(key=date_sorter)
    final_list = final_list[-3:]

    output_json = {
        "last_check": get_kiev_time().strftime("%d.%m %H:%M"),
        "schedules": final_list
    }

    for item in output_json["schedules"]:
        if "source_ts" in item:
            del item["source_ts"]

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Сохранено {len(final_list)} графиков.")

if __name__ == "__main__":
    main()
