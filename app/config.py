from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    github_token: str
    github_repository: str
    devin_api_token: str
    devin_org_id: str
    max_acu_limit: int = 5
    poll_interval_seconds: int = 45
    session_poll_interval_seconds: int = 20
    database_path: str = "./data/jobs.db"


settings = Settings()
