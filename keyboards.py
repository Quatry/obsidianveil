from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import PUBLIC_GROUP_URL, ADMIN_URL, BLOG_URL

# Главное меню
main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💎 Присоединиться к закрытой группе", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="🧘 Записаться на консультацию", callback_data="buy_consultation")],
        [InlineKeyboardButton(text="🔮 Приобрести амулет", callback_data="buy_amulet")],
        [InlineKeyboardButton(text="🌿 Перейти в визуальный блог", url=BLOG_URL)],
        [InlineKeyboardButton(text="💬 Войти в открытую группу", url=PUBLIC_GROUP_URL)],
    ]
)

# Меню согласия с офертой
offer_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="accept_offer")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
    ]
)

# Меню выбора подписки
subscription_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц — 500 руб", callback_data="create_pending:subscription:50000")],
        [InlineKeyboardButton(text="3 месяца — 1200 руб", callback_data="create_pending:subscription:120000")],
        [InlineKeyboardButton(text="6 месяцев — 2200 руб", callback_data="create_pending:subscription:220000")],
        [InlineKeyboardButton(text="12 месяцев — 4000 руб", callback_data="create_pending:subscription:400000")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_offer")]
    ]
)

# Меню консультации
consultation_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Краткая диагностика — 1700 руб",
                              callback_data="create_pending:consultation:170000")],
        [InlineKeyboardButton(text="Полный разбор — 7000 руб",
                              callback_data="create_pending:consultation:700000")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
    ]
)

# Меню амулетов
amulet_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Амулет — 15000 руб", callback_data="create_pending:amulet:1500000")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")]
    ]
)

# Клавиатура для связи с поддержкой
support_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Связаться с поддержкой",
            url=ADMIN_URL
        )]
    ]
)

menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Главное меню", callback_data="back_main")]]
)


# Универсальная клавиатура для оплаты
def payment_keyboard(url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=url)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_offer")]
        ]
    )
