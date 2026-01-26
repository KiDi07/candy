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

@dataclass
class Config:
    tg_bot: TgBot
    yookassa: Yookassa

def load_config():
    load_dotenv()
    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN", "").strip()
        ),
        yookassa=Yookassa(
            shop_id=getenv("YOOKASSA_SHOP_ID", "").strip(),
            secret_key=getenv("YOOKASSA_SECRET_KEY", "").strip()
        )
    )
