import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from bot.config.config import load_config
from bot.keyboards.user import user_router
from bot.handlers.admin import admin_router
from bot.handlers.calculator import calc_router
from bot.database.models import async_main, async_session
from bot.middlewares.db import DatabaseMiddleware

async def on_startup(bot: Bot):
    # Настройка командного меню
    commands = [
        types.BotCommand(command="menu", description="Каталог рецептов"),
    ]
    await bot.set_my_commands(commands)

    # Создаем таблицы если их нет
    await async_main()
    
    # Добавим тестовые рецепты, если база пуста
    async with async_session() as session:
        await session.commit()
        print("База данных проверена и обновлена")

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    config = load_config()

    bot = Bot(token=config.tg_bot.token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.update.middleware(DatabaseMiddleware(session_pool=async_session))
    
    # Регистрация роутеров
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(calc_router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await on_startup(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot stopped!")
