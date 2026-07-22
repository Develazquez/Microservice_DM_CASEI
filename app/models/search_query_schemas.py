from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ComparisonOperator = Literal["lt", "lte", "eq", "gte", "gt", "between"]
SearchRetrievalMode = Literal["hybrid", "bm25", "semantic"]


class NumericCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: ComparisonOperator
    value: float
    max_value: float | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "NumericCondition":
        if self.operator == "between":
            if self.max_value is None or self.max_value < self.value:
                raise ValueError("between requiere max_value mayor o igual que value")
        elif self.max_value is not None:
            raise ValueError("max_value solo se permite con operator=between")
        return self


class StructuredAcademicQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_query: str = Field(
        min_length=1,
        max_length=500,
        description="Consulta natural breve en espanol; nunca SQL, operadores ni nombres de columnas.",
    )
    keywords: list[str] = Field(default_factory=list, max_length=8, description="Terminos explicitos para BM25.")
    synonyms: list[str] = Field(default_factory=list, max_length=8, description="Expansion academica conservadora.")
    programa: str | None = None
    perfil: str | None = None
    estatus: str | None = None
    periodo: str | None = None
    cohorte: str | None = None
    sexo: Literal["F", "M"] | None = None
    cluster: int | None = Field(default=None, ge=0)
    promedio: NumericCondition | None = Field(default=None, description="Condicion numerica del promedio, si existe.")
    asistencia: NumericCondition | None = Field(default=None, description="Condicion numerica del porcentaje de asistencia.")
    rezago: NumericCondition | None = Field(default=None, description="Condicion numerica de materias en rezago.")
    materias_reprobadas: NumericCondition | None = Field(default=None, description="Condicion numerica de materias reprobadas.")
    intent: str | None = Field(default=None, max_length=100)
    semantic_concepts: list[str] = Field(default_factory=list, max_length=8)
    negated_concepts: list[str] = Field(default_factory=list, max_length=8)
    sort_preferences: list[str] = Field(default_factory=list, max_length=4)
    filter_candidates: list[str] = Field(default_factory=list, max_length=8)
    ambiguities: list[str] = Field(default_factory=list, max_length=8)
    confidence_by_field: dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("keywords", "synonyms")
    @classmethod
    def clean_terms(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            term = " ".join(str(value).strip().split())
            if term and term.lower() not in {item.lower() for item in cleaned}:
                cleaned.append(term)
        return cleaned[:8]

    @field_validator("normalized_query")
    @classmethod
    def reject_code_like_query(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if any(operator in cleaned for operator in ("<", ">", "=")):
            raise ValueError("normalized_query no puede contener operadores de codigo")
        if "_" in cleaned or re.search(r"\b(select|from|where|join)\b", cleaned, re.IGNORECASE):
            raise ValueError("normalized_query no puede contener SQL ni nombres de columnas")
        return cleaned

    @field_validator("semantic_concepts", "negated_concepts", "sort_preferences", "filter_candidates", "ambiguities")
    @classmethod
    def clean_controlled_values(cls, values: list[str]) -> list[str]:
        cleaned = [" ".join(str(value).strip().split()) for value in values]
        return list(dict.fromkeys(value for value in cleaned if value))

    @field_validator("confidence_by_field")
    @classmethod
    def validate_field_confidences(cls, values: dict[str, float]) -> dict[str, float]:
        if any(float(value) < 0 or float(value) > 1 for value in values.values()):
            raise ValueError("confidence_by_field requiere valores entre 0 y 1")
        return {str(key): float(value) for key, value in values.items()}


class SemanticHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    similarity: float = Field(ge=-1.0, le=1.0)
    allowed_effect: Literal["ranking", "filter_candidate", "qwen_context"] = "ranking"


class QueryCatalogs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programas: list[str] = Field(default_factory=list)
    perfiles: list[str] = Field(default_factory=list)
    estatus: list[str] = Field(default_factory=list)
    periodos: list[str] = Field(default_factory=list)
    cohortes: list[str] = Field(default_factory=list)
    clusters: list[int] = Field(default_factory=list)
    source_columns: list[str] = Field(default_factory=list)
    version: str


class InterpretationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    catalogs: QueryCatalogs
    semantic_hints: list[SemanticHint] = Field(default_factory=list, max_length=8)


class InterpretationResponse(BaseModel):
    interpretation: StructuredAcademicQuery
    model: str
    cached: bool = False


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=256)

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, values: list[str]) -> list[str]:
        cleaned = [" ".join(str(value).strip().split()) for value in values]
        if any(not value for value in cleaned):
            raise ValueError("Los textos para embeddings no pueden estar vacios.")
        return cleaned


class EmbeddingResponse(BaseModel):
    model: str
    embeddings: list[list[float]]
