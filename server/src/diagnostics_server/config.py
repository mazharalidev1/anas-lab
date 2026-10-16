
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    agent_token: str

    admin_username: str
    admin_password_hash: str
    session_secret: str

    # Set to false only for local HTTP development.
    # Use true when serving the dashboard over HTTPS.
    session_cookie_secure: bool = True

    trusted_origins: str = (
        "http://127.0.0.1:5173,"
        "http://localhost:5173,"
        "http://127.0.0.1:8000,"
        "http://localhost:8000"
    )


settings = ServerSettings()
