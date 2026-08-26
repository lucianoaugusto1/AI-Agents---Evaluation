from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricResult:
    """A single metric score plus the reasoning that produced it."""

    score: float
    explanation: str = ""
    details: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.score = round(max(0.0, min(1.0, float(self.score))), 4)
