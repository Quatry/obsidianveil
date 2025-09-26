import sqlite3
from datetime import datetime, timedelta

tg_id = 799106955  # твой тестовый ID

conn = sqlite3.connect("bot.db")
cur = conn.cursor()

# Проставляем дату окончания подписки в прошлое
cur.execute("""
    UPDATE users
    SET subscription_end = ?, in_group = ?
    WHERE tg_id = ?
""", ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), 1, tg_id))

conn.commit()
conn.close()
