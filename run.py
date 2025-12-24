import asyncio
import logging

from aiogram import Bot, Dispatcher
from bot.config.config import load_config
from bot.handlers.user import user_router

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

    # Регистрация роутеров
    dp.include_router(user_router)

    # Пропуск накопившихся апдейтов и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot stopped!")
