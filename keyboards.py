from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import PUBLIC_GROUP_URL, ADMIN_URL, BLOG_URL

# Главное меню
main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Присоединиться к закрытой группе", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="Записаться на консультацию", callback_data="diagnostics_offer")],
        [InlineKeyboardButton(text="Перейти в визуальный блог", url=BLOG_URL)],
        [InlineKeyboardButton(text="Войти в открытую группу", url=PUBLIC_GROUP_URL)]
    ]
)

offer_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Согласен", callback_data="accept_offer")],
    [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
])

diagnostics_offer_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Согласен", callback_data="accept_diagnostics_offer")],
    [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
])

# --- Выбор тарифа ---
subscription_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="1 месяц — 350 руб", callback_data="buy_month")],
    [InlineKeyboardButton(text="1 год — 4000 руб", callback_data="buy_year")],
    [InlineKeyboardButton(text="↩️ Назад", callback_data="back_offer")]
])


# Кнопка оплаты (динамически создаётся в хендлере)
def payment_keyboard(url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=url)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_subscription")]
        ]
    )
