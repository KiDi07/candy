import asyncio
from bot.database.models import async_session, engine, Base, Recipe, RecipeContent
from bot.utils import texts
from sqlalchemy import select

async def fill_db():
    # Пересоздаем таблицы для новой структуры
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 1. Создаем рецепт
        red_velvet = Recipe(
            id=1,
            title="Бисквит «Красный бархат»",
            description="Классический американский десерт с нежным шоколадным вкусом и эффектным красным цветом.",
            price=1.0
        )
        session.add(red_velvet)
        await session.flush() # Получаем ID рецепта

        # 2. Создаем контент для рецепта
        red_velvet_content = RecipeContent(
            recipe_id=red_velvet.id,
            recipe_text=texts.RED_VELVET_RECIPE,
            video_url=texts.RED_VELVET_VIDEO,
            ingredients=texts.RED_VELVET_INGREDIENTS,
            inventory=texts.RED_VELVET_INVENTORY,
            shops=texts.RED_VELVET_SHOPS
        )
        session.add(red_velvet_content)
        
        await session.commit()
        print("База данных успешно обновлена (2 таблицы) и заполнена!")

if __name__ == "__main__":
    asyncio.run(fill_db())
