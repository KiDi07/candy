from aiogram import Router, types
from aiogram.filters import CommandStart

user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {message.from_user.full_name}! Я бот, написанный на aiogram 3.x")
