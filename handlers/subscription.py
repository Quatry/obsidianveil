import time
from aiogram import Router
from aiogram.types import CallbackQuery, InputMediaPhoto
from keyboards import subscription_menu
from .shared import PHOTOS, last_click
from .utils import send_invoice

router = Router()

@router.callback_query(lambda c: c.data == "buy_subscription")
async def buy_handler(callback: CallbackQuery):
    await callback.message.edit_media(
        InputMediaPhoto(media=PHOTOS["subscription"], caption="Выберите тариф"),
        reply_markup=subscription_menu
    )

@router.callback_query(lambda c: c.data in ["buy_month", "buy_year"])
async def payment_rate_limit_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_time = time.time()

    if user_id in last_click and (current_time - last_click[user_id]) < 10:
        await callback.answer("Подождите немного перед следующим запросом", show_alert=False)
        return

    last_click[user_id] = current_time

    if callback.data == "buy_month":
        await send_invoice(callback.message.bot, user_id, "Подписка на 1 месяц", 35000, "month_subscription")
    else:
        await send_invoice(callback.message.bot, user_id, "Подписка на 1 год", 400000, "year_subscription")

    await callback.answer("Счёт отправлен!")
