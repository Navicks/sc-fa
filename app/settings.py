from pydantic_settings import BaseSettings, SettingsConfigDict

SETTINGS_FILE = ".env"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=SETTINGS_FILE,
        env_file_encoding="utf-8",
    )

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


auth_settings = AuthSettings()
