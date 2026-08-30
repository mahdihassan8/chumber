from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://chumber:chumber@localhost:5432/chumber"
    test_database_url: str = "postgresql+psycopg2://chumber:chumber@localhost:5432/chumber_test"

    jwt_secret_key: str = "dev-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    # 7-day sessions: users stay logged in for a week without re-entering
    # credentials. Since a stolen token would then stay valid for that whole
    # window, this is paired with a token_version check (see core/security.py
    # and core/deps.py) that invalidates all of a user's existing tokens the
    # moment their password changes.
    access_token_expire_days: int = 7

    anthropic_api_key: str = ""

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_email: str = "admin@stchumber.local"
    bootstrap_admin_password: str = "ChangeMe123!"

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
