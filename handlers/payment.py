from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, PreCheckoutQuery

import config
import db

router = Router()
logger = logging.getLogger(__name__)


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    in_group = db.is_user_in_group(user_id)

    days = 30 if payload == "month_subscription" else 365
    new_end = db.add_or_update_user(user_id, days=days, username=username, in_group=in_group)

    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября',
              'декабря']
    formatted_date = f"{new_end.day} {months[new_end.month - 1]} {new_end.year} года в {new_end.strftime('%H:%M')}"

    logger.info(f"Успешная оплата от {username or user_id}, payload={payload}")

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
                "✅ Оплата прошла успешно! Подписка активирована.\n\n"
                "🎉 Ваша уникальная ссылка для вступления в закрытую группу:\n"
                f"{invite_link}\n\n"
                f"📅 Подписка действительна до: {formatted_date}\n\n"
                "⚠️ Ссылка одноразовая и действует 24 часа."
            )

            if config.ADMIN_ID:
                await bot.send_message(
                    config.ADMIN_ID,
                    f"💰 Новый платёж от @{username} (ID: {user_id})\n"
                    f"📦 Тариф: {'1 месяц' if payload == 'month_subscription' else '1 год'}\n"
                    f"📅 Подписка до: {formatted_date}\n"
                    f"🔗 Инвайт: {invite_link}"
                )

        except Exception as e:
            await message.answer(
                "✅ Оплата прошла успешно! Но не удалось создать ссылку. Свяжитесь с администратором."
            )
            if config.ADMIN_ID:
                await bot.send_message(config.ADMIN_ID, f"❌ Ошибка генерации инвайта для {user_id}: {e}")

    else:
        # Продление
        await message.answer(
            "✅ Оплата прошла успешно! Ваша подписка продлена.\n\n"
            f"📅 Новая дата окончания: {formatted_date}\n\n"
            "Вы уже состоите в закрытой группе."
        )
