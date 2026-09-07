import re
from typing import List, Set, Tuple

from app.guardrails.base import GuardrailAction, GuardrailResult
from app.guardrails.config import guardrail_settings


def luhn_checksum_is_valid(card_number: str) -> bool:
    """Validate digits using Luhn algorithm (Mod 10)."""
    digits = [int(c) for c in card_number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    checksum = 0
    reverse_digits = digits[::-1]

    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit

    return checksum % 10 == 0


class PIIGuardrail:
    """
    Personally Identifiable Information (PII) Detection & Redaction Guardrail.
    Sanitizes:
    - Credit Card numbers (with Luhn validation & common card patterns)
    - Social Security Numbers & Aadhaar/National IDs
    - Email Addresses
    - Phone Numbers
    - API Keys, JWTs, and Passwords
    """

    # Email pattern
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    # SSN pattern (XXX-XX-XXXX)
    SSN_PATTERN = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")

    # Aadhaar / 12-digit grouped ID pattern (XXXX XXXX XXXX)
    AADHAAR_PATTERN = re.compile(r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b")

    # Phone numbers (ensuring isolated digit sequences with lookarounds)
    PHONE_PATTERN = re.compile(
        r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
    )

    # API Keys, Tokens, Passwords
    API_KEY_PATTERNS = [
        re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|gsk_[a-zA-Z0-9]{20,})\b"),
        re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),  # JWT
        re.compile(r"(?i)\b(?:api[_-]?key|secret[_-]?key|token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?"),
    ]

    PASSWORD_PATTERN = re.compile(
        r"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?"
    )

    # Credit card candidates (13 to 19 digits with optional hyphens/spaces)
    CC_CANDIDATE_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)")

    def _redact_credit_cards(self, text: str) -> Tuple[str, List[str]]:
        detected = []
        result = text

        for match in self.CC_CANDIDATE_PATTERN.finditer(text):
            matched_str = match.group()
            digits_only = re.sub(r"\D", "", matched_str)
            # Check Luhn or 15-16 digit sequence matching card brands
            if 13 <= len(digits_only) <= 19 and (
                luhn_checksum_is_valid(digits_only)
                or bool(re.search(r"(?i)(?:card|visa|mastercard|amex|credit|debit)\s*#?:?\s*" + re.escape(matched_str), text))
                or len(digits_only) in (15, 16)
            ):
                placeholder = guardrail_settings.PII_PLACEHOLDERS["credit_card"]
                result = result.replace(matched_str, placeholder)
                detected.append("credit_card")

        return result, detected

    def sanitize(self, text: str) -> Tuple[str, List[str]]:
        """Sanitizes text by replacing all detected PII with generic placeholders."""
        if not text or not text.strip():
            return text, []

        detected_entities: Set[str] = set()
        sanitized = text

        # 1. Redact Credit Cards first before general phone numbers
        sanitized, cc_detected = self._redact_credit_cards(sanitized)
        if cc_detected:
            detected_entities.add("credit_card")

        # 2. Redact SSN
        if self.SSN_PATTERN.search(sanitized):
            placeholder = guardrail_settings.PII_PLACEHOLDERS["ssn"]
            sanitized = self.SSN_PATTERN.sub(placeholder, sanitized)
            detected_entities.add("ssn")

        # 3. Redact National ID (Aadhaar)
        if self.AADHAAR_PATTERN.search(sanitized):
            placeholder = guardrail_settings.PII_PLACEHOLDERS["national_id"]
            sanitized = self.AADHAAR_PATTERN.sub(placeholder, sanitized)
            detected_entities.add("national_id")

        # 4. Redact API Keys / Tokens
        for pattern in self.API_KEY_PATTERNS:
            if pattern.search(sanitized):
                placeholder = guardrail_settings.PII_PLACEHOLDERS["api_key"]
                sanitized = pattern.sub(placeholder, sanitized)
                detected_entities.add("api_key")

        # 5. Redact Passwords
        if self.PASSWORD_PATTERN.search(sanitized):
            placeholder = guardrail_settings.PII_PLACEHOLDERS["password"]
            sanitized = self.PASSWORD_PATTERN.sub(f"password: {placeholder}", sanitized)
            detected_entities.add("password")

        # 6. Redact Email addresses
        if self.EMAIL_PATTERN.search(sanitized):
            placeholder = guardrail_settings.PII_PLACEHOLDERS["email"]
            sanitized = self.EMAIL_PATTERN.sub(placeholder, sanitized)
            detected_entities.add("email")

        # 7. Redact Phone numbers
        if self.PHONE_PATTERN.search(sanitized):
            placeholder = guardrail_settings.PII_PLACEHOLDERS["phone"]
            sanitized = self.PHONE_PATTERN.sub(placeholder, sanitized)
            detected_entities.add("phone")

        return sanitized, sorted(list(detected_entities))

    def validate(self, text: str) -> GuardrailResult:
        if not guardrail_settings.ENABLE_PII_REDACTION or not guardrail_settings.ENABLED:
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True, sanitized_content=text)

        sanitized_text, detected_pii = self.sanitize(text)

        if detected_pii:
            return GuardrailResult(
                action=GuardrailAction.MODIFY,
                passed=True,
                violation_type="pii_detected",
                reason=f"PII detected and redacted: {', '.join(detected_pii)}",
                sanitized_content=sanitized_text,
                metadata={"redacted_types": detected_pii},
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            passed=True,
            sanitized_content=text,
        )


pii_guardrail = PIIGuardrail()
