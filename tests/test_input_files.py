from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from demo import (
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_JOBS_PATH,
    INSTITUTION,
    build_config,
)
from job_monitor.analysis import assess_vacancy
from job_monitor.input_files import load_candidate, load_vacancies


NOW = datetime(2026, 8, 28, tzinfo=timezone.utc)


def test_example_files_preserve_demo_scores() -> None:
    candidate = load_candidate(DEFAULT_CANDIDATE_PATH)
    vacancies = load_vacancies(DEFAULT_JOBS_PATH, observed_at=NOW)
    config = build_config(candidate, config_path=DEFAULT_CANDIDATE_PATH)

    assessments = [
        assess_vacancy(
            vacancy,
            config,
            INSTITUTION,
            vacancy_id=index,
            analysed_at=NOW,
        )
        for index, vacancy in enumerate(vacancies, start=1)
    ]

    assert [item.current_application_score for item in assessments] == [
        68.0,
        76.2,
        56.2,
        43.8,
    ]
    assert [item.career_blueprint_score for item in assessments] == [
        50.5,
        75.0,
        69.5,
        9.0,
    ]


def test_custom_files_load_without_editing_python(tmp_path) -> None:
    candidate_path = tmp_path / "candidate.yaml"
    candidate_path.write_text(
        """target_functions: [risk analysis]
education_level: masters
experience_profile:
  years_full_time: 1
  supported_skills: [Python]
""",
        encoding="utf-8",
    )
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text(
        json.dumps(
            [
                {
                    "title": "Risk Analyst",
                    "cleaned_text": "Analyse financial risk using Python.",
                }
            ]
        ),
        encoding="utf-8",
    )

    candidate = load_candidate(candidate_path)
    vacancies = load_vacancies(jobs_path, observed_at=NOW)

    assert candidate["target_functions"] == ["risk analysis"]
    assert vacancies[0].title == "Risk Analyst"
    assert vacancies[0].vacancy_identifier == "CUSTOM-001"


def test_candidate_file_reports_missing_required_fields(tmp_path) -> None:
    candidate_path = tmp_path / "candidate.yaml"
    candidate_path.write_text("education_level: masters\n", encoding="utf-8")

    with pytest.raises(ValueError, match="target_functions, experience_profile"):
        load_candidate(candidate_path)


def test_jobs_file_reports_missing_job_text(tmp_path) -> None:
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text('[{"title": "Analyst"}]', encoding="utf-8")

    with pytest.raises(ValueError, match="cleaned_text"):
        load_vacancies(jobs_path, observed_at=NOW)
