from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import asyncpg
import uvicorn
import os

app = FastAPI(title="ZapLight Admin")
security = HTTPBasic()

# ================= БЕЗОПАСНЫЕ НАСТРОЙКИ =================
# Метод os.getenv берет данные из скрытых настроек Render. 
# На GitHub никто не увидит твоих реальных паролей!
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin") # admin - логин по умолчанию
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
# ========================================================

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_LOGIN or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

class UserUpdate(BaseModel):
    queue_id: str | None
    language: str | None
    notifications_enabled: bool

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
        SET queue_id = $1, language = $2, notifications_enabled = $3
        WHERE user_id = $4
    """, user.queue_id, user.language, user.notifications_enabled, user_id)
    await conn.close()
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def serve_admin_panel(username: str = Depends(verify_credentials)):
    html_content = """
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Админ-панель</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 text-gray-800 p-4">
        
        <div class="max-w-md mx-auto">
            <h1 class="text-2xl font-bold mb-4 text-center text-blue-600">👥 База пользователей</h1>
            
            <input type="text" id="searchInput" onkeyup="filterUsers()" placeholder="Поиск по имени, ID или очереди..." 
                   class="w-full p-3 mb-6 rounded-lg shadow-sm border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500">

            <div id="usersList" class="space-y-4">
                <div class="text-center text-gray-500">Загрузка базы...</div>
            </div>
        </div>

        <div id="editModal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center p-4 z-50">
            <div class="bg-white rounded-xl p-6 w-full max-w-sm shadow-2xl">
                <h2 class="text-xl font-bold mb-4" id="modalTitle">Редактировать</h2>
                
                <input type="hidden" id="editUserId">
                
                <label class="block text-sm font-medium text-gray-700 mb-1">Черга</label>
                <input type="text" id="editQueue" class="w-full p-2 mb-4 border rounded focus:ring-2 focus:ring-blue-500">
                
                <label class="block text-sm font-medium text-gray-700 mb-1">Мова (ua/ru)</label>
                <input type="text" id="editLang" class="w-full p-2 mb-4 border rounded focus:ring-2 focus:ring-blue-500">
                
                <label class="flex items-center mb-6">
                    <input type="checkbox" id="editNotify" class="w-5 h-5 text-blue-600 rounded">
                    <span class="ml-2 text-gray-700">Сповіщення увімкнені</span>
                </label>
                
                <div class="flex justify-end space-x-3">
                    <button onclick="closeModal()" class="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300">Відміна</button>
                    <button onclick="saveUser()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Зберегти</button>
                </div>
            </div>
        </div>

        <script>
            let allUsers = [];

            async function loadUsers() {
                const res = await fetch('/api/users');
                if (res.status === 401) { alert("Ошибка авторизации"); return; }
                allUsers = await res.json();
                renderUsers(allUsers);
            }

            function renderUsers(users) {
                const list = document.getElementById('usersList');
                list.innerHTML = '';
                users.forEach(u => {
                    let name = u.first_name || 'Без имени';
                    let username = u.username ? '@' + u.username : '';
                    let queue = u.queue_id || 'Не обрано';
                    
                    let card = `
                        <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-200 cursor-pointer hover:shadow-md transition" onclick='openModal(${JSON.stringify(u).replace(/'/g, "&#39;")})'>
                            <div class="flex justify-between items-center mb-2">
                                <span class="font-bold text-lg">${name}</span>
                                <span class="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-bold">Черга: ${queue}</span>
                            </div>
                            <div class="text-sm text-gray-500">ID: ${u.user_id} ${username}</div>
                            <div class="text-xs text-gray-400 mt-1">Мова: ${u.language} | Сповіщення: ${u.notifications_enabled ? '✅' : '❌'}</div>
                        </div>
                    `;
                    list.innerHTML += card;
                });
            }

            function filterUsers() {
                const q = document.getElementById('searchInput').value.toLowerCase();
                const filtered = allUsers.filter(u => 
                    String(u.user_id).includes(q) || 
                    (u.first_name && u.first_name.toLowerCase().includes(q)) ||
                    (u.username && u.username.toLowerCase().includes(q)) ||
                    (u.queue_id && u.queue_id.toLowerCase().includes(q))
                );
                renderUsers(filtered);
            }

            function openModal(user) {
                document.getElementById('editUserId').value = user.user_id;
                document.getElementById('modalTitle').innerText = `Юзер: ${user.first_name || user.user_id}`;
                document.getElementById('editQueue').value = user.queue_id || '';
                document.getElementById('editLang').value = user.language || 'ua';
                document.getElementById('editNotify').checked = user.notifications_enabled;
                document.getElementById('editModal').classList.remove('hidden');
            }

            function closeModal() {
                document.getElementById('editModal').classList.add('hidden');
            }

            async function saveUser() {
                const id = document.getElementById('editUserId').value;
                const data = {
                    queue_id: document.getElementById('editQueue').value || null,
                    language: document.getElementById('editLang').value,
                    notifications_enabled: document.getElementById('editNotify').checked
                };

                await fetch(`/api/users/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });

                closeModal();
                loadUsers();
            }

            loadUsers();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
