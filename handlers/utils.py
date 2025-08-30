import os
from aiogram import Bot
from aiogram.types import LabeledPrice


async def send_invoice(bot: Bot, chat_id: int, title: str, amount: int, payload: str):
    prices = [LabeledPrice(label=title, amount=amount)]
    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=f"{title} для доступа в закрытую группу",
        payload=payload,
        provider_token=os.getenv("PAYMENT_TOKEN"),
        currency="RUB",
        prices=prices,
        start_parameter=payload
    )
