import os
from dataclasses import dataclass, field
from typing import List

from app.config import settings


@dataclass
class GuardrailsConfig:
    # Master switch
    ENABLED: bool = settings.ENABLE_GUARDRAILS

    # Input guardrail switches
    ENABLE_RATE_LIMITING: bool = settings.ENABLE_GUARDRAILS
    ENABLE_PROMPT_INJECTION: bool = settings.ENABLE_PROMPT_INJECTION
    ENABLE_TOXICITY: bool = settings.ENABLE_TOXICITY
    ENABLE_PII_REDACTION: bool = settings.ENABLE_PII_REDACTION

    # Output guardrail switches
    ENABLE_HALLUCINATION_CHECK: bool = settings.ENABLE_HALLUCINATION_CHECK
    ENABLE_POLICY_COMPLIANCE: bool = settings.ENABLE_POLICY_COMPLIANCE
    ENABLE_FORMAT_VALIDATION: bool = settings.ENABLE_FORMAT_VALIDATION

    # Rate limiting settings
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = settings.RATE_LIMIT_PER_MINUTE
    RATE_LIMIT_BURST_MAX: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Prompt injection settings
    PROMPT_INJECTION_SENSITIVITY: float = 0.5  # Threshold score (0.0 to 1.0)

    # Toxicity settings
    TOXICITY_STRICT_MODE: bool = False

    # Financial policy settings
    FINANCIAL_DISCLAIMER_TEXT: str = (
        "> ⚠️ **Disclaimer:** *I am an expense tracking assistant. This information is for "
        "personal budgeting and tracking purposes only and does not constitute professional "
        "financial, investment, or tax advice.*"
    )

    # Redaction placeholders
    PII_PLACEHOLDERS: dict = field(
        default_factory=lambda: {
            "credit_card": "[REDACTED_CREDIT_CARD]",
            "ssn": "[REDACTED_SSN]",
            "national_id": "[REDACTED_NATIONAL_ID]",
            "phone": "[REDACTED_PHONE]",
            "email": "[REDACTED_EMAIL]",
            "api_key": "[REDACTED_API_KEY]",
            "password": "[REDACTED_PASSWORD]",
        }
    )


guardrail_settings = GuardrailsConfig()
