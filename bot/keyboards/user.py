import logging
import uuid
import asyncio
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.database.models import User, Recipe, Order, RecipeContent, FreeRecipe
from bot.keyboards.inline import (
    get_recipes_keyboard, get_payment_keyboard, 
    get_recipe_sections_kb, get_main_menu_kb
)
from bot.config.config import load_config
from yookassa import Payment, Configuration

user_router = Router()
config = load_config()

# Явная настройка через класс Configuration
logging.info(f"Configuring YooKassa with Shop ID: {config.yookassa.shop_id}")
if config.yookassa.secret_key:
    logging.info(f"YooKassa Secret Key starts with: {config.yookassa.secret_key[:5]}...")
Configuration.configure(config.yookassa.shop_id, config.yookassa.secret_key)

@user_router.message(Command("menu"))
@user_router.message(CommandStart())
async def cmd_start(message: types.Message, session: AsyncSession):
    # Регистрация пользователя в БД
    stmt = select(User).where(User.tg_id == message.from_user.id)
    user = await session.scalar(stmt)
    
    if not user:
        user = User(tg_id=message.from_user.id, username=message.from_user.username, full_name=message.from_user.full_name)
        session.add(user); await session.commit()
    
    is_admin = user.is_admin
    await message.answer(f"Привет, {message.from_user.full_name}! Выбери категорию:", reply_markup=get_main_menu_kb(is_admin=is_admin))

@user_router.callback_query(F.data == "catalog")
async def show_catalog(callback: types.CallbackQuery, session: AsyncSession):
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    is_admin = user.is_admin if user else False
    await callback.message.edit_text("Выбери категорию:", reply_markup=get_main_menu_kb(is_admin=is_admin))

@user_router.callback_query(F.data == "category_free")
async def show_free_recipes(callback: types.CallbackQuery, session: AsyncSession):
    recipes = await session.scalars(select(FreeRecipe))
    await callback.message.edit_text("🎁 Бесплатные рецепты:", reply_markup=get_recipes_keyboard(recipes.all(), is_free=True))

@user_router.callback_query(F.data == "category_paid")
async def show_paid_recipes(callback: types.CallbackQuery, session: AsyncSession):
    recipes = await session.scalars(select(Recipe))
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    orders = []
    is_admin = False
    is_privileged = False
    if user:
        orders = (await session.scalars(select(Order).where(Order.user_id == user.id))).all()
        is_admin = user.is_admin
        is_privileged = user.is_privileged
    
    await callback.message.edit_text("💎 Платные рецепты:", reply_markup=get_recipes_keyboard(recipes.all(), user_orders=orders, is_free=False, is_admin=is_admin, is_privileged=is_privileged))

@user_router.callback_query(F.data.regexp(r"^recipe_\d+$"))
async def show_recipe(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[1])
    stmt = select(Recipe).where(Recipe.id == recipe_id).options(selectinload(Recipe.content))
    recipe = await session.scalar(stmt)
    
    if not recipe: await callback.answer("Рецепт не найден"); return

    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    is_admin = user.is_admin if user else False
    is_privileged = user.is_privileged if user else False
    order = None
    if user:
        order = await session.scalar(select(Order).where(Order.user_id == user.id, Order.recipe_id == recipe_id, Order.status == 'paid'))
    
    if order or is_admin or is_privileged:
        recipe_text = recipe.content.recipe_text if recipe.content else "Текст рецепта скоро появится"
        recipe_text = recipe_text.replace("<hr>", "---")
        try: await callback.message.edit_text(recipe_text, reply_markup=get_recipe_sections_kb(recipe_id))
        except: await callback.message.edit_text(recipe_text, reply_markup=get_recipe_sections_kb(recipe_id))
    else:
        await callback.message.edit_text(f"💰 {recipe.title}\n\n{recipe.description}\n\nЦена: {recipe.price}₽", reply_markup=get_payment_keyboard(recipe_id))

