from sqlalchemy import BigInteger, String, ForeignKey, Float, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(32))
    full_name: Mapped[str] = mapped_column(String(128))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_privileged: Mapped[bool] = mapped_column(Boolean, default=False)

class Recipe(Base):
    __tablename__ = 'recipes'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Связь с контентом
    content: Mapped["RecipeContent"] = relationship(back_populates="recipe", cascade="all, delete-orphan")

class FreeRecipe(Base):
    __tablename__ = 'free_recipes'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    external_link: Mapped[str] = mapped_column(Text)

class RecipeContent(Base):
    __tablename__ = 'recipe_contents'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id'))
    
    recipe_text: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    ingredients: Mapped[str | None] = mapped_column(Text)
    inventory: Mapped[str | None] = mapped_column(Text)
    shops: Mapped[str | None] = mapped_column(Text)
    
    recipe: Mapped["Recipe"] = relationship(back_populates="content")

class Order(Base):
    __tablename__ = 'orders'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id'))
    status: Mapped[str] = mapped_column(String(20), default='pending')  # pending, paid
    payment_id: Mapped[str | None] = mapped_column(String(128))
    payment_method: Mapped[str | None] = mapped_column(String(20))

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
