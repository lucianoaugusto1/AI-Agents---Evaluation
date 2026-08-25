import unittest

from evals.run_eval import run


class EvalRunnerTest(unittest.TestCase):
    def test_eval_suite_runs_all_cases(self) -> None:
        results = run(trace_provider="none")
        self.assertEqual(len(results), 10)
        self.assertTrue(all(0 <= result.total <= 1 for result in results))

    def test_baseline_has_intentional_failures(self) -> None:
        results = run(trace_provider="none")
        failing = [result for result in results if result.total < 0.85]
        self.assertGreaterEqual(len(failing), 4)


if __name__ == "__main__":
    unittest.main()
