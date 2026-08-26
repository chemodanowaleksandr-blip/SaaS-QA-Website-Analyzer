import sqlite3
import time
import hashlib

DB_FILE = "users_history.db"

def hash_password(password):
    """Хэширует пароль (SHA-256) для безопасного хранения."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    """Создает таблицы пользователей и истории, если их нет."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Таблица аккаунтов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            created_at TEXT
        )
    """)
    
    # Таблица вечной истории проверок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            scan_time TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def register_user(username, password):
    """Регистрация нового пользователя."""
    username = username.strip().lower()
    if not username or not password:
        return False, "Логин и пароль не могут быть пустыми."
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        pwd_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, pwd_hash, current_time)
        )
        conn.commit()
        return True, "Регистрация успешна!"
    except sqlite3.IntegrityError:
        return False, "Этот логин уже занят."
    finally:
        conn.close()

def verify_user(username, password):
    """Проверка логина и пароля при входе."""
    username = username.strip().lower()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    pwd_hash = hash_password(password)
    cursor.execute(
        "SELECT username, plan FROM users WHERE username = ? AND password_hash = ?",
        (username, pwd_hash)
    )
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return True, {"username": user[0], "plan": user[1]}
    return False, None

def save_to_db_history(username, url, status):
    """Сохранение поискового лога."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO scan_history (username, url, status, scan_time) VALUES (?, ?, ?, ?)",
        (username, url, status, current_time)
    )
    conn.commit()
    conn.close()

def get_db_history(username):
    """Выгрузка истории конкретного юзера."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT url, status, scan_time FROM scan_history WHERE username = ? ORDER BY id DESC",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    history_list = []
    for row in rows:
        history_list.append({
            "URL": row[0],
            "Status": row[1],
            "Time": row[2]
        })
    return history_list

# Авто-инициализация базы при подключении модуля
init_db()
