from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Protocol


DEFAULT_MODEL = "gpt-5-mini"


@dataclass(frozen=True, slots=True)
class LLMJobAnalysis:
    """Structured job-description fields extracted by an LLM."""

    responsibilities: list[str]
    minimum_experience_years: float | None
    required_skills: list[str]
    preferred_qualifications: list[str]
    education_requirements: list[str]
    long_term_career_signals: list[str]
    ambiguities: list[str]
    model: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResponsesClient(Protocol):
    responses: Any


JOB_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "name": "job_description_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "responsibilities": {
                "type": "array",
                "items": {"type": "string"},
            },
            "minimum_experience_years": {
                "type": ["number", "null"],
            },
            "required_skills": {
                "type": "array",
                "items": {"type": "string"},
            },
            "preferred_qualifications": {
                "type": "array",
                "items": {"type": "string"},
            },
            "education_requirements": {
                "type": "array",
                "items": {"type": "string"},
            },
            "long_term_career_signals": {
                "type": "array",
                "items": {"type": "string"},
            },
            "ambiguities": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "responsibilities",
            "minimum_experience_years",
            "required_skills",
            "preferred_qualifications",
            "education_requirements",
            "long_term_career_signals",
            "ambiguities",
        ],
        "additionalProperties": False,
    },
}


INSTRUCTIONS = """You extract decision-useful facts from job descriptions.

Use only evidence in the supplied vacancy text. Do not infer requirements that
are not stated. Put unclear or conflicting wording in ambiguities. Treat a
qualification as preferred only when the text marks it as preferred, desirable,
or advantageous. Long-term career signals should describe recurring capabilities
or domain exposure the role could help a candidate build, not whether a specific
candidate should apply.
"""


def _default_client() -> ResponsesClient:
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError(
            "The optional OpenAI dependency is not installed. "
            "Run `pip install -e '.[ai]'`."
        ) from error
    return OpenAI()


def extract_job_description_with_llm(
    vacancy_text: str,
    *,
    client: ResponsesClient | None = None,
    model: str | None = None,
) -> LLMJobAnalysis:
    """Extract structured vacancy information using the Responses API.

    The caller may inject a compatible client for testing. Normal use relies on
    ``OPENAI_API_KEY`` and optionally ``OPENAI_MODEL``.
    """

    cleaned_text = vacancy_text.strip()
    if not cleaned_text:
        raise ValueError("vacancy_text must not be empty")

    selected_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    api_client = client or _default_client()
    response = api_client.responses.create(
        model=selected_model,
        instructions=INSTRUCTIONS,
        input=cleaned_text,
        text={"format": JOB_ANALYSIS_SCHEMA},
        store=False,
    )

    try:
        payload = json.loads(response.output_text)
    except (AttributeError, json.JSONDecodeError) as error:
        raise RuntimeError("The model did not return valid structured JSON.") from error

    return LLMJobAnalysis(
        responsibilities=list(payload["responsibilities"]),
        minimum_experience_years=payload["minimum_experience_years"],
        required_skills=list(payload["required_skills"]),
        preferred_qualifications=list(payload["preferred_qualifications"]),
        education_requirements=list(payload["education_requirements"]),
        long_term_career_signals=list(payload["long_term_career_signals"]),
        ambiguities=list(payload["ambiguities"]),
        model=selected_model,
    )
