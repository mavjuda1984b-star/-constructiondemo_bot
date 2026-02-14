import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bot token
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Admin IDs from .env (comma separated)
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in os.getenv("ADMIN_IDS", "").split(",") if admin_id.strip()]

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///construction.db")

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in cls.ADMIN_IDS

    @classmethod
    def get_admin_ids(cls) -> list:
        """Get list of admin IDs"""
        return cls.ADMIN_IDS

    @classmethod
    def validate_config(cls):
        """Validate configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не указан в .env файле!")

        if not cls.ADMIN_IDS:
            print("⚠️  ADMIN_IDS не указаны в .env файле!")

        print(f"✅ Конфигурация загружена:")
        print(f"   Bot Token: {'✅' if cls.BOT_TOKEN else '❌'}")
        print(f"   Admin IDs: {cls.ADMIN_IDS}")
        print(f"   Database: {cls.DATABASE_URL}")