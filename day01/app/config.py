import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./portfolio_reviewer.db"
    GEMINI_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
