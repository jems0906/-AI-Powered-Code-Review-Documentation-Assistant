from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://codereview:password@localhost:5432/codereview"
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_AI_PROVIDER: str = "openai"  # openai | anthropic

    # GitHub
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY_PATH: str = "./github-app.pem"
    GITHUB_WEBHOOK_SECRET: str = "change-me"
    GITHUB_INSTALLATION_ID: str = ""

    # GitLab
    GITLAB_API_URL: str = "https://gitlab.com/api/v4"
    GITLAB_TOKEN: str = ""
    GITLAB_WEBHOOK_SECRET: str = "change-me"

    # Slack
    SLACK_BOT_TOKEN: str = ""
    SLACK_CHANNEL_ID: str = ""

    # App
    SECRET_KEY: str = "change-me-in-production-32chars-min"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
