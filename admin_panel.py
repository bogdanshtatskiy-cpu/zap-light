from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncpg
import uvicorn
import os

app = FastAPI(title="ZapLight CRM")

# ================= БЕЗОПАСНЫЕ НАСТРОЙКИ =================
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN") 
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
# ========================================================

def verify_api(request: Request):
    if not ADMIN_LOGIN or not ADMIN_PASSWORD:
        # Защита: если настройки не заданы в Render, не пускаем никого
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Секреты не настроены на сервере")
    if request.cookies.get("admin_session") != f"{ADMIN_LOGIN}:{ADMIN_PASSWORD}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

class LoginData(BaseModel):
    username: str
    password: str

@app.post("/api/login")
async def login(data: LoginData, response: Response):
    if data.username == ADMIN_LOGIN and data.password == ADMIN_PASSWORD:
        response.set_cookie(key="admin_session", value=f"{ADMIN_LOGIN}:{ADMIN_PASSWORD}", max_age=315360000, httponly=True)
        return {"status": "ok"}
    raise HTTPException(status_code=400, detail="Неверные данные")

@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie("admin_session")
    return {"status": "ok"}

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

@app.get("/api/users", dependencies=[Depends(verify_api)])
async def get_users():
    if not DATABASE_URL:
        return []
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Автоматически добавляем колонку для отслеживания даты добавления юзера (если её еще нет)
    await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP")
    
    # Достаем пользователей и переводим дату в удобный UNIX-формат для JS
    rows = await conn.fetch("SELECT *, CAST(extract(epoch from created_at) AS FLOAT) as created_ts FROM users ORDER BY user_id DESC")
    await conn.close()
    return [dict(r) for r in rows]

@app.put("/api/users/{user_id}", dependencies=[Depends(verify_api)])
async def update_user(user_id: int, user: UserUpdate):
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

# ================= СТРАНИЦА ЛОГИНА =================
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no">
    <title>Вход | ZapLight</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #000; color: #fff; touch-action: manipulation; }
        .glass { background: rgba(28, 28, 30, 0.6); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); }
        .glass-input { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: white; }
    </style>
</head>
<body class="flex items-center justify-center h-screen px-4 font-sans">
    <div class="glass p-8 rounded-3xl w-full max-w-sm">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold mb-1 tracking-tight">ZapLight OS</h1>
            <p class="text-gray-400 text-xs font-medium uppercase tracking-widest">Graphite Security</p>
        </div>
        <input type="text" id="login" placeholder="Логин" class="glass-input w-full mb-4 p-3.5 rounded-xl focus:outline-none focus:border-blue-500 transition">
        <input type="password" id="pass" placeholder="Пароль" class="glass-input w-full mb-8 p-3.5 rounded-xl focus:outline-none focus:border-blue-500 transition">
        <button onclick="doLogin()" id="loginBtn" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl transition">Авторизация</button>
    </div>
    <script>
        async function doLogin() {
            const btn = document.getElementById('loginBtn'); btn.innerText = "Вход...";
            const u = document.getElementById('login').value, p = document.getElementById('pass').value;
            const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
            if(res.ok) window.location.reload(); else { alert("❌ Ошибка авторизации. Проверьте настройки Render."); btn.innerText = "Авторизация"; }
        }
    </script>
