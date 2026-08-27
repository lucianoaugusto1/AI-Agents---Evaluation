from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evals" / "golden_dataset.jsonl"
EVALUATORS_DIR = ROOT / "evals" / "langfuse_evaluators"
DEFAULT_DATASET_NAME = "acme-agents-golden-dataset"

sys.path.insert(0, str(ROOT))

from src.acme_support_ai.config import load_env_file

EVALUATOR_FILES = {
    "acme-json-contract": "json_contract.py",
    "acme-golden-dataset-rules": "golden_dataset_rules.py",
    "acme-business-risk-flags": "business_risk_flags.py",
}

EVALUATION_RULES = {
    "acme-json-contract-live-observations": {
        "evaluator": "acme-json-contract",
        "target": "observation",
    },
    "acme-business-risk-flags-live-observations": {
        "evaluator": "acme-business-risk-flags",
        "target": "observation",
    },
    "acme-golden-dataset-rules-experiments": {
        "evaluator": "acme-golden-dataset-rules",
        "target": "experiment",
    },
}

PRECHECK_ERROR_HINT = (
    "Langfuse rejected enabled=true during code evaluator preflight. "
    "The rule was created disabled; test and enable it in the Langfuse UI, "
    "or verify that code evaluator execution is available for this project."
)


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
    expected_output = {
        "expected_keywords": case["expected_keywords"],
        "required_citations": case["required_citations"],
        "forbidden_claims": case["forbidden_claims"],
        "expect_json": case["expect_json"],
        "expect_escalate": case["expect_escalate"],
    }
    metadata = {
        "case_id": case["id"],
        "category": case["category"],
        "workshop": "acme-agents-eval-challenge",
        "evaluator_contract": "deterministic-code",
    }
    return {
        "id": dataset_item_id(dataset_name, case["id"]),
        "dataset_name": dataset_name,
        "input": {"question": case["question"]},
        "expected_output": expected_output,
        "metadata": metadata,
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
        raise RuntimeError("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required.")

    return LangfuseAPI(
        base_url=base_url,
        x_langfuse_sdk_name="acme-agents-eval-challenge",
        x_langfuse_sdk_version="0.1.0",
        x_langfuse_public_key=public_key,
        username=public_key,
        password=secret_key,
    )


def langfuse_api_credentials() -> tuple[str, str, str]:
    load_env_file()
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")
    if not public_key or not secret_key:
        raise RuntimeError("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required.")
    return base_url, public_key, secret_key


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
            description="Golden dataset do workshop ACME Agents Eval Challenge.",
            metadata={
                "source": str(DATASET_PATH.relative_to(ROOT)),
                "cases": len(cases),
                "evaluators": list(EVALUATOR_FILES),
            },
        )
        print(f"created dataset: {dataset_name}")
    except Exception as exc:
        print(f"dataset already exists or could not be created: {dataset_name} ({exc})")

    for item in items:
        try:
            client.create_dataset_item(**item)
            print(f"created item: {item['metadata']['case_id']}")
        except Exception as exc:
            print(f"skipped item: {item['metadata']['case_id']} ({exc})")

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
    existing_names = set()
    try:
        existing = api.unstable.evaluators.list(limit=100)
        existing_names = {getattr(item, "name", "") for item in getattr(existing, "data", [])}
    except Exception as exc:
        print(f"could not list existing evaluators; will try to create all ({exc})")

    for name, source in sources.items():
        if name in existing_names and not force_new_version:
            print(f"skipped evaluator: {name} (already exists; use --force-evaluator-version to create a new version)")
            continue
        try:
            evaluator = api.unstable.evaluators.create(
                request=CreateEvaluatorRequest_Code(
                    name=name,
                    source_code=source,
                    source_code_language=CodeEvaluatorSourceCodeLanguage.PYTHON,
                )
            )
            evaluator_id = getattr(evaluator, "id", "<unknown>")
            print(f"created evaluator: {name} ({evaluator_id})")
        except Exception as exc:
            print(f"could not create evaluator: {name} ({exc})")
            print(f"source file available at: {EVALUATORS_DIR / EVALUATOR_FILES[name]}")
            ok = False
    return ok


