import json
import unittest

from evals.judge import judge_case
from evals.run_eval import load_cases
from src.acme_support_ai.tools import (
    calculate_reimbursement_deadline,
    check_remote_work_eligibility,
    check_software_vendor,
    validate_expense_receipt,
)


class EvalRunnerTest(unittest.TestCase):
    def test_golden_dataset_has_expected_cases(self) -> None:
        cases = load_cases()
        self.assertGreaterEqual(len(cases), 16)
        self.assertTrue(all(case["id"] and case["question"] for case in cases))

    def test_judge_scores_valid_json_response(self) -> None:
        case = load_cases()[0]
        payload = {
            "answer": "O prazo atual é de 10 dias corridos após o retorno.",
            "citations": ["finance_current"],
            "confidence": "high",
            "escalate": False,
        }

        result = judge_case(case, json.dumps(payload))

        self.assertTrue(0 <= result.total <= 1)
        self.assertGreater(result.format, 0)

    def test_intentional_stale_tool_rules_are_visible(self) -> None:
        receipt = json.loads(validate_expense_receipt(95, has_receipt=False))
        deadline = json.loads(calculate_reimbursement_deadline("2026-08-03"))
        vendor = json.loads(check_software_vendor("Figma", 450))
        remote_work = json.loads(check_remote_work_eligibility("Brasil", "Portugal", 10))

        self.assertEqual(receipt["threshold_brl"], 120)
        self.assertEqual(deadline["rule_used"], "10 dias corridos")
        self.assertTrue(vendor["auto_approved"])
        self.assertTrue(remote_work["automatic_approval"])


if __name__ == "__main__":
    unittest.main()
