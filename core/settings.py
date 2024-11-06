from dataclasses import dataclass
from environs import Env

@dataclass()
class Bots:
    bot_token: str
    owner_chat_id: int

@dataclass()
class Settings:
    bots: Bots

def get_settings(path: str):
    env = Env()
    env.read_env(path)

    return Settings(
        bots=Bots(
            bot_token=env.str('BOT_TOKEN'),
            owner_chat_id=env.int('OWNER_CHAT_ID')
        )
    )