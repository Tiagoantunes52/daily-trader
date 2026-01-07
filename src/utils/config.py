"""Configuration management for the application."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class EmailConfig:
    """Email service configuration."""

    sender_email: str
    sender_password: str
    mailgun_domain: str | None = None
    mailgun_api_key: str | None = None
    smtp_server: str | None = None
    smtp_port: int | None = None
    retry_delays: list[int] = None  # Delays in seconds for exponential backoff
    use_mailgun: bool = False

    def __post_init__(self):
        if self.retry_delays is None:
            # Default: 5min, 15min, 30min
            self.retry_delays = [300, 900, 1800]


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""

    morning_time: str  # HH:MM format
    evening_time: str  # HH:MM format
    timezone: str = "UTC"


@dataclass
class APIConfig:
    """API configuration."""

    crypto_api_key: str | None = None
    stock_api_key: str | None = None
    cache_ttl: int = 300  # Cache time-to-live in seconds


@dataclass
class JWTConfig:
    """JWT configuration."""

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


@dataclass
class DatabaseConfig:
    """Database configuration."""

    database_url: str
    echo: bool = False


class Config:
    """Main application configuration."""

    def __init__(self):
        use_mailgun = os.getenv("USE_MAILGUN", "false").lower() == "true"

        self.email = EmailConfig(
            sender_email=os.getenv("SENDER_EMAIL", ""),
            sender_password=os.getenv("SENDER_PASSWORD", ""),
            mailgun_domain=os.getenv("MAILGUN_DOMAIN"),
            mailgun_api_key=os.getenv("MAILGUN_API_KEY"),
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            use_mailgun=use_mailgun,
        )

        self.scheduler = SchedulerConfig(
            morning_time=os.getenv("MORNING_TIME", "06:00"),
            evening_time=os.getenv("EVENING_TIME", "18:00"),
            timezone=os.getenv("TIMEZONE", "UTC"),
        )

        self.api = APIConfig(
            crypto_api_key=os.getenv("CRYPTO_API_KEY"),
            stock_api_key=os.getenv("STOCK_API_KEY"),
            cache_ttl=int(os.getenv("CACHE_TTL", "300")),
        )

        self.database = DatabaseConfig(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./market_tips.db"),
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
        )

        self.jwt = JWTConfig(
            secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
            refresh_token_expire_days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        )

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError if configuration is invalid
        """
        if not self.email.sender_email:
            raise ValueError("SENDER_EMAIL environment variable is required")
        if not self.email.sender_password:
            raise ValueError("SENDER_PASSWORD environment variable is required")

        # Validate time format
        for time_str in [self.scheduler.morning_time, self.scheduler.evening_time]:
            try:
                parts = time_str.split(":")
                if len(parts) != 2:
                    raise ValueError(f"Invalid time format: {time_str}. Use HH:MM")
                hour, minute = int(parts[0]), int(parts[1])
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError(f"Invalid time values: {time_str}")
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid scheduler time configuration: {e}") from e

        return True


# Global config instance
config = Config()
