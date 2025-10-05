from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, PreCheckoutQuery

import config
import db
from keyboards import menu_keyboard, support_keyboard

router = Router()
logger = logging.getLogger(__name__)

PAYMENT_NAMES = {
    "month_subscription": "Подписка на месяц",
    "year_subscription": "Подписка на год",
    "consultation_payment": "Оплата консультации",
    "amulet_payment": "Оплата амулета"
}


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    payment_name = PAYMENT_NAMES.get(payload, payload)

    logger.info(f"✅ Успешная оплата от {username} ({user_id}) — {payment_name}")

    if payload in ["month_subscription", "year_subscription"]:
        days = 30 if payload == "month_subscription" else 365
        in_group = db.is_user_in_group(user_id)
        new_end = db.add_or_update_user(user_id, days=days, username=username, in_group=in_group)

        months = [
            'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
            'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
        ]
        formatted_date = f"{new_end.day} {months[new_end.month - 1]} {new_end.year} года в {new_end.strftime('%H:%M')}"

        if not in_group:
            try:
                token = secrets.token_urlsafe(6)
                invite = await bot.create_chat_invite_link(
                    chat_id=config.PRIVATE_GROUP_CHAT_ID,
                    name=f"invite_{user_id}_{token}",
                    expire_date=int((datetime.utcnow() + timedelta(days=1)).timestamp()),
                    member_limit=1,
                )
                invite_link = invite.invite_link
                db.set_user_in_group(user_id, True)

                await message.answer(
                    f"✅ {payment_name} прошла успешно!\n\n"
                    f"🎉 Ваша ссылка для вступления в закрытую группу:\n{invite_link}\n\n"
                    f"📅 Подписка активна до: {formatted_date}",
                    reply_markup=menu_keyboard
                )

                if config.ADMIN_ID:
                    await bot.send_message(
                        config.ADMIN_ID,
                        f"💰 Новый платёж от @{username} (ID: {user_id})\n"
                        f"📦 {payment_name}\n"
                        f"📅 Подписка до: {formatted_date}\n"
                        f"🔗 Ссылка: {invite_link}"
                    )

            except Exception as e:
                await message.answer(
                    "✅ Оплата прошла, но не удалось создать ссылку. Свяжитесь с Мастером.",
                    reply_markup=support_keyboard
                )
                logger.error(f"Ошибка генерации ссылки для {user_id}: {e}")
        else:
            await message.answer(
                f"✅ Подписка продлена!\n\n📅 Новая дата окончания: {formatted_date}",
                reply_markup=menu_keyboard
            )

    elif payload in ["consultation_payment", "amulet_payment"]:
        await message.answer(
            f"✅ {payment_name} успешно произведена!\n\n"
            "📸 Пожалуйста, прикрепите чек об оплате для подтверждения.",
            reply_markup=menu_keyboard
        )
        if config.ADMIN_ID:
            await bot.send_message(
                config.ADMIN_ID,
                f"💰 Новый платёж: {payment_name}\n"
                f"От @{username} (ID: {user_id})",
            )
