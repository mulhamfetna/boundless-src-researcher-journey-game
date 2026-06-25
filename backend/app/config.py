import os
from dataclasses import dataclass


@dataclass
class Settings:
    bot_token: str
    db_path: str
    public_url: str


def load_settings() -> Settings:
    return Settings(
        bot_token=os.environ.get("BOT_TOKEN", ""),
        db_path=os.environ.get("QUIZ_DB_PATH", "./quiz.db"),
        public_url=os.environ.get("PUBLIC_URL", "http://localhost:8000"),
    )


settings = load_settings()
