import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("bot.db")
cur = conn.cursor()

tg_id = 799106955  # твой тестовый ID
username = "quatryh"
subscription_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

cur.execute(
    "INSERT OR REPLACE INTO users (tg_id, username, subscription_end, in_group) VALUES (?, ?, ?, ?)",
    (tg_id, username, subscription_end, True)
)
conn.commit()
conn.close()
