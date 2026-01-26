from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import User

class IsAdminFilter(BaseFilter):
    async def __call__(self, obj: Message | CallbackQuery, session: AsyncSession) -> bool:
        user = await session.scalar(select(User).where(User.tg_id == obj.from_user.id))
        return user.is_admin if user else False

class IsPrivilegedFilter(BaseFilter):
    async def __call__(self, obj: Message | CallbackQuery, session: AsyncSession) -> bool:
        user = await session.scalar(select(User).where(User.tg_id == obj.from_user.id))
        return user.is_privileged if user else False