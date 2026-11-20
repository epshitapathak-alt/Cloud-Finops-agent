import re
from typing import Dict, Any, List, Tuple
from backend.app.agents.validator_agent import ValidatorAgent
from backend.app.core.config import settings

class CorrectionAgent:
    def __init__(self):
        self.validator = ValidatorAgent()
        self.max_retries = settings.MAX_CORRECTION_RETRIES

    def run_correction_loop(self, initial_code: str) -> Dict[str, Any]:
        """
        Executes bounded retry loop (max 3 attempts).
        Returns:
            code: corrected terraform code
            status: SUCCESS | FAILED | RETRY_LIMIT_REACHED
            attempts: list of validation attempt records
            error_history: list of errors encountered
        """
        current_code = initial_code
        attempts = []
        error_history = []

        for attempt in range(1, self.max_retries + 1):
            val_result = self.validator.validate_code(current_code, attempt=attempt)
            attempts.append(val_result)

            if val_result["status"] == "SUCCESS":
                return {
                    "code": current_code,
                    "status": "SUCCESS",
                    "attempts": attempts,
                    "error_history": error_history,
                    "retry_count": attempt - 1
                }

            # Failure occurred, capture error
            error_msg = val_result["stderr"] or "Unknown validation failure."
            error_history.append(f"Attempt {attempt}: {error_msg}")

            if attempt < self.max_retries:
                # Attempt self-correction
                current_code = self._correct_code(current_code, error_msg)

        return {
            "code": current_code,
            "status": "RETRY_LIMIT_REACHED",
            "attempts": attempts,
            "error_history": error_history,
            "retry_count": self.max_retries
        }

    def _correct_code(self, code: str, error_msg: str) -> str:
        """Apply algorithmic code patches based on validation errors."""
        corrected = code

        # Patch 1: Unbalanced braces
        open_braces = corrected.count("{")
        close_braces = corrected.count("}")
        if open_braces > close_braces:
            corrected += "\n" + "}" * (open_braces - close_braces)
        elif close_braces > open_braces:
            # remove excess trailing braces
            for _ in range(close_braces - open_braces):
                idx = corrected.rfind("}")
                if idx != -1:
                    corrected = corrected[:idx] + corrected[idx+1:]

        # Patch 2: Unterminated string quotes
        if corrected.count('"') % 2 != 0:
            corrected += '"'

        # Patch 3: Formatting fix
        lines = [line.rstrip() for line in corrected.splitlines()]
        corrected = "\n".join(lines) + "\n"

        return corrected
