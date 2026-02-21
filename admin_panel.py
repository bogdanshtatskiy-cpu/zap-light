from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import asyncpg
import uvicorn
import os

app = FastAPI(title="ZapLight CRM")
security = HTTPBasic()

# ================= БЕЗОПАСНЫЕ НАСТРОЙКИ =================
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin") 
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")
# ========================================================

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_LOGIN or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Расширенная модель для обновления ВСЕХ полей
class UserUpdate(BaseModel):
    queue_id: str | None
    language: str | None
    notify_before: int | None
    notifications_enabled: bool
    first_name: str | None
    last_name: str | None
    username: str | None
    phone_number: str | None
    silent_mode: bool

@app.get("/api/users")
async def get_users(username: str = Depends(verify_credentials)):
    if not DATABASE_URL:
        return []
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT * FROM users ORDER BY user_id DESC")
    await conn.close()
    return [dict(r) for r in rows]

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, user: UserUpdate, username: str = Depends(verify_credentials)):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        UPDATE users 
        SET queue_id = $1, language = $2, notify_before = $3, 
            notifications_enabled = $4, first_name = $5, last_name = $6, 
            username = $7, phone_number = $8, silent_mode = $9
        WHERE user_id = $10
    """, 
    user.queue_id, user.language, user.notify_before, 
    user.notifications_enabled, user.first_name, user.last_name, 
    user.username, user.phone_number, user.silent_mode, user_id)
    await conn.close()
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def serve_admin_panel(username: str = Depends(verify_credentials)):
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZapLight | CRM Панель</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            /* Кастомный скроллбар для красоты */
            ::-webkit-scrollbar { width: 6px; }
            ::-webkit-scrollbar-track { background: #1f2937; }
            ::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 3px; }
            body { background-color: #111827; color: #e5e7eb; }
        </style>
    </head>
    <body class="p-4 md:p-6 font-sans antialiased">
        
        <div class="max-w-6xl mx-auto">
            
            <div class="mb-6">
                <h1 class="text-3xl font-bold text-blue-400 mb-4 flex items-center gap-2">
                    ⚡ ZapLight CRM
                </h1>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4" id="dashboard">
                    </div>
            </div>

            <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 mb-6 flex flex-col md:flex-row gap-4 shadow-lg">
                <input type="text" id="searchInput" oninput="applyFilters()" placeholder="🔍 Поиск (Имя, ID, Username)..." 
                       class="w-full bg-gray-900 border border-gray-600 text-white p-2.5 rounded-lg focus:outline-none focus:border-blue-500 text-sm">
                
                <select id="queueFilter" onchange="applyFilters()" class="w-full md:w-48 bg-gray-900 border border-gray-600 text-white p-2.5 rounded-lg focus:outline-none focus:border-blue-500 text-sm">
                    <option value="all">Все очереди</option>
                    </select>

                <select id="notifyFilter" onchange="applyFilters()" class="w-full md:w-48 bg-gray-900 border border-gray-600 text-white p-2.5 rounded-lg focus:outline-none focus:border-blue-500 text-sm">
                    <option value="all">Все уведомления</option>
                    <option value="on">Включены 🔔</option>
                    <option value="off">Выключены 🔕</option>
                </select>
            </div>

            <div id="usersList" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div class="col-span-full text-center text-gray-400 py-10 animate-pulse">Загрузка защищенной базы...</div>
            </div>
        </div>

        <div id="editModal" class="fixed inset-0 bg-black bg-opacity-80 hidden flex items-center justify-center p-4 z-50 overflow-y-auto">
            <div class="bg-gray-800 rounded-xl p-6 w-full max-w-lg border border-gray-600 shadow-2xl relative">
                
                <button onclick="closeModal()" class="absolute top-4 right-4 text-gray-400 hover:text-white text-2xl">&times;</button>
                <h2 class="text-xl font-bold text-blue-400 mb-6 border-b border-gray-700 pb-2" id="modalTitle">Настройки пользователя</h2>
                
                <input type="hidden" id="editUserId">
                
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div>
                        <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase">Имя</label>
                        <input type="text" id="editFirstName" class="w-full bg-gray-900 border border-gray-600 text-white p-2 rounded focus:border-blue-500 text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase">Фамилия</label>
                        <input type="text" id="editLastName" class="w-full bg-gray-900 border border-gray-600 text-white p-2 rounded focus:border-blue-500 text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase">Username</label>
                        <input type="text" id="editUsername" placeholder="@username" class="w-full bg-gray-900 border border-gray-600 text-white p-2 rounded focus:border-blue-500 text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase">Телефон</label>
                        <input type="text" id="editPhone" placeholder="+380..." class="w-full bg-gray-900 border border-gray-600 text-white p-2 rounded focus:border-blue-500 text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase">Очередь</label>
                        <input type="text" id="editQueue" class="w-full bg-gray-900 border border-gray-600 text-white p-2 rounded focus:border-blue-500 text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase">Язык</label>
                        <select id="editLang" class="w-full bg-gray-900 border border-gray-600 text-white p-2 rounded focus:border-blue-500 text-sm">
                            <option value="ua">Украинский (ua)</option>
                            <option value="ru">Русский (ru)</option>
                            <option value="en">Английский (en)</option>
                        </select>
                    </div>
                    <div class="col-span-2">
                        <label class="block text-xs font-semibold text-gray-400 mb-1 uppercase">Предупреждать за (минут)</label>
                        <input type="number" id="editNotifyBefore" class="w-full bg-gray-900 border border-gray-600 text-white p-2 rounded focus:border-blue-500 text-sm">
                    </div>
                </div>
                
                <div class="bg-gray-900 p-3 rounded-lg border border-gray-700 mb-6 space-y-3">
                    <label class="flex items-center cursor-pointer">
                        <input type="checkbox" id="editNotify" class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-0 cursor-pointer">
                        <span class="ml-3 text-sm text-gray-200">Отправлять уведомления 🔔</span>
                    </label>
                    <label class="flex items-center cursor-pointer">
                        <input type="checkbox" id="editSilent" class="w-4 h-4 text-purple-600 bg-gray-700 border-gray-600 rounded focus:ring-0 cursor-pointer">
                        <span class="ml-3 text-sm text-gray-200">Тихий режим (без звука) 🌙</span>
                    </label>
                </div>
                
                <div class="flex justify-end gap-3">
                    <button onclick="closeModal()" class="px-5 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 font-medium text-sm transition">Отмена</button>
                    <button onclick="saveUser()" class="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 font-medium text-sm shadow-lg shadow-blue-500/30 transition">Сохранить</button>
                </div>
            </div>
        </div>

        <script>
            let allUsers = [];

            // Инициализация
            async function loadUsers() {
                const res = await fetch('/api/users');
                if (res.status === 401) { alert("Ошибка авторизации"); return; }
                allUsers = await res.json();
                
                updateDashboard();
                populateQueueDropdown();
                applyFilters();
            }

            // Рендер отчетов (Дашборд)
            function updateDashboard() {
                const total = allUsers.length;
                const notifyOn = allUsers.filter(u => u.notifications_enabled).length;
                
                // Считаем самую популярную очередь
                const queues = {};
                allUsers.forEach(u => {
                    if(u.queue_id) {
                        queues[u.queue_id] = (queues[u.queue_id] || 0) + 1;
                    }
                });
                let topQueue = "Нет данных";
                let max = 0;
                for (const [q, count] of Object.entries(queues)) {
                    if(count > max) { max = count; topQueue = q; }
                }

                document.getElementById('dashboard').innerHTML = `
                    <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-sm">
                        <div class="text-xs text-gray-400 uppercase font-bold tracking-wider">Всего юзеров</div>
                        <div class="text-2xl font-black text-white mt-1">${total}</div>
                    </div>
                    <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-sm">
                        <div class="text-xs text-gray-400 uppercase font-bold tracking-wider">Уведомления ВКЛ</div>
                        <div class="text-2xl font-black text-green-400 mt-1">${notifyOn}</div>
                    </div>
                    <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-sm">
                        <div class="text-xs text-gray-400 uppercase font-bold tracking-wider">Топ Очередь</div>
                        <div class="text-2xl font-black text-blue-400 mt-1">${topQueue}</div>
                    </div>
                    <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-sm">
                        <div class="text-xs text-gray-400 uppercase font-bold tracking-wider">Новых сегодня</div>
                        <div class="text-2xl font-black text-purple-400 mt-1">~</div>
                    </div>
                `;
            }

            // Заполнение дропдауна фильтров очередей
            function populateQueueDropdown() {
                const select = document.getElementById('queueFilter');
                const queues = [...new Set(allUsers.map(u => u.queue_id).filter(q => q))].sort();
                queues.forEach(q => {
                    if(![...select.options].some(opt => opt.value === q)) {
                        select.add(new Option(`Очередь ${q}`, q));
                    }
                });
            }

            // Фильтрация и рендер карточек
            function applyFilters() {
                const searchTxt = document.getElementById('searchInput').value.toLowerCase();
                const queueVal = document.getElementById('queueFilter').value;
                const notifyVal = document.getElementById('notifyFilter').value;

                const filtered = allUsers.filter(u => {
                    // Поиск
                    const matchSearch = String(u.user_id).includes(searchTxt) || 
                                        (u.first_name && u.first_name.toLowerCase().includes(searchTxt)) ||
                                        (u.username && u.username.toLowerCase().includes(searchTxt));
                    // Фильтр очереди
                    const matchQueue = (queueVal === 'all') || (u.queue_id === queueVal);
                    // Фильтр уведомлений
                    const matchNotify = (notifyVal === 'all') || 
                                        (notifyVal === 'on' && u.notifications_enabled) || 
                                        (notifyVal === 'off' && !u.notifications_enabled);

                    return matchSearch && matchQueue && matchNotify;
                });

                renderUsers(filtered);
            }

            // Отрисовка компактных карточек
            function renderUsers(users) {
                const list = document.getElementById('usersList');
                list.innerHTML = '';
                
                if(users.length === 0) {
                    list.innerHTML = `<div class="col-span-full text-center text-gray-500 py-6">Ничего не найдено</div>`;
                    return;
                }

                users.forEach(u => {
                    let name = u.first_name || 'Без имени';
                    if (u.last_name) name += ' ' + u.last_name;
                    let username = u.username ? `<span class="text-blue-400">@${u.username}</span>` : '<span class="text-gray-600">Нет юзернейма</span>';
                    let queue = u.queue_id ? `<span class="bg-blue-900/50 border border-blue-700 text-blue-300 text-xs px-2 py-0.5 rounded-full">${u.queue_id}</span>` : '<span class="bg-gray-700 text-gray-400 text-xs px-2 py-0.5 rounded-full">Не выбрана</span>';
                    
                    let notifyIcon = u.notifications_enabled ? '🔔' : '🔕';
                    let silentIcon = u.silent_mode ? '🌙' : '🔊';

                    let card = `
                        <div class="bg-gray-800 p-3.5 rounded-xl border border-gray-700 shadow-sm cursor-pointer hover:bg-gray-750 hover:border-gray-500 hover:shadow-md transition-all group" 
                             onclick='openModal(${JSON.stringify(u).replace(/'/g, "&#39;")})'>
                            <div class="flex justify-between items-start mb-1.5">
                                <div class="font-bold text-gray-100 truncate pr-2 group-hover:text-blue-400 transition-colors">${name}</div>
                                <div>${queue}</div>
                            </div>
                            <div class="text-xs text-gray-400 font-mono mb-2">ID: ${u.user_id}</div>
                            <div class="text-xs mb-2 truncate">${username} ${u.phone_number ? `| 📞 ${u.phone_number}` : ''}</div>
                            
                            <div class="flex justify-between items-center text-xs text-gray-500 border-t border-gray-700 pt-2 mt-auto">
                                <div>Lang: <span class="uppercase text-gray-300">${u.language || 'UA'}</span></div>
                                <div class="flex gap-2 text-sm" title="Уведомления: ${notifyIcon}, Звук: ${silentIcon}">
                                    ${notifyIcon} ${silentIcon} <span class="text-gray-400 text-xs mt-0.5">-${u.notify_before || 15}м</span>
                                </div>
                            </div>
                        </div>
                    `;
                    list.innerHTML += card;
                });
            }

            // Работа с модальным окном
            function openModal(user) {
                document.getElementById('editUserId').value = user.user_id;
                document.getElementById('modalTitle').innerText = `Юзер: ${user.user_id}`;
                
                // Заполняем все инпуты
                document.getElementById('editFirstName').value = user.first_name || '';
                document.getElementById('editLastName').value = user.last_name || '';
                document.getElementById('editUsername').value = user.username || '';
                document.getElementById('editPhone').value = user.phone_number || '';
                document.getElementById('editQueue').value = user.queue_id || '';
                document.getElementById('editLang').value = user.language || 'ua';
                document.getElementById('editNotifyBefore').value = user.notify_before || 15;
                
                // Чекбоксы
                document.getElementById('editNotify').checked = user.notifications_enabled;
                document.getElementById('editSilent').checked = user.silent_mode;

                document.getElementById('editModal').classList.remove('hidden');
            }

            function closeModal() {
                document.getElementById('editModal').classList.add('hidden');
            }

            // Отправка данных на сервер
            async function saveUser() {
                const id = document.getElementById('editUserId').value;
                const data = {
                    first_name: document.getElementById('editFirstName').value || null,
                    last_name: document.getElementById('editLastName').value || null,
                    username: document.getElementById('editUsername').value || null,
                    phone_number: document.getElementById('editPhone').value || null,
                    queue_id: document.getElementById('editQueue').value || null,
                    language: document.getElementById('editLang').value || 'ua',
                    notify_before: parseInt(document.getElementById('editNotifyBefore').value) || 15,
                    notifications_enabled: document.getElementById('editNotify').checked,
                    silent_mode: document.getElementById('editSilent').checked
                };

                const btn = event.target;
                const oldText = btn.innerText;
                btn.innerText = "Сохранение...";
                btn.disabled = true;

                try {
                    await fetch(`/api/users/${id}`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    closeModal();
                    loadUsers(); 
                } catch(e) {
                    alert("Ошибка при сохранении!");
                } finally {
                    btn.innerText = oldText;
                    btn.disabled = false;
                }
            }

            // Запуск
            loadUsers();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
