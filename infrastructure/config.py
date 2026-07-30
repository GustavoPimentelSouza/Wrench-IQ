import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    db_host: str = os.getenv("DB_HOST", "postgres")
    db_port: str = os.getenv("DB_PORT", "5432")
    db_user: str = os.getenv("DB_USER", "wrenchiq")
    db_password: str = os.getenv("DB_PASSWORD", "wrenchiq")
    db_name: str = os.getenv("DB_NAME", "wrenchiq")
    database_url_test: str = os.getenv(
        "DATABASE_URL_TEST",
        "postgresql+asyncpg://wrenchiq:wrenchiq@localhost:5433/wrenchiq",
    )
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "wrenchiq-dev-jwt-secret")
    jwt_expira_minutos: int = int(os.getenv("JWT_EXPIRA_MINUTOS", "60"))
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
