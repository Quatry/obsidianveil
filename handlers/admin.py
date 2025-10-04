import sqlite3
import csv
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
import config

router = Router()


@router.callback_query(lambda c: c.data == "agreements")
async def agreements_handler(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return await message.answer("❌ У вас нет прав для этой команды.")

    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("SELECT tg_id, username, offer_type, offer_version, accepted_at FROM agreements")
    rows = cur.fetchall()
    conn.close()

    # сохраняем во временный CSV
    filename = "agreements.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tg_id", "username", "offer_type", "offer_version", "accepted_at"])
        writer.writerows(rows)

    file = FSInputFile(filename)
    await message.answer_document(file, caption="📑 Список акцептов оферт")


@router.message(Command("get_id"))
async def get_id_handler(message: Message):
    chat_id = message.chat.id
    await message.answer(f"ID этой группы: {chat_id}")
