const ICON_BASE_URL = "https://basmilius.github.io/weather-icons/production/fill/all/";

// Запрашиваем 5 дней в прошлом и 2 в будущем
const WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast?latitude=47.8388&longitude=35.1396&current=temperature_2m,apparent_temperature,weather_code,is_day&hourly=temperature_2m,weather_code,is_day&timezone=auto&forecast_days=2&past_days=5";

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
let currentViewingDateStr = null; // Храним строку даты (напр. "10 СІЧНЯ")

async function initWeather() {
    // Восстанавливаем состояние видимости
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
    if (!weatherData) return;
    currentViewingDateStr = dateStr; // Запоминаем для смены языка

    const widget = document.getElementById('weather-widget');
    const adviceBox = document.getElementById('w-advice-text');
    
    // Парсим дату графика
    const targetDate = parseScheduleDate(dateStr);
    const today = new Date();
    today.setHours(0,0,0,0,0);
    targetDate.setHours(0,0,0,0,0);

    const isToday = targetDate.getTime() === today.getTime();
    
    // 1. БОЛЬШАЯ КАРТОЧКА (Всегда ТЕКУЩАЯ погода СЕЙЧАС, если смотрим сегодня,
    // или погода на 12:00, если смотрим другой день)
    
    let displayData = null;
    let isCurrent = false;

    if (isToday) {
        // Показываем данные "прямо сейчас"
        const current = weatherData.current;
        displayData = {
            code: current.weather_code,
            temp: current.temperature_2m,
            isDay: current.is_day === 1,
            feel: current.apparent_temperature
        };
        isCurrent = true;
    } else {
        // Ищем данные на 12:00 дня выбранной даты
        const times = weatherData.hourly.time;
        let foundIndex = -1;
        
        for(let i=0; i<times.length; i++) {
            const t = new Date(times[i]);
            if (t.getDate() === targetDate.getDate() && t.getMonth() === targetDate.getMonth() && t.getHours() === 14) {
                foundIndex = i;
                break;
            }
        }
        
        // Если нашли (дата доступна в прогнозе)
        if (foundIndex !== -1) {
            displayData = {
                code: weatherData.hourly.weather_code[foundIndex],
                temp: weatherData.hourly.temperature_2m[foundIndex],
                isDay: true, // Днем в 14:00 обычно светло
                feel: weatherData.hourly.temperature_2m[foundIndex] // API hourly doesn't give apparent easily here, using temp
            };
        }
    }

    if (!displayData) {
        // Дата за пределами прогноза (-5 дней или +2 дня)
        widget.style.opacity = '0.5'; // Делаем полупрозрачным, показываем что данных нет
        document.getElementById('w-desc').innerText = lang === 'uk' ? "Дані відсутні" : "Данные отсутствуют";
        document.getElementById('w-hourly').innerHTML = '';
        return;
    } else {
        widget.style.opacity = '1';
    }

    // Рендер основной части
    const wmo = WMO_CODES[displayData.code] || WMO_CODES[0];
    const iconFile = displayData.isDay ? wmo.img : wmo.img_night;
    const iconUrl = `${ICON_BASE_URL}${iconFile}`;
    const desc = lang === 'uk' ? wmo.uk : wmo.ru;

    document.getElementById('w-icon').innerHTML = `<img src="${iconUrl}" alt="weather">`;
    document.getElementById('w-temp').innerText = `${Math.round(displayData.temp)}°`;
    document.getElementById('w-desc').innerText = desc;
    
    // Фраза "Ощущается как" только для "сейчас", для прогноза просто пусто или дата
    if (isCurrent) {
        document.getElementById('w-feel').innerText = `${lang === 'uk' ? 'Відчувається як' : 'Ощущается как'} ${Math.round(displayData.feel)}°`;
    } else {
        // Форматируем дату для подписи
        const d = targetDate.getDate();
        const m = targetDate.getMonth() + 1;
        document.getElementById('w-feel').innerText = `${pad(d)}.${pad(m)}`;
    }

    // НАПУТСТВИЕ
    if (typeof getWeatherAdvice === 'function') {
        const advice = getWeatherAdvice(displayData.code, lang);
        adviceBox.innerText = advice;
    }

    // 2. ПОЧАСОВОЙ ПРОГНОЗ (Умный скролл)
    const hourlyContainer = document.getElementById('w-hourly');
    if (hourlyContainer) {
        hourlyContainer.innerHTML = '';
        
        const hourlyData = [];
        const times = weatherData.hourly.time;
        const currentHour = new Date().getHours();
        let scrollToIndex = 0;

        for (let i = 0; i < times.length; i++) {
            const t = new Date(times[i]);
            // Фильтр по выбранному дню
            if (t.getDate() === targetDate.getDate() && t.getMonth() === targetDate.getMonth()) {
                
                const hour = t.getHours();
                const code = weatherData.hourly.weather_code[i];
                const isDayH = weatherData.hourly.is_day[i] === 1;
                const temp = weatherData.hourly.temperature_2m[i];
                
                // Рендер элемента
                const wmoH = WMO_CODES[code] || WMO_CODES[0];
                const iconHFile = isDayH ? wmoH.img : wmoH.img_night;
                const iconHUrl = `${ICON_BASE_URL}${iconHFile}`;
                
                let activeClass = '';
                // Если это СЕГОДНЯ:
                if (isToday) {
                    if (hour === currentHour) {
                        activeClass = 'current-hour';
                        scrollToIndex = hourlyData.length; // Запоминаем индекс для скролла
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
                hourlyData.push(item);
            }
        }

        // Скроллим к нужному месту
        requestAnimationFrame(() => {
            if (isToday && scrollToIndex > 0) {
                // Скролл так, чтобы текущий час был вторым слева (комфортно)
                const scrollPos = (scrollToIndex - 1) * 60; 
                hourlyContainer.scrollTo({ left: scrollPos, behavior: 'smooth' });
            } else {
                hourlyContainer.scrollTo({ left: 0, behavior: 'smooth' });
            }
        });
    }
}

function parseScheduleDate(dateStr) {
    const parts = dateStr.split(' ');
    const day = parseInt(parts[0]);
    const monthName = parts[1];
    
    // Маппинг месяцев (такой же как в index.html)
    const monthMap = {
        "СІЧНЯ":0, "ЛЮТОГО":1, "БЕРЕЗНЯ":2, "КВІТНЯ":3, "ТРАВНЯ":4, "ЧЕРВНЯ":5,
        "ЛИПНЯ":6, "СЕРПНЯ":7, "ВЕРЕСНЯ":8, "ЖОВТНЯ":9, "ЛИСТОПАДА":10, "ГРУДНЯ":11
    };
    
    const now = new Date();
    let year = now.getFullYear();
    const month = monthMap[monthName];

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
