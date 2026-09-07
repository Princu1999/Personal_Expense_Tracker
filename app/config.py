import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:1234@localhost:5432/expense_tracker",
    )
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")
    )  # 7 days

    # Guardrails settings
    ENABLE_GUARDRAILS: bool = os.getenv("ENABLE_GUARDRAILS", "true").lower() in ("true", "1", "yes")
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    ENABLE_PII_REDACTION: bool = os.getenv("ENABLE_PII_REDACTION", "true").lower() in ("true", "1", "yes")
    ENABLE_PROMPT_INJECTION: bool = os.getenv("ENABLE_PROMPT_INJECTION", "true").lower() in ("true", "1", "yes")
    ENABLE_TOXICITY: bool = os.getenv("ENABLE_TOXICITY", "true").lower() in ("true", "1", "yes")
    ENABLE_HALLUCINATION_CHECK: bool = os.getenv("ENABLE_HALLUCINATION_CHECK", "true").lower() in ("true", "1", "yes")
    ENABLE_POLICY_COMPLIANCE: bool = os.getenv("ENABLE_POLICY_COMPLIANCE", "true").lower() in ("true", "1", "yes")
    ENABLE_FORMAT_VALIDATION: bool = os.getenv("ENABLE_FORMAT_VALIDATION", "true").lower() in ("true", "1", "yes")

    @property
    def postgres_connection_string(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url


settings = Settings()


