from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Kalshi
    kalshi_api_key_id: str = ""
    kalshi_private_key_path: str = "./kalshi_private_key.pem"
    kalshi_use_demo: bool = True

    # Bot
    database_path: str = "./arbitrage.db"

    # Scanner
    espn_poll_interval: float = 10.0  # seconds
    kalshi_poll_interval: float = 15.0  # seconds

    @property
    def kalshi_base_url(self) -> str:
        if self.kalshi_use_demo:
            return "https://demo-api.kalshi.co/trade-api/v2"
        return "https://api.kalshi.co/trade-api/v2"

settings = Settings()
