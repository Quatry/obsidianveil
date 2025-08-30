import asyncio
from aiogram import Bot, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import db
from config import PRIVATE_GROUP_CHAT_ID, ADMIN_ID

router = Router()


async def check_subscriptions(bot: Bot):
    """Проверяет истёкшие подписки и кикает пользователей"""
    try:
        expired_users = db.get_expired_subscriptions()  # синхронная функция возвращает list of tuples

        for user in expired_users:
            tg_id = user[0]
            username = user[1]

            # Для теста: пропускаем кик и сообщение самому себе
            is_self = tg_id == ADMIN_ID

            # Сбрасываем статус в группе сразу, чтобы не повторять уведомления
            db.set_user_in_group(tg_id, False)

            if not is_self:
                try:
                    # Пытаемся кикнуть пользователя (только если не себя)
                    await bot.ban_chat_member(PRIVATE_GROUP_CHAT_ID, tg_id)
                    await bot.unban_chat_member(PRIVATE_GROUP_CHAT_ID, tg_id)
                except Exception as e:
                    # Если пользователь уже не в группе или чат не подходит — игнорируем
                    print(f"Ошибка при кике пользователя {username}: {e}")

            # Уведомляем пользователя об удалении с кнопкой продления
            try:
                # Создаем клавиатуру с кнопкой продления
                renew_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="💳 Продлить подписку", callback_data="buy_subscription")]
                    ]
                )

                await bot.send_message(
                    tg_id,
                    "❌ Ваша подписка истекла!\n\n"
                    "Вы были удалены из закрытой группы. "
                    "Для продолжения доступа необходимо продлить подписку.\n\n"
                    "Нажмите кнопку ниже, чтобы выбрать тариф и оплатить:",
                    reply_markup=renew_keyboard
                )
                print(f"Уведомление отправлено пользователю {username} (ID: {tg_id})")

            except Exception as e:
                # Если не удалось отправить сообщение
                print(f"Не удалось уведомить пользователя {username}: {e}")

            # Отправляем уведомление администратору
            if ADMIN_ID:
                await bot.send_message(
                    ADMIN_ID,
                    f"👋 Пользователь @{username} (ID: {tg_id}) был удалён из закрытой группы по истечении подписки."
                )
            print(f"Удалён пользователь {username} (ID: {tg_id}) из закрытой группы")

    except Exception as e:
        print(f"Ошибка в шедулере: {e}")
        if ADMIN_ID:
            await bot.send_message(ADMIN_ID, f"❌ Ошибка в шедулере проверки подписок: {e}")


async def start_scheduler(bot: Bot):
    """Запускает периодическую проверку подписок"""
    while True:
        await check_subscriptions(bot)
        await asyncio.sleep(10)  # для теста, в бою 6*3600
