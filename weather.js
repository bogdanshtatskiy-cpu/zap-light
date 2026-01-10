const WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast?latitude=47.8388&longitude=35.1396&current=temperature_2m,apparent_temperature,weather_code,is_day&hourly=temperature_2m,weather_code,is_day&timezone=auto&forecast_days=2";

const WMO_CODES = {
    0: { uk: "Ясно", ru: "Ясно", icon: "☀️", icon_night: "🌙" },
    1: { uk: "Переважно ясно", ru: "Преимущественно ясно", icon: "🌤️", icon_night: "☁️" },
    2: { uk: "Мінлива хмарність", ru: "Переменная облачность", icon: "⛅", icon_night: "☁️" },
    3: { uk: "Похмуро", ru: "Пасмурно", icon: "☁️", icon_night: "☁️" },
    45: { uk: "Туман", ru: "Туман", icon: "🌫️", icon_night: "🌫️" },
    48: { uk: "Туман паморозь", ru: "Туман с инеем", icon: "🌫️", icon_night: "🌫️" },
    51: { uk: "Мряка", ru: "Морось", icon: "💧", icon_night: "💧" },
    53: { uk: "Мряка", ru: "Морось", icon: "💧", icon_night: "💧" },
    55: { uk: "Щільна мряка", ru: "Сильная морось", icon: "💧", icon_night: "💧" },
    61: { uk: "Слабкий дощ", ru: "Слабый дождь", icon: "🌧️", icon_night: "🌧️" },
    63: { uk: "Дощ", ru: "Дождь", icon: "🌧️", icon_night: "🌧️" },
    65: { uk: "Сильний дощ", ru: "Сильный дождь", icon: "🌧️", icon_night: "🌧️" },
    71: { uk: "Слабкий сніг", ru: "Слабый снег", icon: "🌨️", icon_night: "🌨️" },
    73: { uk: "Сніг", ru: "Снег", icon: "🌨️", icon_night: "🌨️" },
    75: { uk: "Сильний сніг", ru: "Сильный снег", icon: "❄️", icon_night: "❄️" },
    77: { uk: "Снігові зерна", ru: "Снежные зерна", icon: "🌨️", icon_night: "🌨️" },
    80: { uk: "Злива", ru: "Ливень", icon: "☔", icon_night: "☔" },
    81: { uk: "Злива", ru: "Ливень", icon: "☔", icon_night: "☔" },
    82: { uk: "Сильна злива", ru: "Сильный ливень", icon: "☔", icon_night: "☔" },
    85: { uk: "Снігопад", ru: "Снегопад", icon: "❄️", icon_night: "❄️" },
    86: { uk: "Сильний снігопад", ru: "Сильный снегопад", icon: "❄️", icon_night: "❄️" },
    95: { uk: "Гроза", ru: "Гроза", icon: "⚡", icon_night: "⚡" },
    96: { uk: "Гроза з градом", ru: "Гроза с градом", icon: "⛈️", icon_night: "⛈️" },
    99: { uk: "Гроза з градом", ru: "Гроза с градом", icon: "⛈️", icon_night: "⛈️" }
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
        document.getElementById('weather-widget').style.display = 'none';
    }
}

function renderWeather() {
    if (!weatherData) return;

    const widget = document.getElementById('weather-widget');
    if (!widget) return;
    
    widget.style.display = 'flex';

    // Поточна погода
    const current = weatherData.current;
    const wmo = WMO_CODES[current.weather_code] || WMO_CODES[0];
    const isDay = current.is_day === 1;
    const icon = isDay ? wmo.icon : wmo.icon_night;
    const desc = lang === 'uk' ? wmo.uk : wmo.ru;
    
    // Відображення поточної
    document.getElementById('w-icon').innerText = icon;
    document.getElementById('w-temp').innerText = `${Math.round(current.temperature_2m)}°`;
    document.getElementById('w-desc').innerText = desc;
    document.getElementById('w-feel').innerText = `${lang === 'uk' ? 'Відчувається як' : 'Ощущается как'} ${Math.round(current.apparent_temperature)}°`;

    // Погодинний прогноз (наступні 24 години)
    const hourlyContainer = document.getElementById('w-hourly');
    hourlyContainer.innerHTML = '';

    const currentHourIndex = new Date().getHours(); // Простий індекс, для точності можна парсити ISO
    
    // Беремо наступні 12 годин
    for (let i = currentHourIndex + 1; i < currentHourIndex + 13; i++) {
        if (!weatherData.hourly.time[i]) break;

        const timeStr = weatherData.hourly.time[i]; // "2024-01-10T14:00"
        const date = new Date(timeStr);
        const hour = date.getHours().toString().padStart(2, '0');
        
        const code = weatherData.hourly.weather_code[i];
        const isDayHourly = weatherData.hourly.is_day[i] === 1;
        const wmoH = WMO_CODES[code] || WMO_CODES[0];
        const iconH = isDayHourly ? wmoH.icon : wmoH.icon_night;
        const tempH = Math.round(weatherData.hourly.temperature_2m[i]);

        const item = document.createElement('div');
        item.className = 'w-hour';
        item.innerHTML = `
            <div class="wh-time">${hour}:00</div>
            <div class="wh-icon">${iconH}</div>
            <div class="wh-temp">${tempH}°</div>
        `;
        hourlyContainer.appendChild(item);
    }
}

// Викликаємо оновлення тексту при зміні мови
function updateWeatherLang() {
    renderWeather();
}
