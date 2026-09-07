import re
from typing import Tuple

from app.guardrails.base import GuardrailAction, GuardrailResult
from app.guardrails.config import guardrail_settings


class FormatGuardrail:
    """
    Output Format Validation and Sanitization Guardrail.
    Repairs:
    - Unclosed markdown code fences (```)
    - Leaked raw tool call tags (<tool_call>...</tool_call> or <function=...>)
    - Trailing unclosed formatting tokens
    - Redundant whitespace and malformed markdown syntax
    """

    RAW_TOOL_CALL_PATTERN = re.compile(
        r"(?:<tool_call>.*?</tool_call>|<function=[^>]+>.*?</function>|<function_calls>.*?</function_calls>)",
        re.DOTALL | re.IGNORECASE,
    )

    def sanitize(self, text: str) -> Tuple[str, bool]:
        if not text:
            return text, False

        modified = False
        result = text

        # 1. Strip raw leaked tool XML tags if present
        if self.RAW_TOOL_CALL_PATTERN.search(result):
            result = self.RAW_TOOL_CALL_PATTERN.sub("", result).strip()
            modified = True

        # 2. Repair unclosed code blocks
        code_fence_count = result.count("```")
        if code_fence_count % 2 != 0:
            result = result.rstrip() + "\n```"
            modified = True

        # 3. Trim excessive blank lines (more than 2 consecutive newlines)
        cleaned_newlines = re.sub(r"\n{3,}", "\n\n", result)
        if cleaned_newlines != result:
            result = cleaned_newlines
            modified = True

        return result, modified

    def validate(self, text: str) -> GuardrailResult:
        if not guardrail_settings.ENABLE_FORMAT_VALIDATION or not guardrail_settings.ENABLED:
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True, sanitized_content=text)

        sanitized, was_modified = self.sanitize(text)

        if was_modified:
            return GuardrailResult(
                action=GuardrailAction.MODIFY,
                passed=True,
                violation_type="format_repaired",
                reason="Markdown syntax or tool artifacts repaired.",
                sanitized_content=sanitized,
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            passed=True,
            sanitized_content=text,
        )


format_guardrail = FormatGuardrail()
