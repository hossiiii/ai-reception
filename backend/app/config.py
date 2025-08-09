
from typing import List

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
    
    # CORS Configuration
    allowed_origins: str = ""  # Comma-separated list for production
    
    # Session Configuration
    session_timeout_minutes: int = 30
    max_correction_attempts: int = 3

    @property
    def cors_origins(self) -> List[str]:
        """
        Get CORS origins based on environment.
        
        Returns:
            - ["*"] for development environment (allows all origins)
            - Specific origins from ALLOWED_ORIGINS env var for production
        """
        if self.environment == "development":
            # In development, allow all origins for easier testing
            return ["*"]
        else:
            # In production, use specific allowed origins
            if self.allowed_origins:
                # Parse comma-separated origins
                origins = [origin.strip() for origin in self.allowed_origins.split(",")]
                # Filter out empty strings
                return [origin for origin in origins if origin]
            else:
                # Fallback to a safe default (no origins allowed)
                return []
    
    @property
    def cors_allow_credentials(self) -> bool:
        """
        Whether to allow credentials in CORS requests.
        
        Returns:
            - False when allowing all origins (*)
            - True when using specific origins
        """
        return "*" not in self.cors_origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
