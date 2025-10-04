from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from handlers.shared import offer_text
from keyboards import main_menu, offer_menu, subscription_menu

router = Router()


@router.callback_query(F.data == "buy_subscription")
async def offer_handler(callback: CallbackQuery):
    if callback.message and callback.message.text:
        await callback.message.edit_text(text=offer_text, reply_markup=offer_menu)
    else:
        await callback.message.answer(text=offer_text, reply_markup=offer_menu)
    await callback.answer()


@router.callback_query(F.data == "accept_offer")
async def subscription_handler(callback: CallbackQuery):
    if callback.message and callback.message.text:
        await callback.message.edit_text(text="Выберите тариф подписки:", reply_markup=subscription_menu)
    else:
        await callback.message.answer(text="Выберите тариф подписки:", reply_markup=subscription_menu)
    await callback.answer()


@router.callback_query(F.data == "back_offer")
async def back_offer_handler(callback: CallbackQuery):
    if callback.message and callback.message.text:
        await callback.message.edit_text(text=offer_text, reply_markup=offer_menu)
    else:
        await callback.message.answer(text=offer_text, reply_markup=offer_menu)
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_main_handler(callback: CallbackQuery):
    if callback.message and callback.message.text:
        await callback.message.edit_text(text="Главное меню:", reply_markup=main_menu)
    else:
        await callback.message.answer(text="Главное меню:", reply_markup=main_menu)
    await callback.answer()


@router.callback_query(F.data.in_({"buy_month", "buy_year"}))
async def buy_plan_handler(callback: CallbackQuery):
    plans = {
        'buy_month': '1 месяц - 300руб',
        'buy_year': '1 год - 3000руб'
    }
    plan = plans.get(callback.data)
    text = (
        f"Вы выбрали тариф: <b>{plan}</b>\n\n"
        f"💳 Реквизиты для оплаты:\n"
        f"🔹 Сбербанк: 1234 5678 9876 5432\n"
        f"🔹 Тинькофф: 5555 6666 7777 8888\n\n"
        f"После оплаты прикрепите чек через кнопку ниже."
    )
    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📎 Прикрепить чек", callback_data="attach_receipt")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back_offer")]
            ]
        )
    )
    await callback.answer("Инструкция по оплате отправлена.")
