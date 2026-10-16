import json
from dataclasses import dataclass
from pathlib import Path

DATASET_DIR = Path(__file__).parent / "datasets"


@dataclass(slots=True)
class EvalCase:
    """评测用例。"""

    question: str
    expected_answer: str
    relevant_keywords: list[str]


def list_datasets() -> list[str]:
    """列出内置评测集名称。"""
    return sorted(path.stem for path in DATASET_DIR.glob("*.jsonl"))


def load_dataset(name: str) -> list[EvalCase]:
    """读取 JSONL 评测集。"""
    path = DATASET_DIR / f"{name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"评测集不存在: {name}")

    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            cases.append(
                EvalCase(
                    question=payload["question"],
                    expected_answer=payload.get("expected_answer", ""),
                    relevant_keywords=list(payload.get("relevant_keywords", [])),
                )
            )
    return cases
