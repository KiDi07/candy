from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from bot.database.models import User, UserCalculator, CalculatorIngredient
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

calc_router = Router()

class CalculatorStates(StatesGroup):
    title = State()
    ingredient = State()
    target_mass = State()

def get_calc_main_kb(calculators):
    builder = InlineKeyboardBuilder()
    for calc in calculators:
        builder.row(InlineKeyboardButton(text=f"📊 {calc.title}", callback_data=f"calc_view_{calc.id}"))
    builder.row(InlineKeyboardButton(text="➕ Добавить рецепт", callback_data="calc_add"))
    builder.row(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="catalog"))
    return builder.as_markup()

def get_calc_view_kb(calc_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚖️ Пересчитать", callback_data=f"calc_target_{calc_id}"))
    builder.row(
        InlineKeyboardButton(text="🗑", callback_data=f"calc_del_ask_{calc_id}"),
        InlineKeyboardButton(text="⬅️", callback_data="calc_main")
    )
    return builder.as_markup()

def get_calc_delete_confirm_kb(calc_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"calc_del_conf_{calc_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"calc_view_{calc_id}")
    )
    return builder.as_markup()

@calc_router.callback_query(F.data == "calc_main")
async def calc_main(callback: types.CallbackQuery, session: AsyncSession):
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    calculators = (await session.scalars(select(UserCalculator).where(UserCalculator.user_id == user.id))).all()
    await callback.message.edit_text("🧮 Ваши калькуляторы:", reply_markup=get_calc_main_kb(calculators))

@calc_router.callback_query(F.data == "calc_add")
async def calc_add_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalculatorStates.title)
    await callback.message.edit_text("Введите название рецепта для калькулятора:")

@calc_router.message(CalculatorStates.title)
async def calc_add_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text, ingredients=[])
    await state.set_state(CalculatorStates.ingredient)
    await message.answer(
        "Теперь добавляйте ингредиенты в формате:\n"
        "<code>Название количество</code> (например: <code>Мука 500</code>)\n\n"
        "Когда закончите, нажмите кнопку «Завершить»",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="✅ Завершить", callback_data="calc_add_done")).as_markup()
    )

@calc_router.message(CalculatorStates.ingredient)
async def calc_add_ingredient(message: types.Message, state: FSMContext):
    try:
        if " " not in message.text:
            await message.answer("Пожалуйста, используйте формат: <code>Название количество</code>")
            return
        
        name, grams = message.text.rsplit(" ", 1)
        grams = float(grams.replace(",", "."))
        
        data = await state.get_data()
        ingredients = data.get('ingredients', [])
        ingredients.append({"name": name.strip(), "grams": grams})
        await state.update_data(ingredients=ingredients)
        
        current_list = "\n".join([f"• {i['name']}: {i['grams']}г" for i in ingredients])
        await message.answer(
            f"Добавлено!\n\nТекущий список:\n{current_list}\n\nДобавьте следующий или нажмите «Завершить»",
            reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="✅ Завершить", callback_data="calc_add_done")).as_markup()
        )
    except ValueError:
        await message.answer("Количество должно быть числом!")

@calc_router.callback_query(F.data == "calc_add_done")
async def calc_add_finish(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    if not data.get('ingredients'):
        await callback.answer("Добавьте хотя бы один ингредиент!", show_alert=True)
        return
    
    user = await session.scalar(select(User).where(User.tg_id == callback.from_user.id))
    new_calc = UserCalculator(user_id=user.id, title=data['title'])
    session.add(new_calc)
    await session.flush()
    
    for ing in data['ingredients']:
        session.add(CalculatorIngredient(calculator_id=new_calc.id, name=ing['name'], grams=ing['grams']))
    
    await session.commit()
    await state.clear()
    await callback.answer("Рецепт сохранен!")
    await calc_main(callback, session)

@calc_router.callback_query(F.data.startswith("calc_view_"))
async def calc_view(callback: types.CallbackQuery, session: AsyncSession):
    calc_id = int(callback.data.split("_")[2])
    calc = await session.scalar(select(UserCalculator).where(UserCalculator.id == calc_id).options(selectinload(UserCalculator.ingredients)))
    
    total = sum(i.grams for i in calc.ingredients)
    text = f"📊 <b>{calc.title}</b>\n\n"
    text += "\n".join([f"{i.name}: {i.grams}г" for i in calc.ingredients])
    text += f"\n\n<b>Общая масса: {total}г</b>"
    
    await callback.message.edit_text(text, reply_markup=get_calc_view_kb(calc_id))

@calc_router.callback_query(F.data.startswith("calc_target_"))
async def calc_target_start(callback: types.CallbackQuery, state: FSMContext):
    calc_id = int(callback.data.split("_")[2])
    await state.update_data(calc_id=calc_id)
    await state.set_state(CalculatorStates.target_mass)
    await callback.message.edit_text("Введите желаемую общую массу блюда (в граммах):")

@calc_router.message(CalculatorStates.target_mass)
async def calc_recalculate(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        target_total = float(message.text.replace(",", "."))
        data = await state.get_data()
        calc_id = data['calc_id']
        
        calc = await session.scalar(select(UserCalculator).where(UserCalculator.id == calc_id).options(selectinload(UserCalculator.ingredients)))
        base_total = sum(i.grams for i in calc.ingredients)
        
        if base_total == 0:
            await message.answer("Ошибка: базовая масса равна 0")
            return
            
        ratio = target_total / base_total
        
        text = f"📊 <b>{calc.title}</b> (Пересчет на {target_total}г)\n\n"
        for i in calc.ingredients:
            new_grams = round(i.grams * ratio, 2)
            text += f"{i.name}: {new_grams}г\n"
        
        text += f"\n<b>Итого: {target_total}г</b>"
        
        await message.answer(text, reply_markup=get_calc_view_kb(calc_id))
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число!")

@calc_router.callback_query(F.data.startswith("calc_del_ask_"))
async def calc_delete_ask(callback: types.CallbackQuery, session: AsyncSession):
    calc_id = int(callback.data.split("_")[3])
    calc = await session.get(UserCalculator, calc_id)
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить калькулятор «{calc.title}»?",
        reply_markup=get_calc_delete_confirm_kb(calc_id)
    )

@calc_router.callback_query(F.data.startswith("calc_del_conf_"))
async def calc_delete_conf(callback: types.CallbackQuery, session: AsyncSession):
    calc_id = int(callback.data.split("_")[3])
    await session.execute(delete(UserCalculator).where(UserCalculator.id == calc_id))
    await session.commit()
    await callback.answer("Удалено")
    await calc_main(callback, session)
