from aiogram import Router, F, Bot
from aiogram.types import Message
import db, config

router = Router()


@router.pre_checkout_query()
async def pre_checkout_handler(query):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    months = [
        'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    in_group = db.is_user_in_group(user_id)
    days = 30 if payload == "month_subscription" else 365
    new_end_date = db.add_or_update_user(user_id, days=days, username=username, in_group=in_group)

    formatted_date = f"{new_end_date.day} {months[new_end_date.month - 1]} {new_end_date.year} года в {new_end_date.strftime('%H:%M')}"

    if not in_group:
        invite_link = await db.create_invite_link(user_id)
        if invite_link:
            db.set_user_in_group(user_id, True)
            await message.answer(
                f"✅ Оплата прошла успешно! Подписка активирована.\n\n"
                f"🎉 Ссылка: {invite_link}\n\n"
                f"📅 Подписка действительна до: {formatted_date}"
            )
            if config.ADMIN_ID:
                await bot.send_message(
                    config.ADMIN_ID,
                    f"💰 Новый платёж от @{username} (ID: {user_id})\n"
                    f"📦 Тариф: {'1 месяц' if payload == 'month_subscription' else '1 год'}\n"
                    f"📅 Подписка действительна до: {formatted_date}\n"
                    f"🔗 Инвайт: {invite_link}"
                )
        else:
            await message.answer("✅ Оплата прошла, но ссылка не сгенерировалась. Свяжитесь с @Obsidianveil74.")
    else:
        await message.answer(
            f"✅ Оплата прошла успешно! Подписка продлена.\n"
            f"📅 Новая дата окончания: {formatted_date}"
        )
