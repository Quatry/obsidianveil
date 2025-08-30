from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import PUBLIC_GROUP_URL, ADMIN_URL

# Главное меню
main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Перейти в общую группу", url=PUBLIC_GROUP_URL)],
        [InlineKeyboardButton(text="Купить подписку", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="Связаться", url=ADMIN_URL)],
        [InlineKeyboardButton(text="Информация", callback_data="info")]
    ]
)

information_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ]
)

# Подменю выбора подписки
subscription_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц", callback_data="buy_month")],
        [InlineKeyboardButton(text="1 год", callback_data="buy_year")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ]
)


# Кнопка оплаты (динамически создаётся в хендлере)
def payment_keyboard(url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=url)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_subscription")]
        ]
    )
