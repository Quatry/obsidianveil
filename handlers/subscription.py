from __future__ import annotations

from datetime import datetime, timedelta

import logging
import secrets

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.filters import Command

import db
import config
from handlers.shared import offer_text
from keyboards import main_menu, subscription_menu, support_keyboard, menu_keyboard

router = Router()
logger = logging.getLogger(__name__)


async def safe_edit_or_send(callback: CallbackQuery, text: str, reply_markup):
    """Попробовать edit_text, иначе отправить новое сообщение."""
    if callback.message and callback.message.text:
        try:
            await callback.message.edit_text(text=text, reply_markup=reply_markup)
        except Exception:
            await callback.message.answer(text=text, reply_markup=reply_markup)
    else:
        await callback.message.answer(text=text, reply_markup=reply_markup)
    await callback.answer()


# === Этап 1. Переход к публичной оферте ===
@router.callback_query(F.data == "buy_subscription")
async def buy_subscription_offer(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="accept_offer:subscription")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
    ])
    await safe_edit_or_send(callback, offer_text, kb)


@router.callback_query(F.data == "buy_consultation")
async def buy_consultation_offer(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="accept_offer:consultation")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
    ])
    await safe_edit_or_send(callback, offer_text, kb)


@router.callback_query(F.data == "buy_amulet")
async def buy_amulet_offer(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="accept_offer:amulet")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
    ])
    await safe_edit_or_send(callback, offer_text, kb)


# === Этап 2. После согласия с офертой ===
@router.callback_query(F.data.startswith("accept_offer"))
async def accept_offer(callback: CallbackQuery):
    try:
        _, service = callback.data.split(":", 1)
    except ValueError:
        service = "subscription"

    if service == "subscription":
        await safe_edit_or_send(callback, "Выберите тариф подписки:", subscription_menu)
        return

    if service == "consultation":
        text = (
            "🧘 Консультация — индивидуальная работа с вами, разбор ситуации и рекомендации.\n\n"
            "💰 Стоимость: <b>5000 руб</b>.\n\n"
            "После оплаты прикрепите чек — Мастер свяжется с вами для назначения времени."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить консультацию — 5000 руб",
                                  callback_data="create_pending:consultation:500000")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
        ])
        await safe_edit_or_send(callback, text, kb)
        return

    if service == "amulet":
        text = (
            "🔮 Амулет изготавливается индивидуально под вас.\n\n"
            "💰 Стоимость: <b>2500 руб</b>.\n\n"
            "После оплаты прикрепите чек — мастер свяжется с вами для уточнения деталей."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить амулет — 2500 руб", callback_data="create_pending:amulet:250000")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
        ])
        await safe_edit_or_send(callback, text, kb)
        return


# === Этап 3. Создание заявки (pending) ===
@router.callback_query(F.data.startswith("create_pending:"))
async def create_pending_handler(callback: CallbackQuery):
    try:
        _, plan, amount_s = callback.data.split(":", 2)
        amount = int(amount_s)
    except Exception:
        await callback.answer("Ошибка формирования заявки.", show_alert=True)
        return

    user = callback.from_user
    pid = db.create_pending_payment(user.id, user.username or user.first_name, plan, amount)
    logger.info("Created pending payment %s for user %s plan=%s amount=%s", pid, user.id, plan, amount)

    plan_text = (
        "Консультация" if plan == "consultation"
        else "Амулет" if plan == "amulet"
        else "Подписка"
    )

    rub = amount / 100
    text = (
        f"💳 <b>Оплата услуги: {plan_text}</b>\n\n"
        f"💰 Сумма: {rub:.2f} руб.\n\n"
        "Реквизиты для перевода:\n"
        "🔹 Сбербанк: 1234 5678 9876 5432\n"
        "🔹 Тинькофф: 5555 6666 7777 8888\n\n"
        "После оплаты нажмите «📎 Прикрепить чек» и отправьте фото/файл."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Прикрепить чек", callback_data=f"attach_receipt:{pid}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
    ])

    await callback.message.answer(text=text, reply_markup=kb)
    await callback.answer("Заявка создана — прикрепите чек.")


# === Этап 4. Прикрепление чека ===
@router.callback_query(F.data.startswith("attach_receipt:"))
async def attach_receipt_prompt(callback: CallbackQuery):
    try:
        _, pid = callback.data.split(":", 1)
    except Exception:
        await callback.answer("Ошибка ID заявки.")
        return

    db.set_receipt_waiting(callback.from_user.id, pid)
    await callback.message.answer(
        "📎 Пожалуйста, отправьте фото или документ с чеком.\n\n"
        "❗ Только изображение или файл — текстовые сообщения не принимаются.",
        reply_markup=menu_keyboard
    )
    await callback.answer()


