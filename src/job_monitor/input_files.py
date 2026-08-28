from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from job_monitor.models import Vacancy


def _mapping(value: Any, *, source: Path) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{source} must contain a mapping at the top level")
    return dict(value)


def load_candidate(path: str | Path) -> dict[str, Any]:
    """Load a candidate profile from a YAML file."""

    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        candidate = _mapping(yaml.safe_load(handle), source=source)

    required = ("target_functions", "education_level", "experience_profile")
    missing = [field for field in required if field not in candidate]
    if missing:
        raise ValueError(
            f"{source} is missing required candidate fields: {', '.join(missing)}"
        )
    return candidate


def _optional_date(value: Any, *, field: str, source: Path) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError(
            f"{source}: {field} must use YYYY-MM-DD format"
        ) from error


def load_vacancies(
    path: str | Path,
    *,
    observed_at: datetime | None = None,
) -> list[Vacancy]:
    """Load vacancies from JSON and convert them to public model objects."""

    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{source} must contain a JSON list of vacancies")

    timestamp = observed_at or datetime.now(timezone.utc)
    vacancies: list[Vacancy] = []
    required = ("title", "cleaned_text")
    for index, raw_item in enumerate(payload, start=1):
        item = _mapping(raw_item, source=source)
        missing = [field for field in required if not item.get(field)]
        if missing:
            raise ValueError(
                f"{source}: vacancy {index} is missing: {', '.join(missing)}"
            )

        identifier = str(item.get("vacancy_identifier") or f"CUSTOM-{index:03d}")
        vacancies.append(
            Vacancy(
                institution=str(item.get("institution") or "DEMO"),
                title=str(item["title"]),
                official_url=str(
                    item.get("official_url") or "https://example.com/job"
                ),
                vacancy_identifier=identifier,
                closing_date=_optional_date(
                    item.get("closing_date"), field="closing_date", source=source
                ),
                cleaned_text=str(item["cleaned_text"]),
                first_seen=timestamp,
                last_seen=timestamp,
                department=item.get("department"),
                location=item.get("location"),
                employment_type=item.get("employment_type"),
                contract_type=item.get("contract_type"),
            )
        )
    return vacancies
