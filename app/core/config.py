from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://futbol:futbol@localhost:5432/futbol"
    bsd_token: str = ""
    sitio_url: str = "http://localhost:8000"    # URL publica, para canonical y sitemap


settings = Settings()