# === Этап 5. Приём фото или документа от пользователя ===
@router.message(F.photo | F.document)
async def handle_receipt_upload(message: Message):
    user_id = message.from_user.id
    pending = db.get_receipt_waiting(user_id)
    if not pending:
        return  # Игнорируем, если не ждём чек

    pid = pending["pid"]
    plan = pending["plan"]

    # Получаем file_id
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id

    db.save_receipt_file(pid, file_id)
    db.set_receipt_waiting(user_id, None)

    # Уведомляем администратора
    kb_admin = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve:{pid}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{pid}")
        ],
        [InlineKeyboardButton(text="💬 Перейти к пользователю", url=f"tg://user?id={user_id}")]
    ])

    plan_text = (
        "Консультация" if plan == "consultation"
        else "Амулет" if plan == "amulet"
        else "Подписка"
    )

    await message.bot.send_photo(
        config.ADMIN_ID,
        photo=file_id,
        caption=f"💰 Новый чек по заявке #{pid}\n"
                f"👤 Пользователь: @{message.from_user.username or message.from_user.first_name}\n"
                f"💫 Услуга: {plan_text}",
        reply_markup=kb_admin
    )

    await message.answer(
        "✅ Чек отправлен. Мастер проверит оплату и свяжется с вами.",
        reply_markup=menu_keyboard
    )


# === Этап 6. Подтверждение или отклонение (для администратора) ===
@router.callback_query(F.data.startswith("approve:") | F.data.startswith("reject:"))
async def handle_admin_decision(callback: CallbackQuery):
    try:
        action, pid = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Ошибка ID.", show_alert=True)
        return

    approved = action == "approve"
    db.set_payment_status(pid, "approved" if approved else "rejected")

    text = (
        "✅ Оплата подтверждена. Пользователь уведомлён." if approved
        else "❌ Оплата отклонена. Пользователь уведомлён."
    )

    # обновляем сообщение у админа
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n🧾 Статус: {'✅ Подтверждён' if approved else '❌ Отклонён'}",
        reply_markup=callback.message.reply_markup
    )

    # уведомляем пользователя
    pending = db.get_payment(pid)
    if pending:
        uid = pending["tg_id"]
        username = pending.get("username") or str(uid)
        plan = pending["plan"]

        if approved:
            if plan == "subscription":
                # по аналогии с payment.py
                days = 30  # можно доработать: хранить срок тарифа в pending
                in_group = db.is_user_in_group(uid)
                new_end = db.add_or_update_user(uid, days=days, username=username, in_group=in_group)

                months = [
                    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
                ]
                formatted_date = f"{new_end.day} {months[new_end.month - 1]} {new_end.year} года в {new_end.strftime('%H:%M')}"

                if not in_group:
                    try:
                        token = secrets.token_urlsafe(6)
                        invite = await callback.bot.create_chat_invite_link(
                            chat_id=config.PRIVATE_GROUP_CHAT_ID,
                            name=f"invite_{uid}_{token}",
                            expire_date=int((datetime.utcnow() + timedelta(days=1)).timestamp()),
                            member_limit=1,
                        )
                        invite_link = invite.invite_link
                        db.set_user_in_group(uid, True)

                        await callback.bot.send_message(
                            uid,
                            f"✅ Подписка активирована!\n\n"
                            f"🎉 Ваша ссылка для вступления в закрытую группу:\n{invite_link}\n\n"
                            f"📅 Подписка активна до: {formatted_date}",
                            reply_markup=menu_keyboard
                        )

                        if config.ADMIN_ID:
                            await callback.bot.send_message(
                                config.ADMIN_ID,
                                f"💰 Подтверждён платёж от @{username} (ID: {uid})\n"
                                f"📦 Подписка\n"
                                f"📅 До: {formatted_date}\n"
                                f"🔗 Ссылка: {invite_link}"
                            )

                    except Exception as e:
                        await callback.bot.send_message(
                            uid,
                            "✅ Оплата подтверждена, но не удалось создать ссылку. Свяжитесь с Мастером.",
                            reply_markup=support_keyboard
                        )
                        logger.error(f"Ошибка генерации ссылки для {uid}: {e}")
                else:
                    await callback.bot.send_message(
                        uid,
                        f"✅ Подписка продлена!\n\n📅 Новая дата окончания: {formatted_date}",
                        reply_markup=menu_keyboard
                    )

            elif plan in ["consultation", "amulet"]:
                await callback.bot.send_message(
                    uid,
                    "✨ Ваш платёж подтверждён. Спасибо!\n"
                    "Мастер свяжется с вами в ближайшее время.",
                    reply_markup=menu_keyboard
                )
        else:
            await callback.bot.send_message(
                uid,
                "❌ Ваш платёж не подтверждён.\nПожалуйста, свяжитесь с Мастером.",
                reply_markup=support_keyboard
            )

    await callback.answer(text)
    logger.info("Payment %s %s by admin", pid, action)


# === Кнопки "назад" ===
@router.callback_query(F.data == "back_offer")
async def back_offer(callback: CallbackQuery):
    await safe_edit_or_send(callback, offer_text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="accept_offer:subscription")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
    ]))


@router.callback_query(F.data == "back_main")
@router.message(Command("start"))
async def back_main(callback_or_message):
    text = "🌟 Добро пожаловать! Главное меню:"
    if isinstance(callback_or_message, CallbackQuery):
        await safe_edit_or_send(callback_or_message, text, main_menu)
    else:
        await callback_or_message.answer(text, reply_markup=main_menu)
