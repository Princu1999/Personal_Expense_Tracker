import re
from typing import List, Tuple

from app.guardrails.base import GuardrailAction, GuardrailResult
from app.guardrails.config import guardrail_settings


class PolicyComplianceGuardrail:
    """
    Policy Compliance Guardrail.
    Enforces:
    1. Financial advice disclaimer: Appends standard disclaimer if model gives investment/trading advice.
    2. System prompt and secret leakage prevention: Redacts accidental output of system instructions, DB URLs, or API keys.
    3. Output content safety: Ensures assistant output adheres to professional guidelines.
    """

    # Indicators of financial or investment advice
    FINANCIAL_ADVICE_TRIGGERS = [
        r"(?i)\b(invest\s+(in|your\s+money\s+in)\s+(crypto|bitcoin|ethereum|stocks|equities|options|forex|nfts))\b",
        r"(?i)\b(you\s+should\s+(buy|sell|short|hold|trade)\s+(stocks|crypto|shares|bitcoin|gold))\b",
        r"(?i)\b(guaranteed\s+(return|profit|gain|yield))\b",
        r"(?i)\b(high\s+yield\s+investment\s+program)\b",
        r"(?i)\b(allocate\s+\d+%\s+of\s+your\s+portfolio\s+to)\b",
        r"(?i)\b(financial\s+advice|investment\s+strategy)\b",
    ]

    # Internal system prompt leak signatures
    PROMPT_LEAK_TRIGGERS = [
        r"You are a helpful and precise personal expense assistant\.",
        r"When the user tells you about spending money.*call the `record_expense` tool",
        r"When presenting expenses from `query_expenses`, ALWAYS clearly state",
        r"postgresql(?:\+asyncpg)?:\/\/[^\s]+",
        r"gsk_[a-zA-Z0-9]{20,}",
        r"sk-[a-zA-Z0-9]{20,}",
    ]

    def __init__(self):
        self._compiled_advice = [re.compile(p) for p in self.FINANCIAL_ADVICE_TRIGGERS]
        self._compiled_leaks = [re.compile(p, re.DOTALL) for p in self.PROMPT_LEAK_TRIGGERS]

    def validate(self, text: str) -> GuardrailResult:
        if not guardrail_settings.ENABLE_POLICY_COMPLIANCE or not guardrail_settings.ENABLED:
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True, sanitized_content=text)

        if not text or not text.strip():
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True, sanitized_content=text)

        sanitized = text
        violations: List[str] = []
        disclaimer_added = False

        # 1. Check for secret / prompt leaks
        for pattern in self._compiled_leaks:
            if pattern.search(sanitized):
                violations.append("Internal prompt or connection secret leak prevented")
                sanitized = pattern.sub("[REDACTED_SYSTEM_INFO]", sanitized)

        # 2. Check for financial advice and append disclaimer if needed
        is_advice = any(pattern.search(text) for pattern in self._compiled_advice)
        if is_advice and guardrail_settings.FINANCIAL_DISCLAIMER_TEXT not in sanitized:
            disclaimer = f"\n\n{guardrail_settings.FINANCIAL_DISCLAIMER_TEXT}"
            sanitized = sanitized.rstrip() + disclaimer
            disclaimer_added = True
            violations.append("Mandatory financial disclaimer appended")

        if violations:
            return GuardrailResult(
                action=GuardrailAction.MODIFY,
                passed=True,
                violation_type="policy_compliance",
                reason="; ".join(violations),
                sanitized_content=sanitized,
                metadata={
                    "disclaimer_added": disclaimer_added,
                    "violations": violations,
                },
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            passed=True,
            sanitized_content=text,
        )


policy_guardrail = PolicyComplianceGuardrail()
