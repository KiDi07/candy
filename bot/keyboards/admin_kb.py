from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def get_admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📜 Список рецептов", callback_data="admin_recipes_list"))
    builder.row(InlineKeyboardButton(text="➕ Добавить рецепт", callback_data="admin_recipe_add"))
    return builder.as_markup()

def get_admin_recipes_kb(recipes):
    builder = InlineKeyboardBuilder()
    for recipe in recipes:
        builder.row(InlineKeyboardButton(text=recipe.title, callback_data=f"admin_recipe_view_{recipe.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main"))
    return builder.as_markup()

def get_recipe_edit_kb(recipe_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Название", callback_data=f"edit_field_title_{recipe_id}"),
        InlineKeyboardButton(text="Цена", callback_data=f"edit_field_price_{recipe_id}")
    )
    builder.row(
        InlineKeyboardButton(text="Описание", callback_data=f"edit_field_description_{recipe_id}"),
        InlineKeyboardButton(text="Текст рецепта", callback_data=f"edit_field_recipe_text_{recipe_id}")
    )
    builder.row(
        InlineKeyboardButton(text="Видео (URL)", callback_data=f"edit_field_video_url_{recipe_id}"),
        InlineKeyboardButton(text="Ингредиенты", callback_data=f"edit_field_ingredients_{recipe_id}")
    )
    builder.row(
        InlineKeyboardButton(text="Инвентарь", callback_data=f"edit_field_inventory_{recipe_id}"),
        InlineKeyboardButton(text="Ссылки", callback_data=f"edit_field_shops_{recipe_id}")
    )
    builder.row(InlineKeyboardButton(text="❌ Удалить рецепт", callback_data=f"admin_recipe_delete_{recipe_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ К списку", callback_data="admin_recipes_list"))
    return builder.as_markup()

def get_cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    return builder.as_markup()
