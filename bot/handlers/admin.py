import html
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from bot.database.models import Recipe, RecipeContent
from bot.keyboards.admin_kb import (
    get_admin_main_kb, get_admin_recipes_kb, 
    get_recipe_edit_kb, get_cancel_kb
)
from bot.config.config import load_config

admin_router = Router()
config = load_config()

class AdminAuth(StatesGroup):
    # Просто для фильтрации, если захотим пароль, но пока по ID
    pass

class AddRecipe(StatesGroup):
    title = State()
    description = State()
    price = State()
    recipe_text = State()
    video_url = State()
    ingredients = State()
    inventory = State()
    shops = State()

class EditRecipe(StatesGroup):
    field_value = State()

# Фильтр для админов
def is_admin(message: types.Message):
    return message.from_user.id in config.tg_bot.admin_ids

@admin_router.message(Command("admin"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_start(message: types.Message):
    await message.answer("👋 Добро пожаловать в админ-панель!", reply_markup=get_admin_main_kb())

@admin_router.callback_query(F.data == "admin_main", F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_main_cb(callback: types.CallbackQuery):
    await callback.message.edit_text("👋 Добро пожаловать в админ-панель!", reply_markup=get_admin_main_kb())

@admin_router.callback_query(F.data == "admin_recipes_list", F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_recipes_list(callback: types.CallbackQuery, session: AsyncSession):
    recipes = await session.scalars(select(Recipe))
    await callback.message.edit_text("📜 Список всех рецептов:", reply_markup=get_admin_recipes_kb(recipes.all()))

@admin_router.callback_query(F.data.startswith("admin_recipe_view_"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_recipe_view(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[3])
    stmt = select(Recipe).where(Recipe.id == recipe_id).options(selectinload(Recipe.content))
    recipe = await session.scalar(stmt)
    
    text = (
        f"<b>Рецепт:</b> {recipe.title}\n"
        f"<b>Цена:</b> {recipe.price}₽\n"
        f"<b>Описание:</b> {recipe.description[:100]}...\n\n"
        f"Выберите поле для редактирования:"
    )
    await callback.message.edit_text(text, reply_markup=get_recipe_edit_kb(recipe_id), parse_mode="HTML")

# --- ДОБАВЛЕНИЕ РЕЦЕПТА ---

@admin_router.callback_query(F.data == "admin_recipe_add", F.from_user.id.in_(config.tg_bot.admin_ids))
async def add_recipe_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddRecipe.title)
    await callback.message.edit_text("Введите название рецепта:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.title)
async def add_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddRecipe.description)
    await message.answer("Введите описание рецепта (короткое):", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.description)
async def add_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddRecipe.price)
    await message.answer("Введите цену (число):", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.price)
async def add_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await state.set_state(AddRecipe.recipe_text)
        await message.answer("Введите основной текст рецепта (HTML поддерживается):", reply_markup=get_cancel_kb())
    except ValueError:
        await message.answer("Пожалуйста, введите число.")

@admin_router.message(AddRecipe.recipe_text)
async def add_recipe_text(message: types.Message, state: FSMContext):
    await state.update_data(recipe_text=message.text)
    await state.set_state(AddRecipe.video_url)
    await message.answer("Введите ссылку на видео или описание видео-раздела:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.video_url)
async def add_video_url(message: types.Message, state: FSMContext):
    await state.update_data(video_url=message.text)
    await state.set_state(AddRecipe.ingredients)
    await message.answer("Введите текст раздела 'Ингредиенты':", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.ingredients)
async def add_ingredients(message: types.Message, state: FSMContext):
    await state.update_data(ingredients=message.text)
    await state.set_state(AddRecipe.inventory)
    await message.answer("Введите текст раздела 'Инвентарь':", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.inventory)
async def add_inventory(message: types.Message, state: FSMContext):
    await state.update_data(inventory=message.text)
    await state.set_state(AddRecipe.shops)
    await message.answer("Введите текст раздела 'Ссылки на магазины':", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.shops)
async def add_shops(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    
    new_recipe = Recipe(
        title=data['title'],
        description=data['description'],
        price=data['price']
    )
    session.add(new_recipe)
    await session.flush()
    
    new_content = RecipeContent(
        recipe_id=new_recipe.id,
        recipe_text=data['recipe_text'],
        video_url=data['video_url'],
        ingredients=data['ingredients'],
        inventory=data['inventory'],
        shops=message.text
    )
    session.add(new_content)
    await session.commit()
    
    await state.clear()
    await message.answer("✅ Рецепт успешно добавлен!", reply_markup=get_admin_main_kb())

# --- РЕДАКТИРОВАНИЕ ПОЛЯ ---

@admin_router.callback_query(F.data.startswith("edit_field_"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def edit_field_start(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Разбор данных вида "edit_field_{name}_{id}"
    data = callback.data.replace("edit_field_", "")
    parts = data.rsplit("_", 1)
    
    field = parts[0]
    recipe_id = int(parts[1])
        
    await state.update_data(edit_recipe_id=recipe_id, edit_field=field)
    await state.set_state(EditRecipe.field_value)
    
    fields_map = {
        "title": "название",
        "price": "цену",
        "description": "описание",
        "recipe_text": "текст рецепта",
        "video_url": "ссылку на видео",
        "ingredients": "ингредиенты",
        "inventory": "инвентарь",
        "shops": "ссылки"
    }

    # Получаем текущее значение
    current_value = ""
    if field in ["title", "description", "price"]:
        recipe = await session.get(Recipe, recipe_id)
        current_value = str(getattr(recipe, field, ""))
    else:
        stmt = select(RecipeContent).where(RecipeContent.recipe_id == recipe_id)
        content = await session.scalar(stmt)
        current_value = str(getattr(content, field, "")) if content else ""

    # Экранируем HTML и ограничиваем длину вывода, чтобы не сломать Telegram
    safe_value = html.escape(current_value)
    preview = safe_value if len(safe_value) < 1000 else safe_value[:1000] + "..."
    
    text = (
        f"📝 Редактирование поля: <b>{fields_map.get(field)}</b>\n\n"
        f"<b>Текущее значение:</b>\n{preview or '<i>(пусто)</i>'}\n\n"
        f"Введите новое значение:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_cancel_kb(), parse_mode="HTML")

@admin_router.message(EditRecipe.field_value)
async def edit_field_save(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    recipe_id = data['edit_recipe_id']
    field = data['edit_field']
    
    if field in ["title", "description", "price"]:
        recipe = await session.get(Recipe, recipe_id)
        if field == "price":
            try:
                setattr(recipe, field, float(message.text))
            except ValueError:
                await message.answer("Введите число.")
                return
        else:
            setattr(recipe, field, message.text)
    else:
        stmt = select(RecipeContent).where(RecipeContent.recipe_id == recipe_id)
        content = await session.scalar(stmt)
        if not content:
            content = RecipeContent(recipe_id=recipe_id)
            session.add(content)
        setattr(content, field, message.text)
    
    await session.commit()
    await state.clear()
    await message.answer("✅ Изменения сохранены!", reply_markup=get_admin_main_kb())

# --- УДАЛЕНИЕ ---

@admin_router.callback_query(F.data.startswith("admin_recipe_delete_"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def delete_recipe(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[3])
    # Каскадное удаление контента настроено в моделях (delete-orphan)
    await session.execute(delete(Recipe).where(Recipe.id == recipe_id))
    await session.commit()
    await callback.answer("Рецепт удален", show_alert=True)
    await admin_recipes_list(callback, session)

# --- ОТМЕНА ---

@admin_router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.", reply_markup=get_admin_main_kb())
