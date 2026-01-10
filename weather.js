// Используем набор иконок Meteocons (стиль "Fill" - яркие и четкие)
const ICON_BASE_URL = "https://basmilius.github.io/weather-icons/production/fill/all/";

// Запрашиваем прогноз на 7 дней (чтобы покрыть неделю)
const WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast?latitude=47.8388&longitude=35.1396&current=temperature_2m,apparent_temperature,weather_code,is_day&hourly=temperature_2m,weather_code,is_day&timezone=auto&forecast_days=7";

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
let currentViewingDate = null; // Дата, которую сейчас смотрит пользователь

async function initWeather() {
    try {
        const res = await fetch(WEATHER_API_URL);
        if (!res.ok) throw new Error("Weather API Error");
        weatherData = await res.json();
        // Рендер запустится из main.js при выборе даты
    } catch (e) {
        console.error("Weather load failed:", e);
        const widget = document.getElementById('weather-widget');
        if (widget) widget.style.display = 'none';
    }
}

// Эта функция вызывается из index.html когда меняется дата
function renderWeatherForDate(dateStr) {
    if (!weatherData) return;

    const widget = document.getElementById('weather-widget');
    if (!widget) return;
    widget.style.display = 'flex';

    // Парсим дату графика "10 СІЧНЯ" -> ищем соответствующую дату в прогнозе
    // Поскольку у нас нет года в графике, берем текущий/следующий
    const targetDate = parseScheduleDate(dateStr);
    const today = new Date();
    today.setHours(0,0,0,0);

    const isToday = targetDate.getTime() === today.getTime();
    
    // --- ВЕРХНЯЯ ЧАСТЬ (БОЛЬШАЯ) ---
    // Всегда показывает ТЕКУЩУЮ погоду "сейчас", независимо от выбранной даты графика
    // (По желанию пользователя)
    const current = weatherData.current;
    const wmo = WMO_CODES[current.weather_code] || WMO_CODES[0];
    const isDay = current.is_day === 1;
    
    const iconFile = isDay ? wmo.img : wmo.img_night;
    const iconUrl = `${ICON_BASE_URL}${iconFile}`;
    const desc = lang === 'uk' ? wmo.uk : wmo.ru;
    
    const elIcon = document.getElementById('w-icon');
    const elTemp = document.getElementById('w-temp');
    const elDesc = document.getElementById('w-desc');
    const elFeel = document.getElementById('w-feel');

    if (elIcon) elIcon.innerHTML = `<img src="${iconUrl}" alt="weather">`;
    if (elTemp) elTemp.innerText = `${Math.round(current.temperature_2m)}°`;
    if (elDesc) elDesc.innerText = desc;
    if (elFeel) elFeel.innerText = `${lang === 'uk' ? 'Відчувається як' : 'Ощущается как'} ${Math.round(current.apparent_temperature)}°`;

    // --- НИЖНЯЯ ЧАСТЬ (ПОЧАСОВОЙ ПРОГНОЗ) ---
    // А вот тут показываем прогноз на ВЫБРАННУЮ дату
    const hourlyContainer = document.getElementById('w-hourly');
    if (hourlyContainer) {
        hourlyContainer.innerHTML = '';
        
        // Фильтруем данные API для нужной даты
        const hourlyData = [];
        const times = weatherData.hourly.time;
        
        let scrollToIndex = 0;
        const currentHour = new Date().getHours();

        for (let i = 0; i < times.length; i++) {
            const t = new Date(times[i]);
            // Сравниваем дни
            if (t.getDate() === targetDate.getDate() && t.getMonth() === targetDate.getMonth()) {
                
                // Данные на этот час
                const code = weatherData.hourly.weather_code[i];
                const isDayH = weatherData.hourly.is_day[i] === 1;
                const temp = weatherData.hourly.temperature_2m[i];
                
                hourlyData.push({
                    time: t,
                    code: code,
                    isDay: isDayH,
                    temp: temp
                });
            }
        }

        if (hourlyData.length === 0) {
            hourlyContainer.innerHTML = '<div style="opacity:0.5; padding:10px; font-size:12px;">Прогноз недоступний</div>';
            return;
        }

        // Рендерим 24 часа (или сколько есть)
        hourlyData.forEach((hData, idx) => {
            const hour = hData.time.getHours();
            const hourStr = hour.toString().padStart(2, '0');
            
            const wmoH = WMO_CODES[hData.code] || WMO_CODES[0];
            const iconHFile = hData.isDay ? wmoH.img : wmoH.img_night;
            const iconHUrl = `${ICON_BASE_URL}${iconHFile}`;
            const tempH = Math.round(hData.temp);

            // Выделяем текущий час, если это сегодня
            let activeClass = '';
            if (isToday && hour === currentHour) {
                activeClass = 'current-hour';
                scrollToIndex = idx;
            } else if (isToday && hour < currentHour) {
                activeClass = 'past-hour';
            }

            const item = document.createElement('div');
            item.className = `w-hour ${activeClass}`;
            item.innerHTML = `
                <div class="wh-time">${hourStr}:00</div>
                <div class="wh-icon"><img src="${iconHUrl}" alt="icon"></div>
                <div class="wh-temp">${tempH}°</div>
            `;
            hourlyContainer.appendChild(item);
        });

        // Скроллим к текущему времени
        requestAnimationFrame(() => {
            if (isToday && scrollToIndex > 0) {
                // Центрируем текущий час (минус пару блоков влево)
                const scrollPos = (scrollToIndex - 1) * 60; // 60px - примерная ширина блока
                hourlyContainer.scrollTo({ left: scrollPos, behavior: 'smooth' });
            } else {
                hourlyContainer.scrollTo({ left: 0, behavior: 'smooth' });
            }
        });
    }
}

// Хелпер для парсинга даты из строки "10 СІЧНЯ"
function parseScheduleDate(dateStr) {
    const parts = dateStr.split(' ');
    const day = parseInt(parts[0]);
    const monthName = parts[1];
    
    // Ищем индекс месяца в UA массиве (он в index.html)
    // Но так как weather.js не видит UA_MONTHS из index.html напрямую, продублируем или передадим
    // Проще: используем текущий год и месяц по номеру
    // (Костыль, но надежный: мапим названия на номера)
    const monthMap = {
        "СІЧНЯ":0, "ЛЮТОГО":1, "БЕРЕЗНЯ":2, "КВІТНЯ":3, "ТРАВНЯ":4, "ЧЕРВНЯ":5,
        "ЛИПНЯ":6, "СЕРПНЯ":7, "ВЕРЕСНЯ":8, "ЖОВТНЯ":9, "ЛИСТОПАДА":10, "ГРУДНЯ":11
    };
    
    const now = new Date();
    let year = now.getFullYear();
    const month = monthMap[monthName];

    // Если сейчас Декабрь, а дата Январь -> следующий год
    if (now.getMonth() === 11 && month === 0) year++;
    // Если сейчас Январь, а дата Декабрь -> прошлый год
    if (now.getMonth() === 0 && month === 11) year--;

    return new Date(year, month, day);
}

function updateWeatherLang() {
    // Перерендер текущего состояния
    const dateTitle = document.querySelector('.date-tab.active')?.innerText;
    if (dateTitle) renderWeatherForDate(dateTitle);
}
