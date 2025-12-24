from aiogram import Router, types, F
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models import User, Recipe, Order
from bot.keyboards.inline import get_recipes_keyboard, get_payment_keyboard

user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(message: types.Message, session: AsyncSession):
    # Регистрация пользователя в БД
    stmt = select(User).where(User.tg_id == message.from_user.id)
    user = await session.scalar(stmt)
    
    if not user:
        user = User(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        session.add(user)
        await session.commit()
    
    await message.answer(
        f"Привет, {message.from_user.full_name}! Выбери рецепт из каталога:",
        reply_markup=await get_catalog_kb(message.from_user.id, session)
    )

async def get_catalog_kb(tg_id, session: AsyncSession):
    # Получаем все рецепты
    recipes = await session.scalars(select(Recipe))
    
    # Получаем заказы пользователя
    user_stmt = select(User).where(User.tg_id == tg_id)
    user = await session.scalar(user_stmt)
    
    orders = []
    if user:
        orders_stmt = select(Order).where(Order.user_id == user.id)
        orders = (await session.scalars(orders_stmt)).all()
    
    return get_recipes_keyboard(recipes.all(), orders)

@user_router.callback_query(F.data == "catalog")
async def show_catalog(callback: types.CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(
        "Выбери рецепт из каталога:",
        reply_markup=await get_catalog_kb(callback.from_user.id, session)
    )

@user_router.callback_query(F.data.startswith("recipe_"))
async def show_recipe(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[1])
    
    # Получаем данные рецепта
    recipe = await session.get(Recipe, recipe_id)
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    
    # Проверяем покупку
    order_stmt = select(Order).where(
        Order.user_id == user.id, 
        Order.recipe_id == recipe_id,
        Order.status == 'paid'
    )
    order = await session.scalar(order_stmt)
    
    if order:
        # Рецепт куплен - показываем контент
        await callback.message.edit_text(
            f"📖 {recipe.title}\n\n{recipe.description}\n\n--- КОНТЕНТ ---\n{recipe.content}",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="catalog")]
            ])
        )
    else:
        # Рецепт не куплен - предлагаем оплату
        await callback.message.edit_text(
            f"💰 {recipe.title}\n\n{recipe.description}\n\nЦена: {recipe.price}₽\n\nДля доступа к рецепту необходимо оплатить.",
            reply_markup=get_payment_keyboard(recipe_id)
        )

@user_router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery, session: AsyncSession):
    # Здесь будет логика инициализации платежа
    data = callback.data.split("_")
    method = data[1]
    recipe_id = int(data[2])
    
    await callback.answer("Платежная система инициализируется...", show_alert=True)
    # В реальности тут генерируем ссылку и отправляем пользователю
    # Для теста можно просто "оплатить" по нажатию
    
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    
    # Создаем или обновляем заказ
    new_order = Order(
        user_id=user.id,
        recipe_id=recipe_id,
        status='paid', # Имитируем успешную оплату для теста
        payment_method=method
    )
    session.add(new_order)
    await session.commit()
    
    await callback.message.answer(f"✅ Оплата прошла успешно! Теперь вам доступен рецепт.")
    await show_recipe(callback, session)
