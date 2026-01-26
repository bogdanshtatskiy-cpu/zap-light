const ICON_BASE_URL = "https://basmilius.github.io/weather-icons/production/fill/all/";

// Запитуємо 14 днів вперед (максимум для більшості параметрів)
// past_days=2 для вчора/сьогодні
const WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast?latitude=47.8388&longitude=35.1396&current=temperature_2m,apparent_temperature,weather_code,is_day&hourly=temperature_2m,weather_code,is_day&timezone=auto&forecast_days=14&past_days=2";

const WMO_CODES = {
    0:  { uk: "Ясно", ru: "Ясно", img: "clear-day.svg", img_night: "clear-night.svg" },
    1:  { uk: "Переважно ясно", ru: "Преим. ясно", img: "partly-cloudy-day.svg", img_night: "partly-cloudy-night.svg" },
    2:  { uk: "Мінлива хмарність", ru: "Облачно", img: "partly-cloudy-day.svg", img_night: "partly-cloudy-night.svg" },
    3:  { uk: "Похмуро", ru: "Пасмурно", img: "overcast.svg", img_night: "overcast.svg" },
    45: { uk: "Туман", ru: "Туман", img: "fog.svg", img_night: "fog.svg" }, 
    48: { uk: "Туман паморозь", ru: "Туман, иней", img: "fog.svg", img_night: "fog.svg" },
    51: { uk: "Мряка", ru: "Морось", img: "drizzle.svg", img_night: "drizzle.svg" },
    53: { uk: "Мряка", ru: "Морось", img: "drizzle.svg", img_night: "drizzle.svg" },
    55: { uk: "Щільна мряка", ru: "Сил. морось", img: "drizzle.svg", img_night: "drizzle.svg" },
    61: { uk: "Слабкий дощ", ru: "Слаб. дождь", img: "rain.svg", img_night: "rain.svg" },
    63: { uk: "Дощ", ru: "Дождь", img: "rain.svg", img_night: "rain.svg" },
    65: { uk: "Сильний дощ", ru: "Сил. дождь", img: "rain.svg", img_night: "rain.svg" },
    71: { uk: "Слабкий сніг", ru: "Слаб. снег", img: "snow.svg", img_night: "snow.svg" },
    73: { uk: "Сніг", ru: "Снег", img: "snow.svg", img_night: "snow.svg" },
    75: { uk: "Сильний сніг", ru: "Сил. снег", img: "snow.svg", img_night: "snow.svg" },
    77: { uk: "Снігові зерна", ru: "Снеж. зерна", img: "hail.svg", img_night: "hail.svg" },
    80: { uk: "Злива", ru: "Ливень", img: "rain.svg", img_night: "rain.svg" },
    81: { uk: "Злива", ru: "Ливень", img: "rain.svg", img_night: "rain.svg" },
    82: { uk: "Сильна злива", ru: "Сил. ливень", img: "thunderstorms-rain.svg", img_night: "thunderstorms-rain.svg" },
    85: { uk: "Снігопад", ru: "Снегопад", img: "snow.svg", img_night: "snow.svg" },
    86: { uk: "Сильний снігопад", ru: "Сил. снегопад", img: "snow.svg", img_night: "snow.svg" },
    95: { uk: "Гроза", ru: "Гроза", img: "thunderstorms.svg", img_night: "thunderstorms.svg" },
    96: { uk: "Гроза з градом", ru: "Гроза, град", img: "thunderstorms-overcast-rain.svg", img_night: "thunderstorms-overcast-rain.svg" },
    99: { uk: "Гроза з градом", ru: "Гроза, град", img: "thunderstorms-overcast-rain.svg", img_night: "thunderstorms-overcast-rain.svg" }
};

let weatherData = null;
let currentViewingDateStr = null;

async function initWeather() {
    // Відновлення видимості (з localStorage)
    const isHidden = localStorage.getItem('weatherHidden') === 'true';
    const widget = document.getElementById('weather-widget');
    const toggleBtn = document.getElementById('weather-toggle');
    
    if (widget && toggleBtn) {
        if (isHidden) {
            widget.classList.add('hidden');
            toggleBtn.classList.remove('active');
        } else {
            widget.classList.remove('hidden');
            toggleBtn.classList.add('active');
        }
    }

    try {
        const res = await fetch(WEATHER_API_URL);
        if (!res.ok) throw new Error("Weather API Error");
        weatherData = await res.json();
        
        // Якщо вже є обрана дата (наприклад, з index.html), рендеримо її
        if (currentViewingDateStr) {
            renderWeatherForDate(currentViewingDateStr);
        } else {
            // Інакше беремо сьогоднішню
            const today = new Date();
            const months = ["СІЧНЯ", "ЛЮТОГО", "БЕРЕЗНЯ", "КВІТНЯ", "ТРАВНЯ", "ЧЕРВНЯ", "ЛИПНЯ", "СЕРПНЯ", "ВЕРЕСНЯ", "ЖОВТНЯ", "ЛИСТОПАДА", "ГРУДНЯ"];
            renderWeatherForDate(`${today.getDate()} ${months[today.getMonth()]}`);
        }

    } catch (e) {
        console.error("Weather load failed:", e);
        if (widget) widget.style.display = 'none';
        if (toggleBtn) toggleBtn.style.display = 'none';
    }
}

