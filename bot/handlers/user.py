import logging
import uuid
import requests
import json
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.database.models import User, Recipe, Order, RecipeContent
from bot.keyboards.inline import get_recipes_keyboard, get_payment_keyboard, get_recipe_sections_kb
from bot.utils import texts
from bot.config.config import load_config
from yookassa import Payment, Configuration

user_router = Router()
config = load_config()

# Явная настройка через класс Configuration
Configuration.configure(config.yookassa.shop_id, config.yookassa.secret_key)

@user_router.message(Command("test_menu"))
async def cmd_test_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Бисквит «Красный бархат»", callback_data="recipe_1"))
    await message.answer(
        "🛠 Тестовое меню рецептов:",
        reply_markup=builder.as_markup()
    )

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
    
    is_admin = tg_id in config.tg_bot.admin_ids
    return get_recipes_keyboard(recipes.all(), orders, is_admin=is_admin)

@user_router.callback_query(F.data == "catalog")
async def show_catalog(callback: types.CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(
        "Выбери рецепт из каталога:",
        reply_markup=await get_catalog_kb(callback.from_user.id, session)
    )

@user_router.callback_query(F.data.regexp(r"^recipe_\d+$"))
async def show_recipe(callback: types.CallbackQuery, session: AsyncSession):
    try:
        recipe_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка в ID рецепта")
        return

    # Получаем данные рецепта с контентом
    stmt = select(Recipe).where(Recipe.id == recipe_id).options(selectinload(Recipe.content))
    recipe = await session.scalar(stmt)
    
    if not recipe:
        await callback.answer("Рецепт не найден")
        return

    # Проверяем покупку
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    is_admin = callback.from_user.id in config.tg_bot.admin_ids
    
    order = None
    if user:
        order_stmt = select(Order).where(
            Order.user_id == user.id, 
            Order.recipe_id == recipe_id,
            Order.status == 'paid'
        )
        order = await session.scalar(order_stmt)
    
    # Если куплено или пользователь - админ
    if order or is_admin:
        # Рецепт куплен - показываем сразу текст рецепта и меню разделов
        recipe_text = recipe.content.recipe_text if recipe.content else "Текст рецепта скоро появится"
        try:
            await callback.message.edit_text(
                recipe_text,
                reply_markup=get_recipe_sections_kb(recipe_id),
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            await callback.message.edit_text(
                recipe_text,
                reply_markup=get_recipe_sections_kb(recipe_id),
                parse_mode=None
            )
    else:
        # Рецепт не куплен - предлагаем оплату
        await callback.message.edit_text(
            f"💰 {recipe.title}\n\n{recipe.description}\n\nЦена: {recipe.price}₽\n\nДля доступа к рецепту необходимо оплатить.",
            reply_markup=get_payment_keyboard(recipe_id)
        )

@user_router.callback_query(F.data.startswith("recipe_text_"))
async def show_recipe_text(callback: types.CallbackQuery, session: AsyncSession, **kwargs):
    recipe_id = int(callback.data.split("_")[2])
    stmt = select(RecipeContent).where(RecipeContent.recipe_id == recipe_id)
    content = await session.scalar(stmt)
    
    text = content.recipe_text if content else "Текст рецепта скоро появится"
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.message.edit_text(
            text,
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode=None
        )
    await callback.answer()

@user_router.callback_query(F.data.startswith("recipe_video_"))
async def show_recipe_video(callback: types.CallbackQuery, session: AsyncSession, **kwargs):
    recipe_id = int(callback.data.split("_")[2])
    stmt = select(RecipeContent).where(RecipeContent.recipe_id == recipe_id)
    content = await session.scalar(stmt)
    
    video_url = content.video_url if content else "Видео скоро появится"
    try:
        await callback.message.edit_text(
            f"🎥 <b>Видеоурок:</b>\n\n{video_url}",
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.message.edit_text(
            f"🎥 Видеоурок:\n\n{video_url}",
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode=None
        )
    await callback.answer()

@user_router.callback_query(F.data.startswith("recipe_ingredients_"))
async def show_recipe_ingredients(callback: types.CallbackQuery, session: AsyncSession, **kwargs):
    recipe_id = int(callback.data.split("_")[2])
    stmt = select(RecipeContent).where(RecipeContent.recipe_id == recipe_id)
    content = await session.scalar(stmt)
    
    ingredients = content.ingredients if content else "Список ингредиентов скоро появится"
    try:
        await callback.message.edit_text(
            ingredients,
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.message.edit_text(
            ingredients,
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode=None
        )
    await callback.answer()

@user_router.callback_query(F.data.startswith("recipe_inventory_"))
async def show_recipe_inventory(callback: types.CallbackQuery, session: AsyncSession, **kwargs):
    recipe_id = int(callback.data.split("_")[2])
    stmt = select(RecipeContent).where(RecipeContent.recipe_id == recipe_id)
    content = await session.scalar(stmt)
    
    inventory = content.inventory if content else "Информация об инвентаре скоро появится"
    try:
        await callback.message.edit_text(
            inventory,
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.message.edit_text(
            inventory,
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode=None
        )
    await callback.answer()

@user_router.callback_query(F.data.startswith("recipe_shops_"))
async def show_recipe_shops(callback: types.CallbackQuery, session: AsyncSession, **kwargs):
    recipe_id = int(callback.data.split("_")[2])
    stmt = select(RecipeContent).where(RecipeContent.recipe_id == recipe_id)
    content = await session.scalar(stmt)
    
    shops = content.shops if content else "Ссылки скоро появятся"
    try:
        await callback.message.edit_text(
            shops,
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.message.edit_text(
            shops,
            reply_markup=get_recipe_sections_kb(recipe_id),
            parse_mode=None
        )
    await callback.answer()

@user_router.callback_query(F.data.startswith("pay_ukassa_"))
async def process_payment(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    
    stmt = select(Recipe).where(Recipe.id == recipe_id)
    recipe = await session.scalar(stmt)
    
    if not recipe:
        await callback.answer("Рецепт не найден")
        return

    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    
    # Создаем платеж в ЮKassa через прямой запрос (requests) для отладки
    url = "https://api.yookassa.ru/v3/payments"
    idempotency_key = str(uuid.uuid4())
    
    headers = {
        "Idempotence-Key": idempotency_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": {
            "value": f"{recipe.price:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/agcandybot"
        },
        "capture": True,
        "description": f"Оплата рецепта: {recipe.title}"
    }
    
    try:
        response = requests.post(
            url,
            auth=(config.yookassa.shop_id, config.yookassa.secret_key),
            headers=headers,
            data=json.dumps(payload),
            timeout=10
        )
        
        if response.status_code != 200:
            logging.error(f"Yookassa error ({response.status_code}): {response.text}")
            error_msg = response.text[:150]
            await callback.answer(f"Ошибка ЮKassa ({response.status_code}): {error_msg}", show_alert=True)
            return
            
        payment_data = response.json()
        payment_id = payment_data.get("id")
        confirmation_url = payment_data.get("confirmation", {}).get("confirmation_url")

    except Exception as e:
        logging.error(f"Request error: {e}")
        await callback.answer(f"Ошибка сети: {str(e)[:150]}", show_alert=True)
        return

    # Сохраняем информацию о платеже
    new_order = Order(
        user_id=user.id,
        recipe_id=recipe_id,
        status='pending',
        payment_id=payment_id,
        payment_method='ukassa'
    )
    session.add(new_order)
    await session.commit()
    
    await callback.message.edit_text(
        f"💰 Оплата рецепта: <b>{recipe.title}</b>\n\nСумма к оплате: {recipe.price}₽\n\nПосле оплаты нажмите кнопку «Проверить оплату»",
        reply_markup=get_payment_keyboard(recipe_id, payment_url=confirmation_url),
        parse_mode="HTML"
    )

@user_router.callback_query(F.data.startswith("check_pay_"))
async def check_payment(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    
    stmt = select(Order).where(
        Order.user_id == user.id,
        Order.recipe_id == recipe_id,
        Order.status == 'pending'
    ).order_by(Order.id.desc())
    
    order = await session.scalar(stmt)
    
    if not order or not order.payment_id:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    # Проверяем статус в ЮKassa
    payment = Payment.find_one(order.payment_id)
    
    if payment.status == 'succeeded':
        order.status = 'paid'
        await session.commit()
        await callback.answer("✅ Оплата подтверждена!", show_alert=True)
        await show_recipe(callback, session)
    elif payment.status == 'pending':
        await callback.answer("⏳ Оплата еще в обработке. Попробуйте позже.", show_alert=True)
    elif payment.status == 'canceled':
        await callback.answer("❌ Платеж отменен.", show_alert=True)
    else:
        await callback.answer(f"Статус платежа: {payment.status}", show_alert=True)
