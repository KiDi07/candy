import asyncio
import logging

from aiogram import Bot, Dispatcher
from bot.config.config import load_config
from bot.handlers.user import user_router
from bot.database.models import async_main, async_session, Recipe
from bot.middlewares.db import DatabaseMiddleware
from sqlalchemy import select

async def on_startup():
    # Создаем таблицы если их нет
    await async_main()
    
    # Добавим тестовый рецепт, если база пуста
    async with async_session() as session:
        result = await session.execute(select(Recipe))
        if not result.scalars().first():
            test_recipe = Recipe(
                title="Шоколадный торт",
                description="Самый вкусный торт в мире!",
                price=500.0,
                content="Рецепт торта: 1. Купите шоколад... 2. Смешайте..."
            )
            session.add(test_recipe)
            await session.commit()
            print("Тестовый рецепт добавлен в базу")

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting bot")

    # Загрузка конфига
    config = load_config()

    # Инициализация бота и диспетчера
    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher()

    # Мидлварь для базы данных
    dp.update.middleware(DatabaseMiddleware(session_pool=async_session))

    # Регистрация роутеров
    dp.include_router(user_router)

    # Запуск действий при старте
    await on_startup()

    # Пропуск накопившихся апдейтов и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot stopped!")
