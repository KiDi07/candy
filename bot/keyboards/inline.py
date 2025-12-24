from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def get_recipes_keyboard(recipes, user_orders):
    builder = InlineKeyboardBuilder()
    
    # Создаем сет из ID купленных рецептов для быстрой проверки
    paid_recipe_ids = {order.recipe_id for order in user_orders if order.status == 'paid'}
    
    for recipe in recipes:
        if recipe.id in paid_recipe_ids:
            text = f"✅ {recipe.title}"
        else:
            text = f"💰 {recipe.title} ({recipe.price}₽)"
        
        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"recipe_{recipe.id}")
        )
    
    return builder.as_markup()

def get_payment_keyboard(recipe_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 ЮKassa", callback_data=f"pay_ukassa_{recipe_id}"))
    builder.row(InlineKeyboardButton(text="💎 Крипта", callback_data=f"pay_crypto_{recipe_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog"))
    return builder.as_markup()
