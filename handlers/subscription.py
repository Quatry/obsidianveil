from __future__ import annotations

import re
from datetime import datetime, timedelta

import logging
import secrets

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.filters import Command

import db
import config
from handlers.shared import offer_text, months, consultation_text, amulet_text, subscription_text
from keyboards import main_menu, subscription_menu, support_keyboard, menu_keyboard, consultation_menu, amulet_menu

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
        await callback.message.edit_text(text=subscription_text, reply_markup=subscription_menu)
        await callback.answer()
        return

    if service == "consultation":
        await callback.message.edit_text(text=consultation_text, reply_markup=consultation_menu)
        await callback.answer()
        return

    if service == "amulet":
        await callback.message.edit_text(text=amulet_text, reply_markup=amulet_menu)
        await callback.answer()
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
        f"💳 Оплата услуги: <b>{plan_text}</b>\n\n"
        f"💰 Сумма: <b>{rub:.2f}</b> руб.\n\n"
        "Реквизиты для перевода:\n"
        "🔹 Сбербанк: <b>40817810403005867172</b>\n"
        "🔹 Альфа: <b>40817810805614823674</b>\n\n"
        "После оплаты:\n"
        "1️⃣ Нажмите «📎 Прикрепить чек» и отправьте фото или скриншот\n"
        "2️⃣ Затем укажите номер телефона и электронную почту\n\n"
        "⚠️ <b>Не переходите в главное меню до завершения процесса</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Прикрепить чек", callback_data=f"attach_receipt:{pid}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_offer")]
    ])

    try:
        await callback.message.edit_text(text=text, reply_markup=kb)
    except Exception:
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

    try:
        await callback.message.edit_text(
            "📎 Пожалуйста, отправьте фото или документ с чеком.\n\n"
            "❗ Только изображение или файл — текстовые сообщения не принимаются."
        )
    except Exception:
        await callback.message.answer(
            "📎 Пожалуйста, отправьте фото или документ с чеком.\n\n"
            "❗ Только изображение или файл — текстовые сообщения не принимаются."
        )

    await callback.answer()


# === Этап 5. Приём фото или документа от пользователя ===
@router.message(F.photo | F.document)
async def handle_receipt_upload(message: Message):
    user_id = message.from_user.id
    pending = db.get_receipt_waiting(user_id)
    if not pending:
        return

    pid = pending["pid"]
    plan = pending["plan"]

    file_id = message.photo[-1].file_id if message.photo else message.document.file_id

    db.save_receipt_file(pid, file_id)
    db.set_receipt_waiting(user_id, None)

    # Переходим к сбору контактных данных
    db.set_contacts_waiting(user_id, pid)

    await message.answer(
        "✅ Чек получен! Теперь укажите ваши контактные данные:\n\n"
        "📱 <b>Номер телефона</b> и 📧 <b>Email</b>\n\n"
        "Отправьте их в формате:\n"
        "<code>+79991234567</code>\n<code>example@mail.ru</code>",
        parse_mode="HTML"
    )


