import os
from dataclasses import dataclass


@dataclass
class Settings:
    bot_token: str
    db_path: str
    public_url: str
    sample_size: int
    admin_id: int
    bot_username: str


def load_settings() -> Settings:
    return Settings(
        bot_token=os.environ.get("BOT_TOKEN", ""),
        db_path=os.environ.get("QUIZ_DB_PATH", "./quiz.db"),
        public_url=os.environ.get("PUBLIC_URL", "http://localhost:8000"),
        sample_size=int(os.environ.get("SAMPLE_SIZE", "10")),
        admin_id=int(os.environ.get("ADMIN_ID", "0")),
        bot_username=os.environ.get("BOT_USERNAME", "src_quize_bot"),
    )


settings = load_settings()