def create_evaluation_rules(dry_run: bool, enable_rules: bool) -> bool:
    if dry_run:
        for name, config in EVALUATION_RULES.items():
            print(
                "[dry-run] evaluation_rule="
                f"{name} evaluator={config['evaluator']} target={config['target']} "
                f"enabled={str(enable_rules).lower()}"
            )
        return True

    import httpx

    api = create_langfuse_api()
    base_url, public_key, secret_key = langfuse_api_credentials()
    ok = True
    existing_by_name = {}
    try:
        existing = api.unstable.evaluation_rules.list(limit=100)
        existing_by_name = {
            getattr(rule, "name", ""): getattr(rule, "id", None)
            for rule in getattr(existing, "data", [])
        }
    except Exception as exc:
        print(f"could not list existing evaluation rules; will try to create all ({exc})")

    for name, config in EVALUATION_RULES.items():
        payload = {
            "name": name,
            "evaluators": [
                {
                    "evaluator": {
                        "name": config["evaluator"],
                        "type": "code",
                    }
                }
            ],
            "target": config["target"],
            "enabled": enable_rules,
            "sampling": 1.0,
        }

        existing_id = existing_by_name.get(name)
        try:
            if existing_id:
                update_payload = {key: value for key, value in payload.items() if key != "name"}
                try:
                    response = httpx.patch(
                        f"{base_url}/api/public/unstable/evaluation-rules/{existing_id}",
                        auth=(public_key, secret_key),
                        json=update_payload,
                        timeout=60,
                    )
                    response.raise_for_status()
                    state = "enabled" if enable_rules else "disabled"
                    print(f"updated evaluation rule {state}: {name} ({existing_id})")
                except httpx.HTTPStatusError as first_exc:
                    if not enable_rules:
                        raise
                    disabled_payload = {**update_payload, "enabled": False}
                    response = httpx.patch(
                        f"{base_url}/api/public/unstable/evaluation-rules/{existing_id}",
                        auth=(public_key, secret_key),
                        json=disabled_payload,
                        timeout=60,
                    )
                    response.raise_for_status()
                    print(f"updated evaluation rule disabled: {name} ({existing_id})")
                    print(f"activation warning: {PRECHECK_ERROR_HINT}")
                    print(f"preflight response: {first_exc.response.text[:500]}")
            else:
                try:
                    response = httpx.post(
                        f"{base_url}/api/public/unstable/evaluation-rules",
                        auth=(public_key, secret_key),
                        json=payload,
                        timeout=60,
                    )
                    response.raise_for_status()
                    rule_id = response.json().get("id", "<unknown>")
                    state = "enabled" if enable_rules else "disabled"
                    print(f"created evaluation rule {state}: {name} ({rule_id})")
                except httpx.HTTPStatusError as first_exc:
                    if not enable_rules:
                        raise
                    disabled_payload = {**payload, "enabled": False}
                    response = httpx.post(
                        f"{base_url}/api/public/unstable/evaluation-rules",
                        auth=(public_key, secret_key),
                        json=disabled_payload,
                        timeout=60,
                    )
                    response.raise_for_status()
                    rule_id = response.json().get("id", "<unknown>")
                    print(f"created evaluation rule disabled: {name} ({rule_id})")
                    print(f"activation warning: {PRECHECK_ERROR_HINT}")
                    print(f"preflight response: {first_exc.response.text[:500]}")
        except Exception as exc:
            print(f"could not create evaluation rule: {name} ({exc})")
            if "response" in locals():
                print(f"response body: {response.text[:1000]}")
            ok = False
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Create ACME golden dataset and code evaluators in Langfuse.")
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--skip-dataset", action="store_true")
    parser.add_argument("--skip-evaluators", action="store_true")
    parser.add_argument("--skip-rules", action="store_true")
    parser.add_argument(
        "--enable-rules",
        action="store_true",
        help=(
            "Try to enable Langfuse server-side evaluation rules during setup. "
            "By default they are created disabled because Dataset Runs use SDK evaluators."
        ),
    )
    parser.add_argument("--force-evaluator-version", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.skip_dataset:
        ensure_dataset(args.dataset_name, dry_run=args.dry_run)
    if not args.skip_evaluators:
        ok = create_code_evaluators(
            dry_run=args.dry_run,
            force_new_version=args.force_evaluator_version,
        )
        if not ok:
            raise SystemExit(1)
    if not args.skip_rules:
        ok = create_evaluation_rules(dry_run=args.dry_run, enable_rules=args.enable_rules)
        if not ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
