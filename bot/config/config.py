from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

@dataclass
class TgBot:
    token: str
    admin_ids: list[int]

@dataclass
class Config:
    tg_bot: TgBot

def load_config():
    load_dotenv()
    # Очищаем строку от скобок и пробелов, затем делим по запятой
    raw_admins = getenv("ADMIN_IDS", "").replace("[", "").replace("]", "").strip()
    admins = [int(id.strip()) for id in raw_admins.split(",") if id.strip()]
    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN"),
            admin_ids=admins
        )
    )
