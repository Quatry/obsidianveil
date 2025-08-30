import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
import config
from handlers import routers
from scheduler import start_scheduler  # импорт твоей функции шедулера


async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    for r in routers:
        dp.include_router(r)

    print("Бот запущен...")

    # Запускаем шедулер параллельно с polling
    asyncio.create_task(start_scheduler(bot))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
