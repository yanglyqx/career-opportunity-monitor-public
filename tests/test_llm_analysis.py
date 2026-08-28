from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from job_monitor.llm_analysis import extract_job_description_with_llm


class FakeResponses:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.request: dict | None = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(output_text=json.dumps(self.payload))


def fake_client(payload: dict):
    return SimpleNamespace(responses=FakeResponses(payload))


def sample_payload() -> dict:
    return {
        "responsibilities": ["Analyse financial-sector policy"],
        "minimum_experience_years": 2,
        "required_skills": ["quantitative analysis"],
        "preferred_qualifications": ["Python knowledge"],
        "education_requirements": ["postgraduate degree in economics or finance"],
        "long_term_career_signals": ["financial regulation exposure"],
        "ambiguities": [],
    }


def test_extracts_structured_job_analysis() -> None:
    client = fake_client(sample_payload())

    result = extract_job_description_with_llm(
        "Analyse policy. Two years of experience preferred.",
        client=client,
        model="test-model",
    )

    assert result.minimum_experience_years == 2
    assert result.required_skills == ["quantitative analysis"]
    assert result.model == "test-model"
    assert client.responses.request["store"] is False
    assert client.responses.request["text"]["format"]["strict"] is True


def test_rejects_empty_vacancy_text() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        extract_job_description_with_llm("  ", client=fake_client(sample_payload()))


def test_rejects_non_json_model_output() -> None:
    client = SimpleNamespace(
        responses=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(output_text="not json")
        )
    )

    with pytest.raises(RuntimeError, match="structured JSON"):
        extract_job_description_with_llm("A valid vacancy", client=client)
