from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def get_recipes_keyboard(recipes, user_orders=None, is_free=False, is_admin=False):
    builder = InlineKeyboardBuilder()
    
    # Создаем сет из ID купленных рецептов для быстрой проверки
    paid_recipe_ids = set()
    if user_orders:
        paid_recipe_ids = {order.recipe_id for order in user_orders if order.status == 'paid'}
    
    for recipe in recipes:
        if is_free:
            # Для бесплатных рецептов кнопка - это прямая ссылка на пост
            builder.row(InlineKeyboardButton(
                text=f"{recipe.title}",
                url=recipe.external_link if recipe.external_link else "https://t.me"
            ))
        else:
            # Платные рецепты
            if is_admin or recipe.id in paid_recipe_ids:
                text = f"✅ {recipe.title}"
            else:
                text = f"💰 {recipe.title} ({recipe.price}₽)"
            
            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=f"recipe_{recipe.id}")
            )
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog"))
    return builder.as_markup()

def get_payment_keyboard(recipe_id, payment_url=None):
    builder = InlineKeyboardBuilder()
    if payment_url:
        builder.row(InlineKeyboardButton(text="💳 Оплатить", url=payment_url))
        builder.row(InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_pay_{recipe_id}"))
    else:
        builder.row(InlineKeyboardButton(text="💳 Перейти к оплате", callback_data=f"pay_ukassa_{recipe_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="category_paid"))
    return builder.as_markup()

def get_recipe_sections_kb(recipe_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📖 Рецепт", callback_data=f"recipe_text_{recipe_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🎥 Видео", callback_data=f"recipe_video_{recipe_id}"),
        InlineKeyboardButton(text="🛒 Ингредиенты", callback_data=f"recipe_ingredients_{recipe_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Магазины", callback_data=f"recipe_shops_{recipe_id}"),
        InlineKeyboardButton(text="🛠 Инвентарь", callback_data=f"recipe_inventory_{recipe_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 К списку", callback_data="category_paid")
    )
    return builder.as_markup()

def get_main_menu_kb(is_admin=False):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Бесплатные рецепты", callback_data="category_free"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Платные рецепты", callback_data="category_paid")
    )
    
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚙️ Панель администратора", callback_data="admin_main")
        )
        
    return builder.as_markup()