</body>
</html>
"""

# ================= СТРАНИЦА АДМИНКИ =================
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no">
    <title>ZapLight | CRM Панель</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Анти-зум и плавность */
        * { touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }
        
        /* Графит & Жидкое стекло (iOS 26) */
        body { background-color: #000; background-image: radial-gradient(circle at top right, #1c1c1e, #000); color: #e5e7eb; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; min-height: 100vh; }
        .glass { background: rgba(28, 28, 30, 0.6); backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px); border: 1px solid rgba(255,255,255,0.08); }
        .glass-input { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); color: white; transition: all 0.2s; }
        .glass-input:focus { border-color: #0a84ff; background: rgba(0,0,0,0.6); box-shadow: 0 0 0 2px rgba(10,132,255,0.3); }
        .card-hover:active { transform: scale(0.98); background: rgba(44, 44, 46, 0.8); }
        
        select option { background: #1c1c1e; color: white; }
    </style>
</head>
<body class="p-2 md:p-4">
    
    <div class="max-w-6xl mx-auto pb-10">
        
        <div class="flex justify-between items-center mb-4 px-1">
            <h1 class="text-xl md:text-2xl font-bold tracking-tight">ZapLight</h1>
            <div class="flex gap-2 items-center">
                <button onclick="loadUsers(false, true)" class="glass hover:bg-white/10 p-2.5 rounded-full transition group">
                    <svg id="syncIcon" class="w-4 h-4 text-gray-300 group-hover:text-white transition" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                </button>
                <button onclick="logout()" class="glass hover:bg-red-500/20 text-red-400 px-3 py-1.5 rounded-full text-xs font-bold transition">Выйти</button>
            </div>
        </div>

        <div class="grid grid-cols-3 gap-2 mb-2" id="dashboard"></div>
        
        <div class="glass p-3 rounded-2xl mb-4 flex justify-around items-center" id="statsRow">
            </div>

        <div class="glass p-3 rounded-2xl mb-4 flex flex-col md:flex-row gap-2">
            <div class="relative w-full">
                <input type="text" id="searchInput" oninput="applyFilters()" placeholder="Поиск (Имя, ID)..." class="glass-input w-full p-2 pl-3 pr-8 rounded-xl text-xs outline-none">
                <button onclick="clearSearch()" class="absolute right-2 top-1.5 text-gray-400 hover:text-white font-bold p-1 text-xs">×</button>
            </div>
            <div class="flex gap-2 w-full md:w-auto">
                <select id="queueFilter" onchange="applyFilters()" class="glass-input w-1/2 md:w-32 p-2 rounded-xl text-xs outline-none">
                    <option value="all">Очередь: Все</option>
                </select>
                <select id="notifyFilter" onchange="applyFilters()" class="glass-input w-1/2 md:w-32 p-2 rounded-xl text-xs outline-none">
                    <option value="all">Статус: Все</option>
                    <option value="on">ВКЛ 🔔</option>
                    <option value="off">ВЫКЛ 🔕</option>
                </select>
            </div>
        </div>

        <div class="px-2 mb-2 text-xs text-gray-400 font-medium tracking-wide">
            Показано: <span id="filteredCount" class="text-white font-bold">0</span>
        </div>

        <div id="usersList" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            <div class="col-span-full text-center text-gray-500 py-10 text-sm">Подключение к БД...</div>
        </div>
    </div>

    <div id="editModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm hidden flex items-center justify-center p-3 z-50">
        <div class="glass rounded-3xl p-5 w-full max-w-sm relative shadow-2xl border border-white/10 transform transition-all">
            <button onclick="closeModal()" class="absolute top-4 right-4 text-gray-400 hover:text-white bg-white/5 rounded-full w-7 h-7 flex items-center justify-center text-lg">&times;</button>
            <h2 class="text-lg font-bold mb-4" id="modalTitle">Настройки</h2>
            
            <input type="hidden" id="editUserId">
            
            <div class="grid grid-cols-2 gap-3 mb-4">
                <div class="col-span-2 flex gap-3">
                    <div class="w-1/2"><label class="block text-[10px] text-gray-400 mb-1 uppercase">Имя</label><input type="text" id="editFirstName" class="glass-input w-full p-2 rounded-lg text-xs"></div>
                    <div class="w-1/2"><label class="block text-[10px] text-gray-400 mb-1 uppercase">Фамилия</label><input type="text" id="editLastName" class="glass-input w-full p-2 rounded-lg text-xs"></div>
                </div>
                <div><label class="block text-[10px] text-gray-400 mb-1 uppercase">Username</label><input type="text" id="editUsername" class="glass-input w-full p-2 rounded-lg text-xs"></div>
                <div><label class="block text-[10px] text-gray-400 mb-1 uppercase">Телефон</label><input type="text" id="editPhone" class="glass-input w-full p-2 rounded-lg text-xs"></div>
                <div><label class="block text-[10px] text-gray-400 mb-1 uppercase">Очередь</label><input type="text" id="editQueue" class="glass-input w-full p-2 rounded-lg text-xs text-center font-bold text-[#0a84ff]"></div>
                <div><label class="block text-[10px] text-gray-400 mb-1 uppercase">Мин. до откл.</label><input type="number" id="editNotifyBefore" class="glass-input w-full p-2 rounded-lg text-xs text-center"></div>
            </div>
            
            <div class="bg-white/5 p-3 rounded-xl mb-5 space-y-3 border border-white/5">
                <label class="flex items-center justify-between cursor-pointer">
                    <span class="text-xs">Уведомления 🔔</span>
                    <input type="checkbox" id="editNotify" class="w-4 h-4 accent-[#0a84ff]">
                </label>
                <label class="flex items-center justify-between cursor-pointer">
                    <span class="text-xs">Без звука 🌙</span>
                    <input type="checkbox" id="editSilent" class="w-4 h-4 accent-purple-500">
                </label>
            </div>
            
            <button onclick="saveUser(event)" class="w-full bg-[#0a84ff] hover:bg-blue-500 text-white font-bold py-2.5 rounded-xl shadow-lg shadow-blue-500/20 text-sm transition">Сохранить</button>
        </div>
    </div>

    <script>
        let allUsers = [];

        // Автообновление каждые 5 сек (если не открыто окно редактирования)
        setInterval(() => {
            if (document.getElementById('editModal').classList.contains('hidden')) {
                loadUsers(true, false);
            }
        }, 5000);

        async function loadUsers(silent = false, isManualBtn = false) {
            if(isManualBtn) document.getElementById('syncIcon').classList.add('animate-spin');
            try {
                const res = await fetch('/api/users');
                if (res.status === 401) { window.location.reload(); return; }
                allUsers = await res.json();
                
                updateDashboard();
                if(!silent) populateQueueDropdown(); 
                applyFilters();
            } finally {
                if(isManualBtn) setTimeout(() => document.getElementById('syncIcon').classList.remove('animate-spin'), 500);
            }
        }

        async function logout() { await fetch('/api/logout', {method: 'POST'}); window.location.reload(); }
        function clearSearch() { document.getElementById('searchInput').value = ''; applyFilters(); }

        function updateDashboard() {
            const total = allUsers.length;
            const notifyOn = allUsers.filter(u => u.notifications_enabled).length;
            const queues = {};
            allUsers.forEach(u => { if(u.queue_id) queues[u.queue_id] = (queues[u.queue_id] || 0) + 1; });
            let topQueue = "-", max = 0;
            for (const [q, count] of Object.entries(queues)) { if(count > max) { max = count; topQueue = q; } }

            // Подсчет новых пользователей
            const now = Date.now() / 1000;
            let dDay = 0, dWeek = 0, dMonth = 0;
            allUsers.forEach(u => {
                if (u.created_ts) {
                    const diff = now - u.created_ts;
                    if(diff <= 86400) dDay++;
                    if(diff <= 86400*7) dWeek++;
                    if(diff <= 86400*30) dMonth++;
                }
            });

            document.getElementById('dashboard').innerHTML = `
                <div class="glass p-2 rounded-xl text-center"><div class="text-[9px] text-gray-400 uppercase">Юзеров</div><div class="text-lg font-bold">${total}</div></div>
                <div class="glass p-2 rounded-xl text-center"><div class="text-[9px] text-gray-400 uppercase">Увед. ВКЛ</div><div class="text-lg font-bold text-green-400">${notifyOn}</div></div>
                <div class="glass p-2 rounded-xl text-center"><div class="text-[9px] text-gray-400 uppercase">Топ очередь</div><div class="text-lg font-bold text-[#0a84ff]">${topQueue}</div></div>
            `;
            
            document.getElementById('statsRow').innerHTML = `
                <div class="text-xs text-gray-400"><span class="text-white font-bold">+${dDay}</span> сегодня</div>
                <div class="w-px h-4 bg-gray-700"></div>
                <div class="text-xs text-gray-400"><span class="text-white font-bold">+${dWeek}</span> за неделю</div>
                <div class="w-px h-4 bg-gray-700"></div>
                <div class="text-xs text-gray-400"><span class="text-white font-bold">+${dMonth}</span> за месяц</div>
            `;
        }

        function populateQueueDropdown() {
            const select = document.getElementById('queueFilter');
            const currentVal = select.value;
            select.innerHTML = '<option value="all">Очередь: Все</option>';
            
            const queues = [...new Set(allUsers.map(u => u.queue_id).filter(q => q))];
            queues.sort((a, b) => a.localeCompare(b, undefined, {numeric: true, sensitivity: 'base'}));
            queues.forEach(q => select.add(new Option(`Очередь ${q}`, q)));
            select.value = [...select.options].some(o=>o.value===currentVal) ? currentVal : 'all';
        }

        function applyFilters() {
            const searchTxt = document.getElementById('searchInput').value.toLowerCase();
            const queueVal = document.getElementById('queueFilter').value;
            const notifyVal = document.getElementById('notifyFilter').value;

            const filtered = allUsers.filter(u => {
                const matchSearch = String(u.user_id).includes(searchTxt) || (u.first_name && u.first_name.toLowerCase().includes(searchTxt)) || (u.username && u.username.toLowerCase().includes(searchTxt));
                const matchQueue = (queueVal === 'all') || (u.queue_id === queueVal);
                const matchNotify = (notifyVal === 'all') || (notifyVal === 'on' && u.notifications_enabled) || (notifyVal === 'off' && !u.notifications_enabled);
                return matchSearch && matchQueue && matchNotify;
            });
            
            document.getElementById('filteredCount').innerText = filtered.length;
            renderUsers(filtered);
        }

        function renderUsers(users) {
            const list = document.getElementById('usersList');
            list.innerHTML = '';
            if(users.length === 0) { list.innerHTML = `<div class="col-span-full text-center text-gray-500 py-4 text-xs">Ничего не найдено</div>`; return; }

            users.forEach(u => {
                let name = u.first_name || 'Без имени'; if (u.last_name) name += ' ' + u.last_name;
                let username = u.username ? `<span class="text-[#0a84ff]">@${u.username}</span>` : '<span class="text-gray-600">Нет юзернейма</span>';
                let queue = u.queue_id ? `<span class="bg-[#0a84ff]/20 text-[#0a84ff] border border-[#0a84ff]/30 text-[10px] px-2 py-0.5 rounded-md font-bold">${u.queue_id}</span>` : '<span class="bg-white/5 text-gray-400 text-[10px] px-2 py-0.5 rounded-md">Нет</span>';
                
                let notifyIcon = u.notifications_enabled ? '<span class="text-green-400">🔔</span>' : '<span class="text-red-400/50">🔕</span>';
                let silentIcon = u.silent_mode ? '🌙' : '🔊';

                let card = `
                    <div class="glass p-2.5 rounded-2xl card-hover cursor-pointer flex flex-col justify-between" onclick='openModal(${JSON.stringify(u).replace(/'/g, "&#39;")})'>
                        <div class="flex justify-between items-center mb-1">
                            <div class="font-semibold text-sm truncate pr-2 text-white">${name}</div>
                            <div>${queue}</div>
                        </div>
                        <div class="flex justify-between items-end">
                            <div class="text-[10px] text-gray-400 leading-tight">ID: ${u.user_id}<br>${username}</div>
                            <div class="flex gap-1.5 text-xs bg-white/5 px-2 py-1 rounded-lg border border-white/5">
                                ${notifyIcon} ${silentIcon} <span class="text-gray-400">-${u.notify_before || 15}м</span>
                            </div>
                        </div>
                    </div>
                `;
                list.innerHTML += card;
            });
        }

        function openModal(user) {
            document.getElementById('editUserId').value = user.user_id;
            document.getElementById('editFirstName').value = user.first_name || '';
            document.getElementById('editLastName').value = user.last_name || '';
            document.getElementById('editUsername').value = user.username || '';
            document.getElementById('editPhone').value = user.phone_number || '';
            document.getElementById('editQueue').value = user.queue_id || '';
            document.getElementById('editNotifyBefore').value = user.notify_before || 15;
            document.getElementById('editNotify').checked = user.notifications_enabled;
            document.getElementById('editSilent').checked = user.silent_mode;
            document.getElementById('editModal').classList.remove('hidden');
        }

        function closeModal() { document.getElementById('editModal').classList.add('hidden'); }

        async function saveUser(event) {
            const id = document.getElementById('editUserId').value;
            const data = {
                first_name: document.getElementById('editFirstName').value || null,
                last_name: document.getElementById('editLastName').value || null,
                username: document.getElementById('editUsername').value || null,
                phone_number: document.getElementById('editPhone').value || null,
                queue_id: document.getElementById('editQueue').value || null,
                language: 'ua',
                notify_before: parseInt(document.getElementById('editNotifyBefore').value) || 15,
                notifications_enabled: document.getElementById('editNotify').checked,
                silent_mode: document.getElementById('editSilent').checked
            };
            const btn = event.target; const oldText = btn.innerText;
            btn.innerText = "Сохранение..."; btn.disabled = true;
            try {
                await fetch(`/api/users/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
                closeModal(); loadUsers(true); 
            } catch(e) { alert("Ошибка сохранения"); } 
            finally { btn.innerText = oldText; btn.disabled = false; }
        }

        loadUsers();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_admin_panel(request: Request):
    if request.cookies.get("admin_session") != f"{ADMIN_LOGIN}:{ADMIN_PASSWORD}":
        return HTML_LOGIN
    return HTML_DASHBOARD
