from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConclusionMatrixBuilder:
    enabled: bool = True
    rows: list[dict[str, Any]] = field(default_factory=list)

    def add(
        self,
        criterion: str,
        evidence: str,
        evidence_type: str,
        action: str,
        *,
        confidence: float | None = None,
        catalog_match: bool | None = None,
        source_supported: bool = True,
        candidates_before: int | None = None,
        candidates_after: int | None = None,
        warning: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        row = {
            "criterion": criterion,
            "evidence": evidence,
            "evidence_type": evidence_type,
            "action": action,
            "source_supported": source_supported,
        }
        optional = {
            "confidence": round(float(confidence), 4) if confidence is not None else None,
            "catalog_match": catalog_match,
            "candidates_before": candidates_before,
            "candidates_after": candidates_after,
            "warning": warning,
        }
        row.update({key: value for key, value in optional.items() if value is not None})
        self.rows.append(row)

    def export(self) -> list[dict[str, Any]]:
        return list(self.rows) if self.enabled else []
