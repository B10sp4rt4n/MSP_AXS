from pydantic import BaseSettings


class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./database/axs.db"
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    class Config:
        env_file = ".env"


settings = Settings()
