from aiogram import Router
from aiogram.types import CallbackQuery, InputMediaPhoto
from keyboards import information_menu
from .shared import PHOTOS

router = Router()

@router.callback_query(lambda c: c.data == "info")
async def info_handler(callback: CallbackQuery):
    caption = (
        "Информация о подписке:\n\n"
        "— Доступ в закрытую группу\n"
        "— Тарифы: 1 месяц или 1 год"
    )
    await callback.message.edit_media(
        InputMediaPhoto(media=PHOTOS["info"], caption=caption),
        reply_markup=information_menu
    )
