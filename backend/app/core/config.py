from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://chumber:chumber@localhost:5432/chumber"
    test_database_url: str = "postgresql+psycopg2://chumber:chumber@localhost:5432/chumber_test"

    # No default on purpose: a signing key is exactly the kind of thing that
    # must never silently fall back to a value baked into the source tree —
    # pydantic-settings raises at startup if it isn't supplied via the
    # environment/.env, which is the fail-safe behavior we want here.
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    # 7-day sessions: users stay logged in for a week without re-entering
    # credentials. Since a stolen token would then stay valid for that whole
    # window, this is paired with a token_version check (see core/security.py
    # and core/deps.py) that invalidates all of a user's existing tokens the
    # moment their password changes.
    access_token_expire_days: int = 7

    gemini_api_key: str = ""

    bootstrap_admin_username: str = "mooane"
    bootstrap_admin_email: str = "admin@stchumber.com"
    # Same reasoning as jwt_secret_key above: no hardcoded fallback password.
    bootstrap_admin_password: str

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
