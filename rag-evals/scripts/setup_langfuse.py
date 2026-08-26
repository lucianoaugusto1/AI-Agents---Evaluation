"""Cria no Langfuse o dataset e os code evaluators da atividade de RAG.

    uv run python rag-evals/scripts/setup_langfuse.py --dry-run
    uv run python rag-evals/scripts/setup_langfuse.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from acme_cloud_rag.llm import load_env_file  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evals" / "golden_dataset.jsonl"
EVALUATORS_DIR = ROOT / "evals" / "langfuse_evaluators"
DEFAULT_DATASET_NAME = "acme-cloud-rag-golden-dataset"

EVALUATOR_FILES = {
    "rag-json-contract": "rag_json_contract.py",
    "rag-grounding-rules": "rag_grounding_rules.py",
    "rag-retrieval-quality": "rag_retrieval_quality.py",
}


def load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dataset_item_id(dataset_name: str, case_id: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in dataset_name)
    return f"{normalized}-{case_id.lower()}"


def case_to_dataset_item(case: dict[str, Any], dataset_name: str) -> dict[str, Any]:
    return {
        "id": dataset_item_id(dataset_name, case["id"]),
        "dataset_name": dataset_name,
        "input": {"question": case["question"]},
        "expected_output": {
            "expected_keywords": case["expected_keywords"],
            "expected_document_ids": case["expected_document_ids"],
            "forbidden_claims": case["forbidden_claims"],
            "expect_refusal": case["expect_refusal"],
        },
        "metadata": {
            "case_id": case["id"],
            "category": case["category"],
            "workshop": "acme-cloud-rag-eval-challenge",
            "evaluator_contract": "deterministic-code",
        },
    }


def create_langfuse_client():
    load_env_file()
    from langfuse import get_client

    return get_client()


def create_langfuse_api():
    load_env_file()
    from langfuse.api.client import LangfuseAPI

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")
    if not public_key or not secret_key:
        raise RuntimeError("LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY sao obrigatorias.")

    return LangfuseAPI(
        base_url=base_url,
        x_langfuse_sdk_name="acme-cloud-rag-eval-challenge",
        x_langfuse_sdk_version="0.1.0",
        x_langfuse_public_key=public_key,
        username=public_key,
        password=secret_key,
    )


def ensure_dataset(dataset_name: str, dry_run: bool) -> None:
    cases = load_cases()
    items = [case_to_dataset_item(case, dataset_name) for case in cases]

    if dry_run:
        print(f"[dry-run] dataset={dataset_name} items={len(items)}")
        print(json.dumps(items[0], indent=2, ensure_ascii=False))
        return

    client = create_langfuse_client()
    try:
        client.create_dataset(
            name=dataset_name,
            description="Golden dataset do desafio de RAG do workshop.",
            metadata={
                "source": str(DATASET_PATH.relative_to(ROOT)),
                "cases": len(cases),
                "evaluators": list(EVALUATOR_FILES),
            },
        )
        print(f"dataset criado: {dataset_name}")
    except Exception as exc:
        print(f"dataset ja existe ou nao pode ser criado: {dataset_name} ({exc})")

    for item in items:
        try:
            client.create_dataset_item(**item)
            print(f"item criado: {item['metadata']['case_id']}")
        except Exception as exc:
            print(f"item ignorado: {item['metadata']['case_id']} ({exc})")

    client.flush()


def create_code_evaluators(dry_run: bool, force_new_version: bool) -> bool:
    sources = {
        name: (EVALUATORS_DIR / file_name).read_text(encoding="utf-8")
        for name, file_name in EVALUATOR_FILES.items()
    }

    if dry_run:
        for name, source in sources.items():
            print(f"[dry-run] evaluator={name} chars={len(source)}")
        return True

    from langfuse.api.unstable.commons.types.code_evaluator_source_code_language import (
        CodeEvaluatorSourceCodeLanguage,
    )
    from langfuse.api.unstable.evaluators.types.create_evaluator_request import (
        CreateEvaluatorRequest_Code,
    )

    api = create_langfuse_api()
    ok = True
    existing_names: set[str] = set()
    try:
        existing = api.unstable.evaluators.list(limit=100)
        existing_names = {getattr(item, "name", "") for item in getattr(existing, "data", [])}
    except Exception as exc:
        print(f"nao foi possivel listar evaluators; vou tentar criar todos ({exc})")

    for name, source in sources.items():
        if name in existing_names and not force_new_version:
            print(f"evaluator ignorado: {name} (ja existe; use --force-evaluator-version)")
            continue
        try:
            evaluator = api.unstable.evaluators.create(
                request=CreateEvaluatorRequest_Code(
                    name=name,
                    source_code=source,
                    source_code_language=CodeEvaluatorSourceCodeLanguage.PYTHON,
                )
            )
            print(f"evaluator criado: {name} ({getattr(evaluator, 'id', '<unknown>')})")
        except Exception as exc:
            print(f"nao foi possivel criar o evaluator: {name} ({exc})")
            print(f"fonte disponivel em: {EVALUATORS_DIR / EVALUATOR_FILES[name]}")
            ok = False
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria dataset e code evaluators de RAG no Langfuse.")
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--skip-dataset", action="store_true")
    parser.add_argument("--skip-evaluators", action="store_true")
    parser.add_argument("--force-evaluator-version", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.skip_dataset:
        ensure_dataset(args.dataset_name, dry_run=args.dry_run)
    if not args.skip_evaluators:
        if not create_code_evaluators(dry_run=args.dry_run, force_new_version=args.force_evaluator_version):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
