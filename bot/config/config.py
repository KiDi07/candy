from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

@dataclass
class TgBot:
    token: str

@dataclass
class Config:
    tg_bot: TgBot

def load_config():
    load_dotenv()
    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN")
        )
    )