function toggleWeatherWidget() {
    const widget = document.getElementById('weather-widget');
    const btn = document.getElementById('weather-toggle');
    
    if (widget.classList.contains('hidden')) {
        widget.classList.remove('hidden');
        btn.classList.add('active');
        localStorage.setItem('weatherHidden', 'false');
    } else {
        widget.classList.add('hidden');
        btn.classList.remove('active');
        localStorage.setItem('weatherHidden', 'true');
    }
}

function renderWeatherForDate(dateStr) {
    if (!weatherData) {
        currentViewingDateStr = dateStr; // Запам'ятовуємо, щоб відрендерити після завантаження
        return;
    }
    currentViewingDateStr = dateStr;

    const widget = document.getElementById('weather-widget');
    const adviceBox = document.getElementById('w-advice-text');
    const hourlyContainer = document.getElementById('w-hourly');
    
    // Парсинг дати з рядка "25 СІЧНЯ"
    const targetDate = parseScheduleDate(dateStr);
    const today = new Date();
    today.setHours(0,0,0,0,0);
    targetDate.setHours(0,0,0,0,0);

    const isToday = targetDate.getTime() === today.getTime();
    
    // Шукаємо дані в масиві hourly
    const times = weatherData.hourly.time;
    let foundIndex = -1;
    let hasHourlyData = false;

    // Шукаємо індекс для 14:00 обраного дня (для загального прогнозу)
    for(let i=0; i<times.length; i++) {
        const t = new Date(times[i]);
        // Порівнюємо рік, місяць, день
        if (t.getDate() === targetDate.getDate() && 
            t.getMonth() === targetDate.getMonth() && 
            t.getFullYear() === targetDate.getFullYear()) {
            
            hasHourlyData = true; // Знайшли хоча б одну годину для цього дня
            
            if (t.getHours() === 14) {
                foundIndex = i;
            }
        }
    }

    // Якщо на 14:00 немає, беремо першу доступну годину цього дня (наприклад 00:00)
    if (foundIndex === -1 && hasHourlyData) {
        for(let i=0; i<times.length; i++) {
            const t = new Date(times[i]);
            if (t.getDate() === targetDate.getDate() && t.getMonth() === targetDate.getMonth()) {
                foundIndex = i;
                break;
            }
        }
    }

    // --- ЯКЩО ДАНИХ НЕМАЄ (далеке майбутнє) ---
    if (!hasHourlyData) {
        // Приховуємо віджет або показуємо заглушку
        // Варіант: Сховати вміст, показати текст
        document.getElementById('w-icon').innerHTML = '<span style="font-size:24px">📅</span>';
        document.getElementById('w-temp').innerText = '--°';
        document.getElementById('w-desc').innerText = (lang === 'uk' ? "Прогноз недоступний" : "Прогноз недоступен");
        document.getElementById('w-feel').innerText = '';
        if(hourlyContainer) hourlyContainer.innerHTML = '';
        if(adviceBox) adviceBox.innerText = (lang === 'uk' ? "Занадто далеко для точного прогнозу." : "Слишком далеко для точного прогноза.");
        widget.style.opacity = '0.7';
        return;
    }

    widget.style.opacity = '1';

    // Формуємо дані для відображення
    let displayData = null;

    if (isToday) {
        // Для сьогодні беремо поточні дані (current)
        const current = weatherData.current;
        displayData = {
            code: current.weather_code,
            temp: current.temperature_2m,
            isDay: current.is_day === 1,
            feel: current.apparent_temperature
        };
    } else {
        // Для інших днів беремо знайдену годину (14:00 або ранок)
        displayData = {
            code: weatherData.hourly.weather_code[foundIndex],
            temp: weatherData.hourly.temperature_2m[foundIndex],
            isDay: true, // Вдень показуємо денну іконку
            feel: weatherData.hourly.temperature_2m[foundIndex] // API не дає apparent_temperature в hourly (у цьому запиті), тому беремо просто темп.
        };
    }

    // Рендер головної картки
    const wmo = WMO_CODES[displayData.code] || WMO_CODES[0];
    const iconFile = displayData.isDay ? wmo.img : wmo.img_night;
    const iconUrl = `${ICON_BASE_URL}${iconFile}`;
    const desc = lang === 'uk' ? wmo.uk : wmo.ru;

    document.getElementById('w-icon').innerHTML = `<img src="${iconUrl}" alt="weather">`;
    document.getElementById('w-temp').innerText = `${Math.round(displayData.temp)}°`;
    document.getElementById('w-desc').innerText = desc;
    
    if (isToday) {
        document.getElementById('w-feel').innerText = `${lang === 'uk' ? 'Відчувається як' : 'Ощущается как'} ${Math.round(displayData.feel)}°`;
    } else {
        // Для майбутнього показуємо дату (наприклад, "25.01")
        const d = targetDate.getDate();
        const m = targetDate.getMonth() + 1;
        document.getElementById('w-feel').innerText = `${pad(d)}.${pad(m)}`;
    }

    // Напутнє слово
    if (typeof getWeatherAdvice === 'function') {
        const advice = getWeatherAdvice(displayData.code, lang);
        if (adviceBox) adviceBox.innerText = advice;
    }

    // 2. РЕНДЕР ГОДИННОЇ СТРІЧКИ
    if (hourlyContainer) {
        hourlyContainer.innerHTML = '';
        
        const currentHour = new Date().getHours();
        let scrollToIndex = 0;

        for (let i = 0; i < times.length; i++) {
            const t = new Date(times[i]);
            // Фільтруємо тільки обраний день
            if (t.getDate() === targetDate.getDate() && t.getMonth() === targetDate.getMonth()) {
                
                const hour = t.getHours();
                const code = weatherData.hourly.weather_code[i];
                const isDayH = weatherData.hourly.is_day[i] === 1;
                const temp = weatherData.hourly.temperature_2m[i];
                
                const wmoH = WMO_CODES[code] || WMO_CODES[0];
                const iconHFile = isDayH ? wmoH.img : wmoH.img_night;
                const iconHUrl = `${ICON_BASE_URL}${iconHFile}`;
                
                let activeClass = '';
                if (isToday) {
                    if (hour === currentHour) {
                        activeClass = 'current-hour';
                        scrollToIndex = hourlyContainer.children.length; 
                    } else if (hour < currentHour) {
                        activeClass = 'past-hour';
                    }
                }

                const item = document.createElement('div');
                item.className = `w-hour ${activeClass}`;
                item.innerHTML = `
                    <div class="wh-time">${pad(hour)}:00</div>
                    <div class="wh-icon"><img src="${iconHUrl}" alt="icon"></div>
                    <div class="wh-temp">${Math.round(temp)}°</div>
                `;
                hourlyContainer.appendChild(item);
            }
        }

        // Автоскрол
        requestAnimationFrame(() => {
            if (isToday && scrollToIndex > 0) {
                // (ширина елемента + відступ) * індекс
                const scrollPos = (scrollToIndex - 1) * 60; 
                hourlyContainer.scrollTo({ left: scrollPos, behavior: 'smooth' });
            } else {
                hourlyContainer.scrollTo({ left: 0, behavior: 'smooth' });
            }
        });
    }
}

