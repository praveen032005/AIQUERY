import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

class Settings(BaseSettings):
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

settings = Settings()
