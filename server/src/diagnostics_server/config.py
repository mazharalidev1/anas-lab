from pydantic_settings import BaseSettings, SettingsConfigDict

class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://diagnostics:diagnostics@127.0.0.1:5432/diagnostics"
    agent_token: str = "dev-only-change-me"

settings = ServerSettings()
