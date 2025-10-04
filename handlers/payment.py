import secrets

from aiogram import Router, F, Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import config
from db import get_pending_by_user, set_pending_status, add_or_update_user, set_user_in_group

router = Router()


@router.callback_query(F.data == "attach_receipt")
async def attach_receipt_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        "📎 Прикрепите скриншот или файл чека. После отправки администратор получит уведомление."
    )
    await callback.answer()


@router.message(F.photo | F.document)
async def receive_receipt(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    caption = f"💳 Пользователь @{username} (ID: {user_id}) прислал чек для подтверждения оплаты."

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"accept:{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")
            ]
        ]
    )

    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            await bot.send_photo(chat_id=config.ADMIN_ID, photo=file_id, caption=caption, reply_markup=keyboard)
        elif message.document:
            await bot.send_document(chat_id=config.ADMIN_ID, document=message.document.file_id, caption=caption,
                                    reply_markup=keyboard)
        else:
            await message.answer("❌ Пожалуйста, прикрепите скриншот или файл чека.")
            return

        await message.answer("✅ Чек отправлен администратору. После проверки вам активируют доступ.")

    except Exception as e:
        await message.answer("❌ Не удалось отправить чек администратору. Свяжитесь с поддержкой.")
        if config.ADMIN_ID:
            await bot.send_message(config.ADMIN_ID, f"Ошибка отправки чека от @{username}: {e}")


@router.callback_query(F.data.startswith("accept:"))
async def accept_payment(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split(":")[1])

    pending = get_pending_by_user(user_id)
    if not pending:
        await callback.message.answer("❌ Ошибка: заявка не найдена.")
        await callback.answer("Ошибка")
        return

    plan = pending['plan']
    days = 30 if plan == 'month' else 365

    set_pending_status(pending['id'], 'confirmed', admin_id=callback.from_user.id)

    new_end = add_or_update_user(user_id, days=days, username=pending['username'], in_group=False)

    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    formatted_date = f"{new_end.day} {months[new_end.month - 1]} {new_end.year} года в {new_end.strftime('%H:%M')}"

    try:
        token = secrets.token_urlsafe(6)
        invite = await bot.create_chat_invite_link(
            chat_id=config.PRIVATE_GROUP_CHAT_ID,
            name=f"invite_{user_id}_{token}",
            expire_date=int((datetime.utcnow() + timedelta(days=1)).timestamp()),
            member_limit=1
        )
        invite_link = invite.invite_link

        set_user_in_group(user_id, True)

        await bot.send_message(
            user_id,
            "✅ Ваша заявка принята! Подписка активирована.\n\n"
            "🎉 Ваша уникальная ссылка для вступления в закрытую группу:\n"
            f"{invite_link}\n\n"
            f"📅 Подписка действительна до: {formatted_date}\n\n"
            "⚠️ Ссылка одноразовая и действует 24 часа."
        )

        if config.ADMIN_ID:
            await bot.send_message(
                config.ADMIN_ID,
                f"💰 Новый платёж от @{pending['username']} (ID: {user_id})\n"
                f"📦 Тариф: {'1 месяц' if plan == 'month' else '1 год'}\n"
                f"📅 Подписка до: {formatted_date}\n"
                f"🔗 Инвайт: {invite_link}"
            )

    except Exception as e:
        await bot.send_message(user_id,
                               "✅ Заявка принята, но не удалось создать ссылку. Свяжитесь с администратором."
                               )
        if config.ADMIN_ID:
            await bot.send_message(config.ADMIN_ID, f"❌ Ошибка генерации инвайта для {user_id}: {e}")

    await callback.message.edit_reply_markup(None)
    await callback.answer("Пользователь принят.")


@router.callback_query(F.data.startswith("reject:"))
async def reject_payment(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split(":")[1])

    pending = get_pending_by_user(user_id)
    if pending:
        set_pending_status(pending['id'], 'rejected', admin_id=callback.from_user.id)

    await bot.send_message(user_id, "❌ Ваша заявка отклонена. Попробуйте снова или свяжитесь с поддержкой.")

    await callback.message.edit_reply_markup(None)
    await callback.answer("Пользователь отклонён.")
