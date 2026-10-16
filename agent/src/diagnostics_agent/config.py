from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DIAGNOSTICS_", env_file=".env", extra="ignore")
    server_url: str = "http://127.0.0.1:8000"
    agent_id: str = "local-agent"
    agent_token: str = ""
    request_timeout: float = 10.0
