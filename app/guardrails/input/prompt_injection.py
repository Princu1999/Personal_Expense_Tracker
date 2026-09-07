import base64
import re
from typing import List, Tuple

from app.guardrails.base import GuardrailAction, GuardrailResult
from app.guardrails.config import guardrail_settings


class PromptInjectionGuardrail:
    """
    Multi-layered Prompt Injection and Jailbreak detection guardrail.
    Analyzes:
    1. Direct override and instruction replacement commands
    2. System prompt extraction and leakage attempts
    3. Special token and delimiter injections (ChatML, Llama syntax, system delimiters)
    4. Known jailbreak and roleplaying exploits (DAN, developer mode, unrestricted mode)
    5. Obfuscated base64 encoded injection payloads
    """

    # Direct override patterns
    OVERRIDE_PATTERNS = [
        r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules|commands|context)\b",
        r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules|directives)\b",
        r"(?i)\bforget\s+(all\s+)?(previous|prior|system)\s+(instructions|rules|constraints)\b",
        r"(?i)\boverride\s+(all\s+)?(system|safety|security)\s+(prompts|rules|instructions|policies)\b",
        r"(?i)\bnew\s+instructions\s*:\s*you\s+are\s+now\b",
        r"(?i)\bdo\s+not\s+follow\s+(your\s+)?(initial|original|system)\s+(instructions|rules)\b",
        r"(?i)\byou\s+are\s+no\s+longer\s+(an\s+expense\s+tracker|bound\s+by\s+rules|restricted)\b",
    ]

    # System prompt extraction patterns
    EXFILTRATION_PATTERNS = [
        r"(?i)\b(print|reveal|show|display|output|repeat|leak|dump)\s+(your\s+)?(entire\s+)?(system\s+prompt|initial\s+instructions|developer\s+prompt|hidden\s+prompt)\b",
        r"(?i)\bwhat\s+are\s+your\s+(exact\s+)?(system\s+instructions|system\s+prompts|initial\s+directives|hidden\s+rules)\b",
        r"(?i)\brepeat\s+the\s+(words|text)\s+above\s+verbatim\b",
        r"(?i)\bwhat\s+is\s+written\s+at\s+the\s+very\s+beginning\s+of\s+this\s+conversation\b",
    ]

    # Delimiter and special token injection patterns
    DELIMITER_PATTERNS = [
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"<\|system\|>",
        r"<\|user\|>",
        r"<\|assistant\|>",
        r"\[INST\]",
        r"\[/INST\]",
        r"<<SYS>>",
        r"<</SYS>>",
        r"```system",
        r"```prompt",
        r"\{\{\s*system\s*\}\}",
    ]

    # Jailbreak and persona hijacking patterns
    JAILBREAK_PATTERNS = [
        r"(?i)\bdo\s+anything\s+now\b",
        r"(?i)\bDAN\s+mode\b",
        r"(?i)\bdeveloper\s+mode\s+(enabled|active|on)\b",
        r"(?i)\bact\s+as\s+an\s+unrestricted\s+ai\b",
        r"(?i)\bhypothetical\s+scenario\s+where\s+you\s+have\s+no\s+(rules|ethics|guardrails|safety)\b",
        r"(?i)\bjailbreak(ed)?\s+(mode|prompt|persona)\b",
        r"(?i)\bpretend\s+you\s+are\s+(an\s+evil|unfiltered|uncensored|unaligned)\b",
        r"(?i)\bdisable\s+all\s+(safety|content|security)\s+filters\b",
        r"(?i)\bsimulate\s+a\s+conversation\s+where\s+you\s+have\s+no\s+restrictions\b",
    ]

    def __init__(self, sensitivity: float = guardrail_settings.PROMPT_INJECTION_SENSITIVITY):
        self.sensitivity = sensitivity
        self._compiled_override = [re.compile(p) for p in self.OVERRIDE_PATTERNS]
        self._compiled_exfiltration = [re.compile(p) for p in self.EXFILTRATION_PATTERNS]
        self._compiled_delimiter = [re.compile(p, re.IGNORECASE) for p in self.DELIMITER_PATTERNS]
        self._compiled_jailbreak = [re.compile(p) for p in self.JAILBREAK_PATTERNS]

    def _check_base64_injection(self, text: str) -> Tuple[bool, str]:
        """Detect and decode potential base64 hidden injection strings."""
        b64_pattern = re.compile(r"\b[A-Za-z0-9+/]{20,}={0,2}\b")
        matches = b64_pattern.findall(text)
        for match in matches:
            try:
                decoded = base64.b64decode(match).decode("utf-8", errors="ignore").lower()
                for pattern in self._compiled_override + self._compiled_jailbreak:
                    if pattern.search(decoded):
                        return True, f"Base64 encoded injection payload: '{match[:16]}...'"
            except Exception:
                continue
        return False, ""

    def validate(self, text: str) -> GuardrailResult:
        if not guardrail_settings.ENABLE_PROMPT_INJECTION or not guardrail_settings.ENABLED:
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True)

        if not text or not text.strip():
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True)

        reasons: List[str] = []
        score = 0.0

        # 1. Delimiter injections (High risk)
        for pattern in self._compiled_delimiter:
            if pattern.search(text):
                score += 0.8
                reasons.append(f"Contains reserved delimiter/tag: '{pattern.pattern}'")

        # 2. Direct override commands (High risk)
        for pattern in self._compiled_override:
            match = pattern.search(text)
            if match:
                score += 0.9
                reasons.append(f"Instruction override attempt detected: '{match.group()}'")

        # 3. System prompt extraction (High risk)
        for pattern in self._compiled_exfiltration:
            match = pattern.search(text)
            if match:
                score += 0.7
                reasons.append(f"System prompt exfiltration attempt: '{match.group()}'")

        # 4. Jailbreak patterns (High risk)
        for pattern in self._compiled_jailbreak:
            match = pattern.search(text)
            if match:
                score += 0.8
                reasons.append(f"Jailbreak/persona manipulation pattern: '{match.group()}'")

        # 5. Obfuscated Base64 checks
        b64_detected, b64_reason = self._check_base64_injection(text)
        if b64_detected:
            score += 0.9
            reasons.append(b64_reason)

        if score >= self.sensitivity:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                passed=False,
                violation_type="prompt_injection",
                reason="; ".join(reasons),
                metadata={"risk_score": min(score, 1.0), "triggers": reasons},
                safe_response=(
                    "I cannot fulfill this request because it contains instructions that attempt "
                    "to override system security policies or exfiltrate private prompts. "
                    "How can I assist you with your expenses?"
                ),
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            passed=True,
            metadata={"risk_score": score},
        )


prompt_injection_guardrail = PromptInjectionGuardrail()
