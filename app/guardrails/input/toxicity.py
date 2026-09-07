import re
from typing import List, Set

from app.guardrails.base import GuardrailAction, GuardrailResult
from app.guardrails.config import guardrail_settings


class ToxicityGuardrail:
    """
    Toxicity and Content Moderation Guardrail.
    Detects:
    1. Profanity and vulgar abuse
    2. Hate speech, discrimination, and slurs
    3. Threats of physical harm and violence
    4. Explicit self-harm or illegal activity incitement
    """

    # Slurs, hate speech, and severe vulgar abuse patterns (with word boundaries)
    SEVERE_TOXIC_TERMS = [
        r"\b(fuck\s*(you|off|u)|stfu|bitch|bastard|dickhead|asshole|motherfucker|cunt)\b",
        r"\b(nigger|faggot|kike|chink|spic|wetback|retard)\b",
        r"\b(kill\s+yourself|go\s+die|commit\s+suicide)\b",
        r"\b(i\s+will\s+(kill|murder|attack|bomb|harm|rape|destroy)\s+(you|them|all))\b",
        r"\b(how\s+to\s+(make\s+a\s+bomb|synthesize\s+drugs|steal\s+credit\s+cards|hack\s+bank))\b",
    ]

    # Mild profanity terms
    MILD_PROFANITY_TERMS = [
        r"\b(damn|hell|crap|piss|shit|bullshit|fucking)\b",
    ]

    # Character substitutions for leetspeak normalization
    LEET_MAP = {
        "@": "a",
        "4": "a",
        "$": "s",
        "5": "s",
        "0": "o",
        "1": "i",
        "!": "i",
        "3": "e",
        "7": "t",
        "+": "t",
    }

    def __init__(self):
        self._compiled_severe = [re.compile(p, re.IGNORECASE) for p in self.SEVERE_TOXIC_TERMS]
        self._compiled_mild = [re.compile(p, re.IGNORECASE) for p in self.MILD_PROFANITY_TERMS]

    def _normalize_leetspeak(self, text: str) -> str:
        """Normalize common obfuscated leetspeak characters."""
        normalized = text.lower()
        for char, sub in self.LEET_MAP.items():
            normalized = normalized.replace(char, sub)
        # Collapse multiple repeated characters (e.g. fuuuuck -> fuck)
        normalized = re.sub(r"(.)\1{2,}", r"\1\1", normalized)
        return normalized

    def validate(self, text: str) -> GuardrailResult:
        if not guardrail_settings.ENABLE_TOXICITY or not guardrail_settings.ENABLED:
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True)

        if not text or not text.strip():
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True)

        normalized_text = self._normalize_leetspeak(text)
        detected_violations: List[str] = []

        # Check severe toxicity
        for pattern in self._compiled_severe:
            match = pattern.search(text) or pattern.search(normalized_text)
            if match:
                detected_violations.append(f"Severe toxic content/threat: '{match.group()}'")

        # In strict mode, also block mild profanity
        if guardrail_settings.TOXICITY_STRICT_MODE:
            for pattern in self._compiled_mild:
                match = pattern.search(text) or pattern.search(normalized_text)
                if match:
                    detected_violations.append(f"Profane language: '{match.group()}'")

        if detected_violations:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                passed=False,
                violation_type="toxic_content",
                reason="; ".join(detected_violations),
                metadata={"triggers": detected_violations},
                safe_response=(
                    "I am committed to providing a helpful, respectful experience for managing your expenses. "
                    "Please refrain from using abusive, threatening, or offensive language."
                ),
            )

        return GuardrailResult(action=GuardrailAction.ALLOW, passed=True)


toxicity_guardrail = ToxicityGuardrail()
