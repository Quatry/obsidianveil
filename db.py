# db.py
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = "bot.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY,
        username TEXT,
        subscription_end TEXT,
        in_group INTEGER DEFAULT 0,
        notify_7_days INTEGER DEFAULT 0,
        notify_1_day INTEGER DEFAULT 0,
        last_invoice_time TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invite_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER,
        invite_link TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now')),
        used INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS agreements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER,
        username TEXT,
        offer_type TEXT,
        offer_version TEXT,
        accepted_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pending_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER,
        username TEXT,
        plan TEXT,
        amount INTEGER,
        status TEXT DEFAULT 'pending', -- pending, awaiting_review, confirmed, rejected, cancelled
        proof_file_id TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        admin_id INTEGER,
        admin_note TEXT
    )
    """)

    conn.commit()
    conn.close()


def add_or_update_user(tg_id: int, days: int = 30, username: str | None = None, in_group: bool = False):
    """Добавляет или продлевает подписку; возвращает datetime object новой даты окончания."""
    conn = _conn()
    cur = conn.cursor()

    cur.execute("SELECT subscription_end FROM users WHERE tg_id = ?", (tg_id,))
    result = cur.fetchone()

    if result and result[0]:
        try:
            current_end = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            current_end = datetime.now()
        new_end = current_end + timedelta(days=days)
    else:
        new_end = datetime.now() + timedelta(days=days)

    subscription_end_str = new_end.strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,))
    existing = cur.fetchone()
    if existing:
        cur.execute("""
            UPDATE users
            SET subscription_end = ?, username = ?, in_group = ?
            WHERE tg_id = ?
        """, (subscription_end_str, username, 1 if in_group else 0, tg_id))
    else:
        cur.execute("""
            INSERT INTO users (tg_id, username, subscription_end, in_group)
            VALUES (?, ?, ?, ?)
        """, (tg_id, username, subscription_end_str, 1 if in_group else 0))

    conn.commit()
    conn.close()
    return new_end


def is_user_in_group(tg_id: int) -> bool:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT in_group FROM users WHERE tg_id = ?", (tg_id,))
    r = cur.fetchone()
    conn.close()
    return bool(r[0]) if r else False


def set_user_in_group(tg_id: int, in_group: bool):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET in_group = ? WHERE tg_id = ?", (1 if in_group else 0, tg_id))
    conn.commit()
    conn.close()


def get_user_subscription_end(tg_id: int):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT subscription_end FROM users WHERE tg_id = ?", (tg_id,))
    r = cur.fetchone()
    conn.close()
    if r and r[0]:
        return datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
    return None


def get_expired_subscriptions():
    """Возвращает список (tg_id, username) для тех, у кого subscription_end < now и in_group = 1"""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT tg_id, username
        FROM users
        WHERE datetime(subscription_end) < datetime('now')
          AND in_group = 1
    """)
    res = cur.fetchall()
    conn.close()
    return res


def get_users_expiring_in(days: int):
    """Возвращает (tg_id, username, subscription_end, notify_flag) для пользователей, чья подписка кончается через `days`."""
    conn = _conn()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        SELECT tg_id, username, subscription_end, notify_1_day
        FROM users
        WHERE datetime(subscription_end) BETWEEN datetime(?) AND datetime(?)
    """, (now, target))
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_user_notified_1_day(tg_id: int):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET notify_1_day = 1 WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()


def create_pending_payment(tg_id: int, username: str | None, plan: str, amount: int) -> int:
    """Создаёт (или обновляет существующий) pending payment."""
    conn = _conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM pending_payments WHERE tg_id = ? AND status IN ('pending','awaiting_review')", (tg_id,))
    r = cur.fetchone()
    if r:
        pid = r[0]
        cur.execute("""
            UPDATE pending_payments
            SET plan = ?, amount = ?, status = 'pending', proof_file_id = NULL, created_at = datetime('now')
            WHERE id = ?
        """, (plan, amount, pid))
    else:
        cur.execute("""
            INSERT INTO pending_payments (tg_id, username, plan, amount, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (tg_id, username, plan, amount))
        pid = cur.lastrowid

    conn.commit()
    conn.close()
    return pid