function parseScheduleDate(dateStr) {
    if (!dateStr) return new Date();
    
    // Формат "25 СІЧНЯ"
    const parts = dateStr.trim().split(' ');
    if (parts.length < 2) return new Date(); // Фоллбек на сьогодні

    const day = parseInt(parts[0]);
    const monthName = parts[1].toUpperCase();
    
    const monthMap = {
        "СІЧНЯ":0, "ЛЮТОГО":1, "БЕРЕЗНЯ":2, "КВІТНЯ":3, "ТРАВНЯ":4, "ЧЕРВНЯ":5,
        "ЛИПНЯ":6, "СЕРПНЯ":7, "ВЕРЕСНЯ":8, "ЖОВТНЯ":9, "ЛИСТОПАДА":10, "ГРУДНЯ":11
    };
    
    const now = new Date();
    let year = now.getFullYear();
    const month = monthMap[monthName];

    // Корекція року (якщо зараз грудень, а дата - січень, то це наступний рік)
    if (now.getMonth() === 11 && month === 0) year++;
    if (now.getMonth() === 0 && month === 11) year--;

    return new Date(year, month, day);
}

function updateWeatherLang() {
    if (currentViewingDateStr) {
        renderWeatherForDate(currentViewingDateStr);
    }
}

function pad(n) { return n.toString().padStart(2,'0'); }
