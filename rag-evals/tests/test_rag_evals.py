"""Testes deterministicos: nao chamam LLM e nao dependem de chave de API."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.metrics import context_precision, context_recall  # noqa: E402
from src.rag_evals.documents import build_chunks, load_documents, split_text  # noqa: E402
from src.rag_evals.retriever import BM25Index, tokenize  # noqa: E402

DATASET = ROOT / "evals" / "golden_dataset.jsonl"
REQUIRED_CASE_FIELDS = {
    "id",
    "question",
    "expected_keywords",
    "expected_document_ids",
    "forbidden_claims",
    "expect_refusal",
    "category",
}


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


class DatasetTests(unittest.TestCase):
    def test_cases_have_required_fields(self) -> None:
        for case in load_cases():
            self.assertTrue(REQUIRED_CASE_FIELDS.issubset(case), case["id"])

    def test_case_ids_are_unique(self) -> None:
        ids = [case["id"] for case in load_cases()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_expected_documents_exist(self) -> None:
        known = {doc.doc_id for doc in load_documents()}
        for case in load_cases():
            for doc_id in case["expected_document_ids"]:
                self.assertIn(doc_id, known, case["id"])

    def test_obsolete_document_is_never_expected(self) -> None:
        obsolete = {doc.doc_id for doc in load_documents() if doc.is_obsolete}
        self.assertTrue(obsolete, "o corpus precisa ter ao menos um documento obsoleto")
        for case in load_cases():
            self.assertFalse(obsolete & set(case["expected_document_ids"]), case["id"])


class ChunkingTests(unittest.TestCase):
    def test_split_respects_size(self) -> None:
        pieces = split_text("a" * 1000, size=100, overlap=0)
        self.assertEqual(len(pieces), 10)

    def test_overlap_repeats_content(self) -> None:
        pieces = split_text("abcdefghij", size=5, overlap=2)
        self.assertGreater(len(pieces), 2)

    def test_chunks_carry_document_metadata(self) -> None:
        chunks = build_chunks()
        self.assertTrue(chunks)
        self.assertTrue(all(chunk.chunk_id.startswith(chunk.doc_id) for chunk in chunks))


class RetrieverTests(unittest.TestCase):
    def test_bm25_ranks_the_matching_chunk_first(self) -> None:
        index = BM25Index(build_chunks())
        results = index.search("limite de requisicoes por minuto do plano Pro", top_k=3)
        self.assertTrue(results)
        self.assertIn("limites_api", {item.doc_id for item in results})

    def test_tokenize_keeps_accented_words(self) -> None:
        self.assertIn("politica", tokenize("Politica de reembolso"))


class MetricTests(unittest.TestCase):
    def test_precision_is_order_aware(self) -> None:
        first, _ = context_precision(["a", "b"], ["a"])
        second, _ = context_precision(["b", "a"], ["a"])
        self.assertGreater(first, second)

    def test_recall_counts_expected_documents(self) -> None:
        score, _ = context_recall(["a"], ["a", "b"])
        self.assertEqual(score, 0.5)

    def test_recall_is_one_when_nothing_is_expected(self) -> None:
        score, _ = context_recall(["a"], [])
        self.assertEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()


class JudgeTests(unittest.TestCase):
    """Testa o avaliador com o LLM-as-a-Judge substituido por um stub."""

    def setUp(self) -> None:
        import evals.judge as judge

        self.judge = judge
        self._original = judge.complete_json
        judge.complete_json = lambda system, user, model: {"score": 1.0, "reason": "stub", "unsupported": []}

    def tearDown(self) -> None:
        self.judge.complete_json = self._original

    def _rag(self, raw: str, question: str = "Qual e o prazo de reembolso?"):
        from src.rag_evals.pipeline import RagResult, _parse, build_context
        from src.rag_evals.retriever import retrieve

        chunks = retrieve(question)
        return RagResult(
            question=question,
            retrieved=chunks,
            context=build_context(chunks),
            raw_response=raw,
            parsed=_parse(raw),
        )

    def test_invalid_json_zeroes_the_format_score(self) -> None:
        case = load_cases()[0]
        result = self.judge.judge_case(case, self._rag("o prazo e de 30 dias"))
        self.assertEqual(result.format, 0.0)

    def test_forbidden_claim_zeroes_faithfulness(self) -> None:
        case = next(item for item in load_cases() if item["id"] == "REEMB-001")
        raw = json.dumps(
            {"answer": "O prazo e de 7 dias corridos.", "citations": ["politica_reembolso"],
             "confidence": 0.9, "refused": False}
        )
        result = self.judge.judge_case(case, self._rag(raw))
        self.assertEqual(result.faithfulness, 0.0)
        self.assertTrue(any("proibidas" in problem for problem in result.problems))

    def test_weights_sum_to_one(self) -> None:
        self.assertAlmostEqual(sum(self.judge.WEIGHTS.values()), 1.0)
