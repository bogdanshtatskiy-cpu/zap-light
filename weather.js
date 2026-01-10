// Используем крутой набор анимированных иконок Meteocons
const ICON_BASE_URL = "https://basmilius.github.io/weather-icons/production/fill/all/";

const WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast?latitude=47.8388&longitude=35.1396&current=temperature_2m,apparent_temperature,weather_code,is_day&hourly=temperature_2m,weather_code,is_day&timezone=auto&forecast_days=2";

// Маппинг кодов погоды на красивые анимированные иконки
const WMO_CODES = {
    0:  { uk: "Ясно", ru: "Ясно", img: "clear-day.svg", img_night: "clear-night.svg" },
    1:  { uk: "Переважно ясно", ru: "Преимущественно ясно", img: "partly-cloudy-day.svg", img_night: "partly-cloudy-night.svg" },
    2:  { uk: "Мінлива хмарність", ru: "Переменная облачность", img: "partly-cloudy-day.svg", img_night: "partly-cloudy-night.svg" },
    3:  { uk: "Похмуро", ru: "Пасмурно", img: "overcast.svg", img_night: "overcast.svg" },
    
    45: { uk: "Туман", ru: "Туман", img: "fog.svg", img_night: "fog.svg" }, 
    48: { uk: "Туман паморозь", ru: "Туман с инеем", img: "fog.svg", img_night: "fog.svg" },
    
    51: { uk: "Мряка", ru: "Морось", img: "drizzle.svg", img_night: "drizzle.svg" },
    53: { uk: "Мряка", ru: "Морось", img: "drizzle.svg", img_night: "drizzle.svg" },
    55: { uk: "Щільна мряка", ru: "Сильная морось", img: "drizzle.svg", img_night: "drizzle.svg" },
    
    61: { uk: "Слабкий дощ", ru: "Слабый дождь", img: "rain.svg", img_night: "rain.svg" },
    63: { uk: "Дощ", ru: "Дождь", img: "rain.svg", img_night: "rain.svg" },
    65: { uk: "Сильний дощ", ru: "Сильный дождь", img: "rain.svg", img_night: "rain.svg" },
    
    71: { uk: "Слабкий сніг", ru: "Слабый снег", img: "snow.svg", img_night: "snow.svg" },
    73: { uk: "Сніг", ru: "Снег", img: "snow.svg", img_night: "snow.svg" },
    75: { uk: "Сильний сніг", ru: "Сильный снег", img: "snow.svg", img_night: "snow.svg" },
    77: { uk: "Снігові зерна", ru: "Снежные зерна", img: "hail.svg", img_night: "hail.svg" },
    
    80: { uk: "Злива", ru: "Ливень", img: "rain.svg", img_night: "rain.svg" },
    81: { uk: "Злива", ru: "Ливень", img: "rain.svg", img_night: "rain.svg" },
    82: { uk: "Сильна злива", ru: "Сильный ливень", img: "thunderstorms-rain.svg", img_night: "thunderstorms-rain.svg" },
    
    85: { uk: "Снігопад", ru: "Снегопад", img: "snow.svg", img_night: "snow.svg" },
    86: { uk: "Сильний снігопад", ru: "Сильный снегопад", img: "snow.svg", img_night: "snow.svg" },
    
    95: { uk: "Гроза", ru: "Гроза", img: "thunderstorms.svg", img_night: "thunderstorms.svg" },
    96: { uk: "Гроза з градом", ru: "Гроза с градом", img: "thunderstorms-overcast-rain.svg", img_night: "thunderstorms-overcast-rain.svg" },
    99: { uk: "Гроза з градом", ru: "Гроза с градом", img: "thunderstorms-overcast-rain.svg", img_night: "thunderstorms-overcast-rain.svg" }
};

let weatherData = null;

async function initWeather() {
    try {
        const res = await fetch(WEATHER_API_URL);
        if (!res.ok) throw new Error("Weather API Error");
        weatherData = await res.json();
        renderWeather();
    } catch (e) {
        console.error("Weather load failed:", e);
        const widget = document.getElementById('weather-widget');
        if (widget) widget.style.display = 'none';
    }
}

function renderWeather() {
    if (!weatherData) return;

    const widget = document.getElementById('weather-widget');
    if (!widget) return;
    
    widget.style.display = 'flex';

    // Текущая погода
    const current = weatherData.current;
    const wmo = WMO_CODES[current.weather_code] || WMO_CODES[0];
    const isDay = current.is_day === 1;
    
    // Выбираем файл картинки
    const iconFile = isDay ? wmo.img : wmo.img_night;
    const iconUrl = `${ICON_BASE_URL}${iconFile}`;
    const desc = lang === 'uk' ? wmo.uk : wmo.ru;
    
    // Рендерим
    const elIcon = document.getElementById('w-icon');
    const elTemp = document.getElementById('w-temp');
    const elDesc = document.getElementById('w-desc');
    const elFeel = document.getElementById('w-feel');

    // Вставляем картинку вместо текста
    if (elIcon) elIcon.innerHTML = `<img src="${iconUrl}" alt="weather">`;
    if (elTemp) elTemp.innerText = `${Math.round(current.temperature_2m)}°`;
    if (elDesc) elDesc.innerText = desc;
    if (elFeel) elFeel.innerText = `${lang === 'uk' ? 'Відчувається як' : 'Ощущается как'} ${Math.round(current.apparent_temperature)}°`;

    // Почасовой прогноз
    const hourlyContainer = document.getElementById('w-hourly');
    if (hourlyContainer) {
        hourlyContainer.innerHTML = '';

        const currentHourIndex = new Date().getHours(); 
        
        for (let i = currentHourIndex + 1; i < currentHourIndex + 13; i++) {
            if (!weatherData.hourly.time[i]) break;

            const timeStr = weatherData.hourly.time[i]; 
            const date = new Date(timeStr);
            const hour = date.getHours().toString().padStart(2, '0');
            
            const code = weatherData.hourly.weather_code[i];
            const isDayHourly = weatherData.hourly.is_day[i] === 1;
            const wmoH = WMO_CODES[code] || WMO_CODES[0];
            
            const iconHFile = isDayHourly ? wmoH.img : wmoH.img_night;
            const iconHUrl = `${ICON_BASE_URL}${iconHFile}`;
            const tempH = Math.round(weatherData.hourly.temperature_2m[i]);

            const item = document.createElement('div');
            item.className = 'w-hour';
            item.innerHTML = `
                <div class="wh-time">${hour}:00</div>
                <div class="wh-icon"><img src="${iconHUrl}" alt="icon"></div>
                <div class="wh-temp">${tempH}°</div>
            `;
            hourlyContainer.appendChild(item);
        }
    }
}

function updateWeatherLang() {
    renderWeather();
}
