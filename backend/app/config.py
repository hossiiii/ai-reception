
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings"""

    # OpenAI Configuration
    openai_api_key: str

    # Google Calendar Configuration
    google_service_account_key: str
    meeting_room_calendar_ids: str

    # Slack Configuration
    slack_webhook_url: str

    # Application Configuration
    environment: str = "development"
    debug: bool = True
    cors_origins: list[str] = [
        "http://localhost:3000", 
        "http://localhost:3001",
        "https://your-vercel-app.vercel.app",
        "*"  # Allow all origins for development
    ]

    # Session Configuration
    session_timeout_minutes: int = 30
    max_correction_attempts: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
