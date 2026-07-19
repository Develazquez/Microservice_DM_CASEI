from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ComparisonOperator = Literal["lt", "lte", "eq", "gte", "gt", "between"]


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


class InterpretationResponse(BaseModel):
    interpretation: StructuredAcademicQuery
    model: str
    cached: bool = False
