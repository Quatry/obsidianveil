from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from keyboards import main_menu
from .shared import PHOTOS, main_text

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        text=main_text,
        reply_markup=main_menu
    )


@router.callback_query(lambda c: c.data == "back_main")
async def back_main_handler(callback: CallbackQuery):
    await callback.message.edit_text(text=main_text, reply_markup=main_menu)
