from sqlalchemy import BigInteger, String, ForeignKey, Float, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(32))
    full_name: Mapped[str] = mapped_column(String(128))

class Recipe(Base):
    __tablename__ = 'recipes'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float)
    content: Mapped[str] = mapped_column(Text)  # Текст рецепта или ссылка

class Order(Base):
    __tablename__ = 'orders'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id'))
    status: Mapped[str] = mapped_column(String(20), default='pending')  # pending, paid
    payment_method: Mapped[str | None] = mapped_column(String(20))

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
