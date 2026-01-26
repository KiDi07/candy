import html
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from bot.database.models import Recipe, RecipeContent, FreeRecipe
from bot.keyboards.admin_kb import (
    get_admin_main_kb, get_admin_recipes_kb, 
    get_recipe_edit_kb, get_cancel_kb,
    get_delete_confirm_kb, get_recipe_type_kb
)
from bot.config.config import load_config

admin_router = Router()
config = load_config()

class AddRecipe(StatesGroup):
    type = State()
    title = State()
    description = State()
    price = State()
    external_link = State()
    recipe_text = State()
    video_url = State()
    ingredients = State()
    inventory = State()
    shops = State()

class EditRecipe(StatesGroup):
    field_value = State()

@admin_router.message(Command("admin"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_start(message: types.Message):
    await message.answer("👋 Добро пожаловать в админ-панель!", reply_markup=get_admin_main_kb())

@admin_router.callback_query(F.data == "admin_main", F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_main_cb(callback: types.CallbackQuery):
    await callback.message.edit_text("👋 Добро пожаловать в админ-панель!", reply_markup=get_admin_main_kb())

@admin_router.callback_query(F.data == "admin_recipes_list_paid", F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_recipes_list_paid(callback: types.CallbackQuery, session: AsyncSession):
    recipes = await session.scalars(select(Recipe))
    await callback.message.edit_text("📜 Список платных рецептов:", reply_markup=get_admin_recipes_kb(recipes.all(), is_free=False))

@admin_router.callback_query(F.data == "admin_recipes_list_free", F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_recipes_list_free(callback: types.CallbackQuery, session: AsyncSession):
    recipes = await session.scalars(select(FreeRecipe))
    await callback.message.edit_text("🎁 Список бесплатных рецептов:", reply_markup=get_admin_recipes_kb(recipes.all(), is_free=True))

@admin_router.callback_query(F.data.startswith("admin_recipe_view_paid_"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_recipe_view_paid(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[4])
    stmt = select(Recipe).where(Recipe.id == recipe_id).options(selectinload(Recipe.content))
    recipe = await session.scalar(stmt)
    text = (f"<b>Платный:</b> {recipe.title}\n<b>Цена:</b> {recipe.price}₽\n<b>Описание:</b> {recipe.description[:100]}...\n\nВыбор поля:")
    await callback.message.edit_text(text, reply_markup=get_recipe_edit_kb(recipe_id, is_free=False))

@admin_router.callback_query(F.data.startswith("admin_recipe_view_free_"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def admin_recipe_view_free(callback: types.CallbackQuery, session: AsyncSession):
    recipe_id = int(callback.data.split("_")[4])
    recipe = await session.get(FreeRecipe, recipe_id)
    text = (f"<b>Бесплатный:</b> {recipe.title}\n<b>Ссылка:</b> {recipe.external_link}\n\nВыбор поля:")
    await callback.message.edit_text(text, reply_markup=get_recipe_edit_kb(recipe_id, is_free=True))

@admin_router.callback_query(F.data == "admin_recipe_add", F.from_user.id.in_(config.tg_bot.admin_ids))
async def add_recipe_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddRecipe.type); await callback.message.edit_text("Тип рецепта:", reply_markup=get_recipe_type_kb())

@admin_router.callback_query(AddRecipe.type, F.data.startswith("type_"))
async def add_recipe_type(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(type=callback.data); await state.set_state(AddRecipe.title)
    await callback.message.edit_text("Название:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.title)
async def add_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text); data = await state.get_data()
    if data['type'] == 'type_free':
        await state.set_state(AddRecipe.external_link); await message.answer("Ссылка на пост:", reply_markup=get_cancel_kb())
    else:
        await state.set_state(AddRecipe.description); await message.answer("Описание:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.external_link)
async def add_external_link(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    session.add(FreeRecipe(title=data['title'], external_link=message.text))
    await session.commit(); await state.clear(); await message.answer("✅ Добавлено!", reply_markup=get_admin_main_kb())

@admin_router.message(AddRecipe.description)
async def add_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text); await state.set_state(AddRecipe.price)
    await message.answer("Цена:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.price)
async def add_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text); await state.update_data(price=price); await state.set_state(AddRecipe.recipe_text)
        await message.answer("Текст рецепта (HTML):", reply_markup=get_cancel_kb())
    except: await message.answer("Введите число.")

@admin_router.message(AddRecipe.recipe_text)
async def add_recipe_text(message: types.Message, state: FSMContext):
    await state.update_data(recipe_text=message.text); await state.set_state(AddRecipe.video_url)
    await message.answer("Видео URL:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.video_url)
async def add_video_url(message: types.Message, state: FSMContext):
    await state.update_data(video_url=message.text); await state.set_state(AddRecipe.ingredients)
    await message.answer("Ингредиенты:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.ingredients)
async def add_ingredients(message: types.Message, state: FSMContext):
    await state.update_data(ingredients=message.text); await state.set_state(AddRecipe.inventory)
    await message.answer("Инвентарь:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.inventory)
async def add_inventory(message: types.Message, state: FSMContext):
    await state.update_data(inventory=message.text); await state.set_state(AddRecipe.shops)
    await message.answer("Ссылки на магазины:", reply_markup=get_cancel_kb())

@admin_router.message(AddRecipe.shops)
async def add_shops(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    new_r = Recipe(title=data['title'], description=data['description'], price=data['price'])
    session.add(new_r); await session.flush()
    session.add(RecipeContent(recipe_id=new_r.id, recipe_text=data['recipe_text'], video_url=data['video_url'], ingredients=data['ingredients'], inventory=data['inventory'], shops=message.text))
    await session.commit(); await state.clear(); await message.answer("✅ Добавлено!", reply_markup=get_admin_main_kb())

@admin_router.callback_query(F.data.startswith("edit_paid_"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def edit_paid(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = callback.data.replace("edit_paid_", "").rsplit("_", 1)
    await state.update_data(edit_recipe_id=int(data[1]), edit_field=data[0], edit_type='paid')
    await state.set_state(EditRecipe.field_value); await callback.message.edit_text("Введите новое значение:", reply_markup=get_cancel_kb())

@admin_router.callback_query(F.data.startswith("edit_free_"), F.from_user.id.in_(config.tg_bot.admin_ids))
async def edit_free(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = callback.data.replace("edit_free_", "").rsplit("_", 1)
    await state.update_data(edit_recipe_id=int(data[1]), edit_field=data[0], edit_type='free')
    await state.set_state(EditRecipe.field_value); await callback.message.edit_text("Введите новое значение:", reply_markup=get_cancel_kb())

@admin_router.message(EditRecipe.field_value)
async def edit_save(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data(); r_id = data['edit_recipe_id']; field = data['edit_field']
    if data['edit_type'] == 'paid':
        if field in ["title", "description", "price"]:
            r = await session.get(Recipe, r_id)
            if field == "price":
                try: r.price = float(message.text)
                except: await message.answer("Число!"); return
            else: setattr(r, field, message.text)
        else:
            c = await session.scalar(select(RecipeContent).where(RecipeContent.recipe_id == r_id))
            if not c: c = RecipeContent(recipe_id=r_id); session.add(c)
            setattr(c, field, message.text)
    else:
        r = await session.get(FreeRecipe, r_id); setattr(r, field, message.text)
    await session.commit(); await state.clear(); await message.answer("✅ Сохранено!", reply_markup=get_admin_main_kb())

@admin_router.callback_query(F.data.startswith("admin_recipe_delete_paid_"))
async def del_paid_ask(c: types.CallbackQuery, session: AsyncSession):
    r_id = int(c.data.split("_")[4]); r = await session.get(Recipe, r_id)
    await c.message.edit_text(f"Удалить {r.title}?", reply_markup=get_delete_confirm_kb(r_id, False))

@admin_router.callback_query(F.data.startswith("admin_recipe_delete_free_"))
async def del_free_ask(c: types.CallbackQuery, session: AsyncSession):
    r_id = int(c.data.split("_")[4]); r = await session.get(FreeRecipe, r_id)
    await c.message.edit_text(f"Удалить {r.title}?", reply_markup=get_delete_confirm_kb(r_id, True))

@admin_router.callback_query(F.data.startswith("admin_recipe_confirm_delete_paid_"))
async def del_paid_conf(c: types.CallbackQuery, session: AsyncSession):
    await session.execute(delete(Recipe).where(Recipe.id == int(c.data.split("_")[5])))
    await session.commit(); await c.answer("Удалено"); await admin_recipes_list_paid(c, session)

@admin_router.callback_query(F.data.startswith("admin_recipe_confirm_delete_free_"))
async def del_free_conf(c: types.CallbackQuery, session: AsyncSession):
    await session.execute(delete(FreeRecipe).where(FreeRecipe.id == int(c.data.split("_")[5])))
    await session.commit(); await c.answer("Удалено"); await admin_recipes_list_free(c, session)

@admin_router.callback_query(F.data == "admin_cancel")
async def cancel(c: types.CallbackQuery, state: FSMContext):
    await state.clear(); await c.message.edit_text("Отменено", reply_markup=get_admin_main_kb())