@user_router.callback_query(F.data.startswith("recipe_text_"))
async def show_recipe_text(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    content = await session.scalar(select(RecipeContent).where(RecipeContent.recipe_id == recipe_id))
    text = content.recipe_text if content else "Текст рецепта скоро появится"
    try: await callback.message.edit_text(text, reply_markup=get_recipe_sections_kb(recipe_id))
    except: await callback.message.edit_text(text, reply_markup=get_recipe_sections_kb(recipe_id))
    await callback.answer()

@user_router.callback_query(F.data.startswith("recipe_video_"))
async def show_recipe_video(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    content = await session.scalar(select(RecipeContent).where(RecipeContent.recipe_id == recipe_id))
    video_url = content.video_url if content else "Видео скоро появится"
    try: await callback.message.edit_text(f"🎥 <b>Видео:</b>\n\n{video_url}", reply_markup=get_recipe_sections_kb(recipe_id))
    except: await callback.message.edit_text(f"🎥 Видео:\n\n{video_url}", reply_markup=get_recipe_sections_kb(recipe_id))
    await callback.answer()

@user_router.callback_query(F.data.startswith("recipe_ingredients_"))
async def show_recipe_ingredients(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    content = await session.scalar(select(RecipeContent).where(RecipeContent.recipe_id == recipe_id))
    text = content.ingredients if content else "Ингредиенты скоро появятся"
    try: await callback.message.edit_text(text, reply_markup=get_recipe_sections_kb(recipe_id))
    except: await callback.message.edit_text(text, reply_markup=get_recipe_sections_kb(recipe_id))
    await callback.answer()

@user_router.callback_query(F.data.startswith("recipe_inventory_"))
async def show_recipe_inventory(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    content = await session.scalar(select(RecipeContent).where(RecipeContent.recipe_id == recipe_id))
    text = content.inventory if content else "Инвентарь скоро появится"
    try: await callback.message.edit_text(text, reply_markup=get_recipe_sections_kb(recipe_id))
    except: await callback.message.edit_text(text, reply_markup=get_recipe_sections_kb(recipe_id))
    await callback.answer()

@user_router.callback_query(F.data.startswith("recipe_shops_"))
async def show_recipe_shops(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    content = await session.scalar(select(RecipeContent).where(RecipeContent.recipe_id == recipe_id))
    text = content.shops if content else "Ссылки скоро появятся"
    try: await callback.message.edit_text(text, reply_markup=get_recipe_sections_kb(recipe_id))
    except: await callback.message.edit_text(text, reply_markup=get_recipe_sections_kb(recipe_id))
    await callback.answer()

@user_router.callback_query(F.data.startswith("pay_ukassa_"))
async def process_payment(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    recipe = await session.get(Recipe, recipe_id)
    if not recipe: await callback.answer("Не найден"); return
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    if not user: await callback.answer("Попробуйте /start", show_alert=True); return

    try:
        payment = Payment.create({"amount": {"value": f"{recipe.price:.2f}", "currency": "RUB"}, "confirmation": {"type": "redirect", "return_url": "https://t.me/agcandybot"}, "capture": True, "description": f"Рецепт: {recipe.title}"}, str(uuid.uuid4()))
        new_order = Order(user_id=user.id, recipe_id=recipe_id, status='pending', payment_id=payment.id, payment_method='ukassa')
        session.add(new_order); await session.commit()
        await callback.message.edit_text(f"💰 {recipe.title}\n\nК оплате: {recipe.price}₽", reply_markup=get_payment_keyboard(recipe_id, payment_url=payment.confirmation.confirmation_url))
    except Exception as e:
        logging.error(e); await callback.answer("Ошибка ЮKassa", show_alert=True)

@user_router.callback_query(F.data.startswith("check_pay_"))
async def check_payment(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[2])
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    order = await session.scalar(select(Order).where(Order.user_id == user.id, Order.recipe_id == recipe_id, Order.status == 'pending').order_by(Order.id.desc()))
    if not order: await callback.answer("Заказ не найден", show_alert=True); return
    
    await asyncio.sleep(1)
    try:
        payment = Payment.find_one(order.payment_id)
        if payment.status == 'succeeded':
            order.status = 'paid'; await session.commit(); await callback.answer("✅ Оплачено!", show_alert=True); await show_recipe(callback, session)
        else: await callback.answer(f"Статус: {payment.status}", show_alert=True)
    except: await callback.answer("Ошибка проверки", show_alert=True)