# === Этап 6. Сбор контактных данных ===
@router.message(F.text)
async def handle_contacts(message: Message):
    user_id = message.from_user.id
    pending = db.get_contacts_waiting(user_id)

    if not pending:
        return  # Игнорируем текстовые сообщения не в состоянии ожидания контактов

    pid = pending["pid"]
    text = message.text.strip()

    # Парсим контактные данные
    phone = None
    email = None

    lines = text.split('\n')
    for line in lines:
        if 'телефон:' in line.lower() or 'phone:' in line.lower():
            phone = line.split(':', 1)[1].strip()
        elif 'email:' in line.lower() or 'почта:' in line.lower():
            email = line.split(':', 1)[1].strip()

    # Если не найдено в структурированном формате, пробуем извлечь из текста
    if not phone or not email:
        # Простая валидация email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            email = emails[0]

        # Простая валидация телефона
        phone_pattern = r'[\+]?[7|8]?[\s]?[\(]?[0-9]{3}[\)]?[\s]?[0-9]{3}[\s]?[0-9]{2}[\s]?[0-9]{2}'
        phones = re.findall(phone_pattern, text)
        if phones:
            phone = phones[0].strip()

    if not phone or not email:
        await message.answer(
            "❌ Не удалось распознать контактные данные.\n\n"
            "Пожалуйста, отправьте в формате:\n"
            "<code>+79991234567</code>\n<code>example@mail.ru</code>",
            parse_mode="HTML"
        )
        return

    # Сохраняем контактные данные
    db.update_payment_contacts(pid, phone, email)

    # Сбрасываем состояние ожидания
    db.clear_user_state(user_id)

    # Уведомляем админа
    pending_data = db.get_payment(pid)
    if pending_data and config.ADMIN_ID:
        plan = pending_data["plan"]
        amount = pending_data["amount"] / 100
        username = pending_data.get("username") or str(user_id)
        plan_text = (
            "Консультация" if plan == "consultation"
            else "Амулет" if plan == "amulet"
            else "Подписка"
        )

        admin_text = (
            f"🆕 Новая заявка на оплату #{pid}\n\n"
            f"👤 Пользователь: @{username} (ID: {user_id})\n"
            f"📦 Услуга: <b>{plan_text}</b>\n"
            f"💰 Сумма: <b>{amount:.2f}</b> руб.\n"
            f"📱 Телефон: <b>{phone}</b>\n"
            f"📧 Email: <b>{email}</b>\n\n"
            f"Для подтверждения используйте кнопки ниже:"
        )

        kb_admin = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve:{pid}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{pid}")
            ],
            [InlineKeyboardButton(text="💬 Перейти к пользователю", url=f"tg://user?id={user_id}")]
        ])

        # Отправляем чек админу, если есть
        if pending_data.get("proof_file_id"):
            try:
                if pending_data["proof_file_id"].startswith("AgAC"):  # фото
                    await message.bot.send_photo(
                        chat_id=config.ADMIN_ID,
                        photo=pending_data["proof_file_id"],
                        caption=admin_text,
                        reply_markup=kb_admin
                    )
                else:  # документ
                    await message.bot.send_document(
                        chat_id=config.ADMIN_ID,
                        document=pending_data["proof_file_id"],
                        caption=admin_text,
                        reply_markup=kb_admin
                    )
            except Exception as e:
                logger.error(f"Ошибка отправки чека админу: {e}")
                await message.bot.send_message(
                    chat_id=config.ADMIN_ID,
                    text=admin_text + f"\n\n❌ Чек не загружен: {e}",
                    reply_markup=kb_admin
                )
        else:
            await message.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=admin_text,
                reply_markup=kb_admin
            )

    await message.answer(
        "✅ Спасибо! Ваши контактные данные получены.\n\n"
        "Ожидайте подтверждения оплаты Мастером. Вы получите уведомление, "
        "когда доступ будет активирован.",
        reply_markup=menu_keyboard
    )


# === Этап 7. Подтверждение или отклонение (для администратора) ===
@router.callback_query(F.data.startswith("approve:") | F.data.startswith("reject:"))
async def handle_admin_decision(callback: CallbackQuery):
    try:
        action, pid = callback.data.split(":", 1)
    except ValueError:
        await callback.answer("Ошибка ID.", show_alert=True)
        return

    # Проверяем текущий статус платежа
    pending = db.get_payment(pid)
    if pending and pending["status"] in ["approved", "rejected"]:
        await callback.answer("Этот платёж уже обработан.", show_alert=True)
        return

    approved = action == "approve"
    db.set_payment_status(pid, "approved" if approved else "rejected")

    text = (
        "✅ Оплата подтверждена. Пользователь уведомлён." if approved
        else "❌ Оплата отклонена. Пользователь уведомлён."
    )

    # Создаем новую клавиатуру с заблокированными кнопками
    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтверждён",
                callback_data="already_processed"
            ) if approved else InlineKeyboardButton(
                text="❌ Отклонён",
                callback_data="already_processed"
            )
        ],
        [InlineKeyboardButton(text="💬 Перейти к пользователю", url=f"tg://user?id={pending['tg_id']}")]
    ])

    # Обновляем сообщение с заблокированными кнопками
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n🧾 Статус: {'✅ Подтверждён' if approved else '❌ Отклонён'}",
        reply_markup=new_keyboard
    )

    # Остальной код обработки уведомлений пользователя...
    if pending:
        uid = pending["tg_id"]
        username = pending.get("username") or str(uid)
        plan = pending["plan"]
        amount = pending["amount"]
        days_map = {
            50000: 30,
            120000: 90,
            220000: 180,
            400000: 365
        }
        days = days_map.get(amount, 30)

        if approved:
            if plan == "subscription":
                in_group = db.is_user_in_group(uid)
                new_end = db.add_or_update_user(uid, days=days, username=username, in_group=in_group)

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


# Обработчик для заблокированных кнопок
@router.callback_query(F.data == "already_processed")
async def handle_already_processed(callback: CallbackQuery):
    await callback.answer("Этот платёж уже обработан.", show_alert=True)


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
