from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GuardrailAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"


@dataclass
class GuardrailResult:
    action: GuardrailAction = GuardrailAction.ALLOW
    passed: bool = True
    violation_type: Optional[str] = None
    reason: Optional[str] = None
    sanitized_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    safe_response: Optional[str] = None


@dataclass
class InputValidationResult:
    passed: bool = True
    blocked: bool = False
    original_text: str = ""
    sanitized_text: str = ""
    violation_type: Optional[str] = None
    violation_reason: Optional[str] = None
    detected_pii: List[str] = field(default_factory=list)
    safe_response: Optional[str] = None
    rate_limited: bool = False
    retry_after: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputValidationResult:
    passed: bool = True
    original_text: str = ""
    sanitized_text: str = ""
    hallucination_detected: bool = False
    policy_violation_detected: bool = False
    format_corrected: bool = False
    disclaimer_added: bool = False
    violation_details: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
