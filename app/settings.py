from pydantic_settings import BaseSettings, SettingsConfigDict

SETTINGS_FILE = ".env"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=SETTINGS_FILE,
        env_file_encoding="utf-8",
    )

    debug: bool = False


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=SETTINGS_FILE,
        env_file_encoding="utf-8",
    )

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=SETTINGS_FILE,
        env_file_encoding="utf-8",
    )

    database_async_schema: str
    database_sync_schema: str
    database_url_suffix: str
    database_echo: bool = True


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=SETTINGS_FILE,
        env_file_encoding="utf-8",
    )

    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None


app_settings = AppSettings()
auth_settings = AuthSettings()  # type: ignore[call-arg]
database_settings = DatabaseSettings()  # type: ignore[call-arg]
redis_settings = RedisSettings()  # type: ignore[call-arg]
