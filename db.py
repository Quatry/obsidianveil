import secrets
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot
from config import PRIVATE_GROUP_CHAT_ID, BOT_TOKEN

bot = Bot(token=BOT_TOKEN)


def init_db():
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()

    # Таблица пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            subscription_end TEXT,
            last_invoice_time TEXT,
            username TEXT,
            in_group BOOLEAN DEFAULT FALSE
        )
    """)

    # Таблица инвайт-ссылок
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invite_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            invite_link TEXT UNIQUE,
            created_at TEXT DEFAULT (datetime('now')),
            used BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (tg_id) REFERENCES users (tg_id)
        )
    """)

    conn.commit()
    conn.close()


def add_or_update_user(tg_id: int, days: int = 30, username: str = None, in_group: bool = False):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()

    cur.execute("SELECT subscription_end FROM users WHERE tg_id = ?", (tg_id,))
    result = cur.fetchone()

    if result and result[0]:
        current_end = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        new_end = current_end + timedelta(days=days)
    else:
        new_end = datetime.now() + timedelta(days=days)

    subscription_end_str = new_end.strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    existing_user = cur.fetchone()

    if existing_user:
        cur.execute("""
            UPDATE users 
            SET subscription_end = ?, username = ?, in_group = ?
            WHERE tg_id = ?
        """, (subscription_end_str, username, in_group, tg_id))
    else:
        cur.execute("""
            INSERT INTO users (tg_id, subscription_end, username, in_group) 
            VALUES (?, ?, ?, ?)
        """, (tg_id, subscription_end_str, username, in_group))

    conn.commit()
    conn.close()
    return new_end


async def create_invite_link(tg_id: int) -> str | None:
    """Создаёт уникальную одноразовую инвайт-ссылку для пользователя"""
    token = secrets.token_urlsafe(16)
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=PRIVATE_GROUP_CHAT_ID,
            name=f"invite_{tg_id}_{token}",
            expire_date=int((datetime.utcnow() + timedelta(days=1)).timestamp()),
            member_limit=1
        )
        invite_link = invite.invite_link
    except Exception as e:
        print(f"Ошибка при создании инвайта: {e}")
        return None

    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO invite_links (tg_id, invite_link) VALUES (?, ?)",
        (tg_id, invite_link),
    )
    conn.commit()
    conn.close()

    return invite_link


async def get_valid_invite_link(tg_id: int) -> str:
    """Получает валидную ссылку или создаёт новую"""
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("SELECT invite_link FROM invite_links WHERE tg_id = ? AND used = FALSE LIMIT 1", (tg_id,))
    result = cur.fetchone()
    conn.close()

    if result:
        return result[0]

    return await create_invite_link(tg_id)


def mark_invite_used(invite_link: str):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("UPDATE invite_links SET used = TRUE WHERE invite_link = ?", (invite_link,))
    conn.commit()
    conn.close()


def set_user_in_group(tg_id: int, in_group: bool):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("UPDATE users SET in_group = ? WHERE tg_id = ?", (1 if in_group else 0, tg_id))
    conn.commit()
    conn.close()


def is_user_in_group(tg_id: int) -> bool:
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("SELECT in_group FROM users WHERE tg_id = ?", (tg_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else False


def get_user_subscription(tg_id: int):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("SELECT subscription_end FROM users WHERE tg_id = ?", (tg_id,))
    result = cur.fetchone()
    conn.close()
    return result


def get_expired_subscriptions():
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        SELECT tg_id, username
        FROM users
        WHERE datetime(subscription_end) < datetime(?)
          AND in_group = 1
    """, (now,))
    result = cur.fetchall()
    conn.close()
    return result

def update_last_invoice_time(tg_id: int):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("UPDATE users SET last_invoice_time = ? WHERE tg_id = ?", (current_time, tg_id))
    conn.commit()
    conn.close()


def check_last_invoice_time(tg_id: int):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("SELECT last_invoice_time FROM users WHERE tg_id = ?", (tg_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def check_invite_token(token: str):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT il.tg_id, il.used, u.username 
        FROM invite_links il
        JOIN users u ON il.tg_id = u.tg_id
        WHERE il.invite_link LIKE ?
    """, (f"%{token}%",))
    result = cur.fetchone()
    conn.close()
    return result


def get_user_subscription_end(tg_id: int) -> datetime:
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("SELECT subscription_end FROM users WHERE tg_id = ?", (tg_id,))
    result = cur.fetchone()
    conn.close()

    if result and result[0]:
        return datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    return None
