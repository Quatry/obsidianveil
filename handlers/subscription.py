from __future__ import annotations

import os
import time

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

import config
from handlers.shared import offer_text
from keyboards import main_menu, offer_menu, subscription_menu, diagnostics_offer_menu

router = Router()

# Антиспам по кликам (в памяти процесса)
_last_click: dict[int, float] = {}


async def _send_invoice(bot: Bot, chat_id: int, title: str, amount: int, payload: str):
    """
    Отправляет Telegram-инвойс (ЮKassa).
    amount — в копейках (350 руб -> 35000)
    """
    prices = [LabeledPrice(label=title, amount=amount)]
    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=f"{title} для доступа в закрытую группу",
        payload=payload,
        provider_token=config.PAYMENT_TOKEN or os.getenv("PAYMENT_TOKEN"),
        currency="RUB",
        prices=prices,
        start_parameter=payload,
    )


# --- Нажали "Присоединиться к закрытой группе" ---
@router.callback_query(F.data == "buy_subscription")
async def offer_handler(callback: CallbackQuery):
    # Меняем ТЕКСТ того же сообщения на оферту + кнопки оферты
    if callback.message and callback.message.text:
        await callback.message.edit_text(text=offer_text, reply_markup=offer_menu)
    else:
        # На случай если исходное сообщение было не текстом
        await callback.message.answer(text=offer_text, reply_markup=offer_menu)
    await callback.answer()


# --- Пользователь согласился с офертой ---
@router.callback_query(F.data == "accept_offer")
async def subscription_handler(callback: CallbackQuery):
    # В том же сообщении — меню тарифов
    if callback.message and callback.message.text:
        await callback.message.edit_text(text="Выберите тариф подписки:", reply_markup=subscription_menu)
    else:
        await callback.message.answer(text="Выберите тариф подписки:", reply_markup=subscription_menu)
    await callback.answer()


# --- Назад из тарифа → снова оферта ---
@router.callback_query(F.data == "back_offer")
async def back_offer_handler(callback: CallbackQuery):
    if callback.message and callback.message.text:
        await callback.message.edit_text(text=offer_text, reply_markup=offer_menu)
    else:
        await callback.message.answer(text=offer_text, reply_markup=offer_menu)
    await callback.answer()


@router.callback_query(lambda c: c.data == "diagnostics_offer")
async def diagnostics_offer_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        text=offer_text,
        reply_markup=diagnostics_offer_menu
    )


@router.callback_query(lambda c: c.data == "accept_diagnostics_offer")
async def accept_diagnostics_offer(callback: CallbackQuery):
    await callback.message.edit_text(
        text="✅ Вы согласились с офертой.\n\nИсполнитель услуг\nЛегенкина Полина Анатольевна\n\nНажмите на кнопку ниже, чтобы записаться на диагностику:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📅 Записаться", url=config.ADMIN_URL)],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
            ]
        )
    )


# --- Назад из оферты → главное меню ---
@router.callback_query(F.data == "back_main")
async def back_main_handler(callback: CallbackQuery):
    if callback.message and callback.message.text:
        await callback.message.edit_text(text="Главное меню:", reply_markup=main_menu)
    else:
        await callback.message.answer(text="Главное меню:", reply_markup=main_menu)
    await callback.answer()


# === КНОПКИ ТАРИФОВ (ОТПРАВКА ИНВОЙСОВ) ===

@router.callback_query(F.data.in_({"buy_month", "buy_year"}))
async def buy_plan_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    now = time.time()

    # Антиспам: не чаще 10 сек
    if user_id in _last_click and (now - _last_click[user_id]) < 10:
        await callback.answer("Подождите несколько секунд перед следующим запросом", show_alert=False)
        return
    _last_click[user_id] = now

    # Ничего не редактируем здесь — просто отправляем инвойс отдельным сообщением
    if callback.data == "buy_month":
        await _send_invoice(
            bot=callback.message.bot,
            chat_id=user_id,
            title="Подписка на 1 месяц",
            amount=35000,  # 350 руб
            payload="month_subscription",
        )
    else:
        await _send_invoice(
            bot=callback.message.bot,
            chat_id=user_id,
            title="Подписка на 1 год",
            amount=400000,  # 4000 руб
            payload="year_subscription",
        )

    await callback.answer("Счёт отправлен!")
