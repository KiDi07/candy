from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

@dataclass
class Yookassa:
    shop_id: str
    secret_key: str

@dataclass
class TgBot:
    token: str
    admin_ids: list[int]

@dataclass
class Config:
    tg_bot: TgBot
    yookassa: Yookassa

def load_config():
    load_dotenv()
    # Очищаем строку от скобок и пробелов, затем делим по запятой
    raw_admins = getenv("ADMIN_IDS", "").replace("[", "").replace("]", "").strip()
    admins = [int(id.strip()) for id in raw_admins.split(",") if id.strip()]
    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN", "").strip(),
            admin_ids=admins
        ),
        yookassa=Yookassa(
            shop_id=getenv("YOOKASSA_SHOP_ID", "").strip(),
            secret_key=getenv("YOOKASSA_SECRET_KEY", "").strip()
        )
    )
