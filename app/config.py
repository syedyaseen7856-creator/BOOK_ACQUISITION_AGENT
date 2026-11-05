from pathlib import Path
from typing import Set
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "SyllExtract Book Acquisition Agent"
    APP_VERSION: str = "0.2.0"
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # Google Gemini Flash LLM
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Metadata & Repositories
    GOOGLE_BOOKS_API_KEY: str | None = None
    SEARCH_PROVIDER: str = "mock"  # "mock", "direct"
    
    ALLOWED_DOMAINS: str = (
        "gutenberg.org,archive.org,openlibrary.org,doabooks.org,books.google.com,gutendex.com,pages.cs.wisc.edu,wisc.edu,openstax.org,assets.openstax.org,opendatastructures.org,crossref.org,doi.org,deeplearningbook.org,mit.edu,umn.edu"
    )


    # Safety limits & timeouts
    MAX_FILE_SIZE_MB: int = 50
    REQUEST_TIMEOUT_SECONDS: int = 15
    APPROVAL_EXPIRY_HOURS: int = 24

    # Storage Paths
    STORAGE_DIR: str = "./data"
    DATABASE_FILE: str = "book_agent.db"

    @property
    def allowed_domains_set(self) -> Set[str]:
        return {d.strip().lower() for d in self.ALLOWED_DOMAINS.split(",") if d.strip()}

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        return self.storage_path / self.DATABASE_FILE

    @property
    def downloads_path(self) -> Path:
        p = self.storage_path / "downloads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def quarantine_path(self) -> Path:
        p = self.storage_path / "quarantine"
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