def get_pending_by_user(tg_id: int) -> Optional[dict]:
    conn = _conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tg_id, username, plan, amount, status, proof_file_id, created_at
        FROM pending_payments
        WHERE tg_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (tg_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return dict(r)


def get_pending_by_id(pid: int) -> Optional[dict]:
    conn = _conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_payments WHERE id = ?", (pid,))
    r = cur.fetchone()
    conn.close()
    return dict(r) if r else None


def set_pending_proof(payment_id: int, file_id: str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("UPDATE pending_payments SET proof_file_id = ?, status = 'awaiting_review' WHERE id = ?",
                (file_id, payment_id))
    conn.commit()
    conn.close()


def set_pending_status(payment_id: int, status: str, admin_id: int | None = None, admin_note: str | None = None):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("UPDATE pending_payments SET status = ?, admin_id = ?, admin_note = ? WHERE id = ?",
                (status, admin_id, admin_note, payment_id))
    conn.commit()
    conn.close()


def delete_pending_by_user(tg_id: int):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM pending_payments WHERE tg_id = ? AND status IN ('pending','awaiting_review')", (tg_id,))
    conn.commit()
    conn.close()


def save_agreement(tg_id: int, username: str | None, offer_type: str, offer_version: str = "v1"):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO agreements (tg_id, username, offer_type, offer_version, accepted_at)
        VALUES (?, ?, ?, ?, ?)
    """, (tg_id, username, offer_type, offer_version, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def save_invite_link(tg_id: int, invite_link: str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO invite_links (tg_id, invite_link) VALUES (?, ?)", (tg_id, invite_link))
    conn.commit()
    conn.close()


# ===== Логика для чеков и платежей =====

_receipt_waiting: dict[int, dict[str, str]] = {}


def set_receipt_waiting(user_id: int, pid: str | None, plan: str | None = None):
    """
    Устанавливает, что пользователь ожидает прикрепления чека.
    Если pid=None — снимает ожидание.
    """
    global _receipt_waiting
    if pid is None:
        _receipt_waiting.pop(user_id, None)
    else:
        _receipt_waiting[user_id] = {"pid": pid, "plan": plan}


def get_receipt_waiting(user_id: int) -> dict | None:
    """
    Возвращает данные pending заявки, для которой пользователь должен прикрепить чек.
    """
    return _receipt_waiting.get(user_id)


def save_receipt_file(pid: int, file_id: str):
    """Сохраняет file_id чека и переводит заявку в статус 'awaiting_review'"""
    set_pending_proof(pid, file_id)


def set_payment_status(pid: int, status: str):
    """Меняет статус pending payment на approved/rejected"""
    set_pending_status(pid, status)


def get_payment(pid: int) -> Optional[dict]:
    """Возвращает информацию о pending payment по id"""
    return get_pending_by_id(pid)


_contacts_waiting: dict[int, dict[str, str]] = {}


def set_contacts_waiting(user_id: int, pid: str):
    """Устанавливает состояние ожидания контактных данных"""
    global _contacts_waiting
    _contacts_waiting[user_id] = {"pid": pid}


def get_contacts_waiting(user_id: int):
    """Получает информацию об ожидании контактов"""
    return _contacts_waiting.get(user_id)


def update_payment_contacts(pid: int, phone: str, email: str):
    """Обновляет контактные данные в записи платежа"""
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE pending_payments ADD COLUMN phone TEXT")
        cur.execute("ALTER TABLE pending_payments ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass

    cur.execute("UPDATE pending_payments SET phone = ?, email = ? WHERE id = ?", (phone, email, pid))
    conn.commit()
    conn.close()


def clear_user_state(user_id: int):
    """Очищает состояние пользователя"""
    global _receipt_waiting, _contacts_waiting
    _receipt_waiting.pop(user_id, None)
    _contacts_waiting.pop(user_id, None)
