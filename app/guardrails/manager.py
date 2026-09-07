from typing import Any, Dict, List, Optional, Union

from app.guardrails.base import (
    GuardrailAction,
    GuardrailResult,
    InputValidationResult,
    OutputValidationResult,
)
from app.guardrails.config import guardrail_settings
from app.guardrails.input.rate_limiter import rate_limiter
from app.guardrails.input.prompt_injection import prompt_injection_guardrail
from app.guardrails.input.toxicity import toxicity_guardrail
from app.guardrails.input.pii import pii_guardrail
from app.guardrails.output.format import format_guardrail
from app.guardrails.output.policy import policy_guardrail
from app.guardrails.output.hallucination import hallucination_guardrail


class GuardrailsManager:
    """
    Central Guardrails Orchestrator for Input and Output safety checks.
    """

    def __init__(self):
        self.settings = guardrail_settings
        self.rate_limiter = rate_limiter
        self.prompt_injection = prompt_injection_guardrail
        self.toxicity = toxicity_guardrail
        self.pii = pii_guardrail
        self.format_guard = format_guardrail
        self.policy = policy_guardrail
        self.hallucination = hallucination_guardrail

    async def validate_input(
        self,
        text: str,
        user_id: Union[str, int],
        client_ip: Optional[str] = None,
    ) -> InputValidationResult:
        """
        Execute full input guardrail pipeline:
        1. Rate limiting (per-user and per-IP)
        2. Prompt injection and jailbreak detection
        3. Toxicity and abusive content detection
        4. PII detection and redaction
        """
        if not self.settings.ENABLED:
            return InputValidationResult(
                passed=True,
                blocked=False,
                original_text=text,
                sanitized_text=text,
            )

        # 1. Check Rate Limit (User level)
        user_rate_res = await self.rate_limiter.check(f"user:{user_id}")
        if not user_rate_res.passed:
            return InputValidationResult(
                passed=False,
                blocked=True,
                original_text=text,
                sanitized_text=text,
                violation_type=user_rate_res.violation_type,
                violation_reason=user_rate_res.reason,
                safe_response=user_rate_res.safe_response,
                rate_limited=True,
                retry_after=user_rate_res.metadata.get("retry_after", 60),
                details=user_rate_res.metadata,
            )

        # Rate Limit (IP level if provided)
        if client_ip:
            ip_rate_res = await self.rate_limiter.check(f"ip:{client_ip}")
            if not ip_rate_res.passed:
                return InputValidationResult(
                    passed=False,
                    blocked=True,
                    original_text=text,
                    sanitized_text=text,
                    violation_type=ip_rate_res.violation_type,
                    violation_reason=ip_rate_res.reason,
                    safe_response=ip_rate_res.safe_response,
                    rate_limited=True,
                    retry_after=ip_rate_res.metadata.get("retry_after", 60),
                    details=ip_rate_res.metadata,
                )

        # 2. Check Prompt Injection
        pi_res = self.prompt_injection.validate(text)
        if not pi_res.passed or pi_res.action == GuardrailAction.BLOCK:
            return InputValidationResult(
                passed=False,
                blocked=True,
                original_text=text,
                sanitized_text=text,
                violation_type=pi_res.violation_type,
                violation_reason=pi_res.reason,
                safe_response=pi_res.safe_response,
                details=pi_res.metadata,
            )

        # 3. Check Toxicity
        toxic_res = self.toxicity.validate(text)
        if not toxic_res.passed or toxic_res.action == GuardrailAction.BLOCK:
            return InputValidationResult(
                passed=False,
                blocked=True,
                original_text=text,
                sanitized_text=text,
                violation_type=toxic_res.violation_type,
                violation_reason=toxic_res.reason,
                safe_response=toxic_res.safe_response,
                details=toxic_res.metadata,
            )

        # 4. Check & Redact PII
        pii_res = self.pii.validate(text)
        sanitized_text = pii_res.sanitized_content if pii_res.sanitized_content is not None else text
        detected_pii = pii_res.metadata.get("redacted_types", [])

        return InputValidationResult(
            passed=True,
            blocked=False,
            original_text=text,
            sanitized_text=sanitized_text,
            detected_pii=detected_pii,
            details={"pii_detected": len(detected_pii) > 0},
        )

    async def validate_output(
        self,
        response_text: str,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> OutputValidationResult:
        """
        Execute full output guardrail pipeline:
        1. Format validation and syntax repair
        2. Policy compliance & system prompt leak protection & financial disclaimer
        3. Grounding and hallucination verification against tool outputs
        """
        if not self.settings.ENABLED:
            return OutputValidationResult(
                passed=True,
                original_text=response_text,
                sanitized_text=response_text,
            )

        current_text = response_text
        violations: List[str] = []
        hallucination_detected = False
        policy_violation = False
        format_corrected = False
        disclaimer_added = False

        # 1. Format validation & repair
        fmt_res = self.format_guard.validate(current_text)
        if fmt_res.action == GuardrailAction.MODIFY and fmt_res.sanitized_content:
            current_text = fmt_res.sanitized_content
            format_corrected = True
            if fmt_res.reason:
                violations.append(fmt_res.reason)

        # 2. Policy compliance
        policy_res = self.policy.validate(current_text)
        if policy_res.action == GuardrailAction.MODIFY and policy_res.sanitized_content:
            current_text = policy_res.sanitized_content
            policy_violation = True
            disclaimer_added = policy_res.metadata.get("disclaimer_added", False)
            if policy_res.reason:
                violations.append(policy_res.reason)

        # 3. Grounding and Hallucination verification
        if tool_results:
            hal_res = self.hallucination.validate(current_text, tool_results=tool_results)
            if hal_res.action == GuardrailAction.MODIFY and hal_res.sanitized_content:
                current_text = hal_res.sanitized_content
                hallucination_detected = True
                if hal_res.reason:
                    violations.append(hal_res.reason)

        return OutputValidationResult(
            passed=True,
            original_text=response_text,
            sanitized_text=current_text,
            hallucination_detected=hallucination_detected,
            policy_violation_detected=policy_violation,
            format_corrected=format_corrected,
            disclaimer_added=disclaimer_added,
            violation_details=violations,
        )


guardrails_manager = GuardrailsManager()
