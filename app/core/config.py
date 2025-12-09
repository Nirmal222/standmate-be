from pydantic_settings import BaseSettings
from pathlib import Path

# Get the project root directory (parent of app directory)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "your-super-secret-key-change-it"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OAuth
    GOOGLE_CLIENT_ID: str = "your-google-client-id"
    GOOGLE_CLIENT_SECRET: str = "your-google-client-secret"
    
    # URLs
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # Mailjet
    MAILJET_API_KEY: str = ""
    MAILJET_SECRET_KEY: str = ""
    MAILJET_SENDER_EMAIL: str = "nirmal@huzlr.com"

    # Admin
    ADMIN_SECRET: str = "admin-secret-key"

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # Ignore extra fields in .env file

settings = Settings()
