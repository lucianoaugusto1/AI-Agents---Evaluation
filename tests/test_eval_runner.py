import json
import unittest

from evals.judge import judge_case
from evals.run_eval import load_cases


class EvalRunnerTest(unittest.TestCase):
    def test_golden_dataset_has_expected_cases(self) -> None:
        cases = load_cases()
        self.assertEqual(len(cases), 10)
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


if __name__ == "__main__":
    unittest.main()
