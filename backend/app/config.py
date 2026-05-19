from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    HEALTH_CHECK_INTERVAL_SEC: int = 60
    HEALTH_CHECK_TIMEOUT_SEC: int = 3
    HEALTH_CHECK_CONCURRENCY: int = 50

    CROSSTEST_PAIR_TIMEOUT_SEC: int = 70
    CROSSTEST_MAX_CONCURRENT_PAIRS: int = 150
    CROSSTEST_DISPATCH_INTERVAL_MS: int = 100


settings = Settings()
