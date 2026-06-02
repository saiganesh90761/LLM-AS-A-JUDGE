import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AI Safety Guardrail Framework"
    API_V1_STR: str = "/api"
    
    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "supersecretkeychangeinproduction1234567890!")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    # We default to postgresql, but can fallback to sqlite for ease of local development
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./ai_safety.db"
    )
    
    # OpenRouter API
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Google Custom Search API
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_CSE_ID: Optional[str] = os.getenv("GOOGLE_CSE_ID", "")
    
    # Default Models
    DEFAULT_CANDIDATE_MODEL: str = "google/gemini-2.5-flash"
    DEFAULT_JUDGE_MODEL: str = "google/gemini-2.5-pro"
    
    # Guardrail Thresholds
    TOXICITY_THRESHOLD: float = 0.6
    JAILBREAK_THRESHOLD: float = 0.7
    PROMPT_INJECTION_THRESHOLD: float = 0.7
    HALLUCINATION_THRESHOLD: float = 0.5
    MIN_OVERALL_SCORE_FOR_APPROVAL: float = 8.0
    MAX_REGENERATION_LIMIT: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
