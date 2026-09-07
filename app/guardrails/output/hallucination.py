import re
from typing import Any, Dict, List, Optional, Tuple

from app.guardrails.base import GuardrailAction, GuardrailResult
from app.guardrails.config import guardrail_settings


class HallucinationGuardrail:
    """
    Grounding and Hallucination Verification Guardrail for expense operations.
    Cross-validates LLM generated assertions against tool execution results.
    """

    AMOUNT_PATTERN = re.compile(r"[\$₹€£]?\s*(\d+(?:\.\d{1,2})?)")

    def _extract_numbers(self, text: str) -> List[float]:
        matches = self.AMOUNT_PATTERN.findall(text)
        numbers = []
        for m in matches:
            try:
                val = float(m)
                if val > 0:
                    numbers.append(val)
            except ValueError:
                continue
        return numbers

    def validate(
        self,
        response_text: str,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> GuardrailResult:
        if not guardrail_settings.ENABLE_HALLUCINATION_CHECK or not guardrail_settings.ENABLED:
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True, sanitized_content=response_text)

        if not response_text or not response_text.strip():
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True, sanitized_content=response_text)

        if not tool_results:
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True, sanitized_content=response_text)

        hallucinations: List[str] = []
        corrected_text = response_text

        for tool_res in tool_results:
            # Case 1: query_expenses check
            if "query" in tool_res or "data" in tool_res:
                data = tool_res.get("data", [])
                count = tool_res.get("count", len(data))

                if count == 0:
                    # Model should NOT list specific non-zero expenses or claim found records
                    listing_indicators = [
                        r"here (are|is) your (expenses|records)",
                        r"you (spent|have recorded) (a total of )?[\$₹€£]?\s*[1-9]\d*",
                        r"found \d+ expense",
                    ]
                    for ind in listing_indicators:
                        if re.search(ind, response_text, re.IGNORECASE):
                            hallucinations.append(
                                "Model reported expenses when query tool returned 0 records."
                            )
                            corrected_text = (
                                "According to your records, no expenses were found matching that query. "
                                "Feel free to tell me whenever you would like to log a new expense!"
                            )
                            break

            # Case 2: record_expense check
            elif "expense_id" in tool_res and "amount" in tool_res:
                expected_amount = float(tool_res.get("amount", 0.0))

                # If the text explicitly mentions recorded numbers that do not include the recorded amount
                mentioned_nums = self._extract_numbers(response_text)
                if mentioned_nums and expected_amount not in mentioned_nums:
                    hallucinations.append(
                        f"Discrepancy in recorded amount: tool logged {expected_amount}, "
                        f"but model mentioned {mentioned_nums}"
                    )

        if hallucinations:
            return GuardrailResult(
                action=GuardrailAction.MODIFY,
                passed=False,
                violation_type="hallucination_detected",
                reason="; ".join(hallucinations),
                sanitized_content=corrected_text,
                metadata={"hallucination_details": hallucinations},
            )

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            passed=True,
            sanitized_content=response_text,
        )


hallucination_guardrail = HallucinationGuardrail()
