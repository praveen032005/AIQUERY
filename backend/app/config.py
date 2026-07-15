from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_URI: Optional[str] = None
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash"

settings = Settings()
