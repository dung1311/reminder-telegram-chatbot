from pydantic_settings import BaseSettings
from pytz import timezone
from typing import Any

class Settings(BaseSettings):
    telegram_bot_token: str
    admin_id: str
    TIMEZONE: Any = timezone("Asia/Ho_Chi_Minh")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()