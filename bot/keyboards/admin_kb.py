from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def get_admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📜 Платные рецепты", callback_data="admin_recipes_list_paid"))
    builder.row(InlineKeyboardButton(text="🎁 Бесплатные рецепты", callback_data="admin_recipes_list_free"))
    builder.row(InlineKeyboardButton(text="➕ Добавить рецепт", callback_data="admin_recipe_add"))
    builder.row(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_stats_users"))
    return builder.as_markup()

def get_admin_recipes_kb(recipes, is_free=False):
    builder = InlineKeyboardBuilder()
    prefix = "admin_recipe_view_free" if is_free else "admin_recipe_view_paid"
    for recipe in recipes:
        builder.row(InlineKeyboardButton(text=recipe.title, callback_data=f"{prefix}_{recipe.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main"))
    return builder.as_markup()

def get_recipe_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Бесплатный", callback_data="type_free"),
        InlineKeyboardButton(text="💎 Платный", callback_data="type_paid")
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    return builder.as_markup()

def get_recipe_edit_kb(recipe_id, is_free=False):
    builder = InlineKeyboardBuilder()
    prefix = "edit_free" if is_free else "edit_paid"
    
    if is_free:
        builder.row(
            InlineKeyboardButton(text="Название", callback_data=f"{prefix}_title_{recipe_id}"),
            InlineKeyboardButton(text="Ссылка на пост", callback_data=f"{prefix}_external_link_{recipe_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="Название", callback_data=f"{prefix}_title_{recipe_id}"),
            InlineKeyboardButton(text="Описание", callback_data=f"{prefix}_description_{recipe_id}")
        )
        builder.row(InlineKeyboardButton(text="Цена", callback_data=f"{prefix}_price_{recipe_id}"))
        builder.row(
            InlineKeyboardButton(text="Текст рецепта", callback_data=f"{prefix}_recipe_text_{recipe_id}"),
            InlineKeyboardButton(text="Видео (URL)", callback_data=f"{prefix}_video_url_{recipe_id}")
        )
        builder.row(
            InlineKeyboardButton(text="Ингредиенты", callback_data=f"{prefix}_ingredients_{recipe_id}"),
            InlineKeyboardButton(text="Инвентарь", callback_data=f"{prefix}_inventory_{recipe_id}")
        )
        builder.row(InlineKeyboardButton(text="Магазины (ссылки)", callback_data=f"{prefix}_shops_{recipe_id}"))
    
    del_prefix = "admin_recipe_delete_free" if is_free else "admin_recipe_delete_paid"
    back_data = "admin_recipes_list_free" if is_free else "admin_recipes_list_paid"
    
    builder.row(InlineKeyboardButton(text="❌ Удалить рецепт", callback_data=f"{del_prefix}_{recipe_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ К списку", callback_data=back_data))
    return builder.as_markup()

def get_cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    return builder.as_markup()

def get_delete_confirm_kb(recipe_id, is_free=False):
    builder = InlineKeyboardBuilder()
    view_prefix = "admin_recipe_view_free" if is_free else "admin_recipe_view_paid"
    confirm_prefix = "admin_recipe_confirm_delete_free" if is_free else "admin_recipe_confirm_delete_paid"
    
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"{confirm_prefix}_{recipe_id}"),
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"{view_prefix}_{recipe_id}")
    )
    return builder.as_markup()
