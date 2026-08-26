from __future__ import annotations

from datetime import datetime, timezone

import pytest

from job_monitor.preference_filter import (
    candidate_preference_decision,
    filter_current_recommendations,
    ordinary_opportunity_decision,
)
from job_monitor.models import Vacancy


PREFERENCES = {
    "enabled": True,
    "internship": {
        "id": "internship",
        "action": "EXCLUDED",
        "title_terms": ["intern", "internship"],
        "employment_terms": ["intern", "internship"],
    },
    "excluded_role_families": [
        {
            "id": "human_resources",
            "action": "EXCLUDED",
            "title_terms": [
                "human resources",
                "HR analyst",
                "HR operations",
                "recruitment",
                "payroll",
            ],
            "responsibility_terms": [
                "recruitment",
                "payroll",
                "employee relations",
            ],
            "keyword_terms": ["human resources", "recruitment", "payroll"],
            "minimum_non_title_matches": 2,
        }
    ],
    "deprioritized_role_families": [
        {
            "id": "administrative_programme_execution",
            "action": "DEPRIORITIZED",
            "title_terms": [
                "administrative assistant",
                "programme assistant",
                "program assistant",
                "programme coordinator",
                "program coordinator",
                "project support",
            ],
            "responsibility_terms": [
                "general administration",
                "administrative support",
                "logistics",
                "procurement",
                "scheduling",
                "budget administration",
                "operational support",
                "meeting coordination",
                "maintain records",
                "day-to-day implementation",
                "work planning",
                "grant management",
                "donor reporting",
                "partner coordination",
                "supervision of consultants",
                "team supervision",
                "monitoring and evaluation",
                "implementation oversight",
            ],
            "keyword_terms": [
                "general administration",
                "logistics",
                "procurement",
                "scheduling",
                "budget administration",
                "operational support",
                "programme execution",
                "program execution",
                "grant management",
                "donor reporting",
                "partner coordination",
                "monitoring and evaluation",
                "implementation oversight",
            ],
            "preserve_terms": [
                "investment",
                "climate finance",
                "policy",
                "financial analysis",
                "risk",
                "regulation",
                "research",
                "technical programme design",
            ],
            "minimum_evidence_count": 2,
            "low_value_dominance_ratio": 1.0,
            "substantive_override_minimum": 2,
        }
    ],
}


def configuration(*, enabled: bool = True) -> dict:
    preferences = dict(PREFERENCES)
    preferences["enabled"] = enabled
    return {"candidate": {"ordinary_opportunity_preferences": preferences}}


def vacancy(**overrides) -> Vacancy:
    values = {
        "institution": "Fictional Development Institute",
        "title": "Policy Analyst",
        "official_url": "https://example.test/jobs/example",
        "vacancy_identifier": "EXAMPLE-001",
        "closing_date": None,
        "cleaned_text": "Conduct financial policy research.",
        "first_seen": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "last_seen": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "location": "Example City",
        "employment_type": "Full-time",
    }
    values.update(overrides)
    return Vacancy(**values)


def test_internship_is_excluded_from_current_recommendations() -> None:
    item = vacancy(title="Research and Project Support Intern")

    decision = candidate_preference_decision(item, configuration())

    assert decision.status == "EXCLUDED"
    assert decision.rule == "internship"
    assert filter_current_recommendations([item], configuration()) == []


def test_internship_employment_type_is_excluded() -> None:
    item = vacancy(title="Research Assistant", employment_type="Internship")

    assert candidate_preference_decision(item, configuration()).rule == "internship"


@pytest.mark.parametrize("title", ["Human Resources Analyst", "Analyst, HR Operations"])
def test_clearly_unrelated_hr_roles_are_excluded(title: str) -> None:
    item = vacancy(title=title)

    decision = candidate_preference_decision(item, configuration())

    assert decision.status == "EXCLUDED"
    assert decision.rule == "human_resources"


def test_hr_family_can_be_excluded_by_multiple_non_title_evidence_terms() -> None:
    item = vacancy(
        title="People Analytics Officer",
        cleaned_text="Manage recruitment pipelines and monthly payroll processing.",
    )

    decision = ordinary_opportunity_decision(item, configuration())

    assert decision.status == "EXCLUDED"
    assert decision.rule == "human_resources"


def test_routine_programme_execution_is_deprioritized() -> None:
    duties = (
        "Coordinate day-to-day implementation, work planning, grant management, "
        "donor reporting, partner coordination, monitoring and evaluation, and "
        "implementation oversight."
    )
    item = vacancy(title="Programme Coordinator", cleaned_text=duties)

    decision = candidate_preference_decision(item, configuration())

    assert decision.status == "DEPRIORITIZED"
    assert decision.rule == "administrative_programme_execution"
    assert "responsibility: day-to-day implementation" in decision.evidence
    assert "responsibility: monitoring and evaluation" in decision.evidence


def test_administrative_title_alone_is_not_enough_to_deprioritize() -> None:
    item = vacancy(
        title="Programme Assistant",
        cleaned_text="Design evidence-based policy for financial regulation.",
    )

    assert candidate_preference_decision(item, configuration()).retained


def test_incidental_substantive_term_does_not_override_execution_evidence() -> None:
    item = vacancy(
        title="Programme Assistant",
        cleaned_text=(
            "Provide general administration, logistics, scheduling, meeting "
            "coordination, and occasional research support."
        ),
    )

    assert candidate_preference_decision(item, configuration()).status == (
        "DEPRIORITIZED"
    )


@pytest.mark.parametrize(
    "substantive_work",
    [
        "climate finance and policy",
        "investment and financial analysis",
        "regulation and risk",
        "research and technical programme design",
    ],
)
def test_substantive_work_explicitly_overrides_programme_execution(
    substantive_work: str,
) -> None:
    item = vacancy(
        title="Programme Coordinator",
        cleaned_text=(
            "Lead day-to-day implementation, grant management, donor reporting, "
            f"and partner coordination. Lead {substantive_work}."
        ),
    )

    decision = candidate_preference_decision(item, configuration())

    assert decision.status == "RETAINED"
    assert decision.rule == (
        "administrative_programme_execution_substantive_override"
    )
    substantive_evidence = [
        item for item in decision.evidence if item.startswith("substantive:")
    ]
    assert len(substantive_evidence) >= 2


def test_location_never_changes_preference_decision() -> None:
    first = vacancy(location="Example City")
    second = vacancy(location="Remote")

    assert candidate_preference_decision(first, configuration()) == (
        candidate_preference_decision(second, configuration())
    )


def test_preferences_can_be_disabled() -> None:
    item = vacancy(title="Research Intern")

    assert candidate_preference_decision(item, configuration(enabled=False)).retained
    assert filter_current_recommendations(
        [item], configuration(enabled=False)
    ) == [item]


def test_filter_does_not_modify_long_term_fields_on_mapping() -> None:
    item = {
        "title": "Climate Research Intern",
        "cleaned_text": "Research climate finance policy.",
        "employment_type": "Internship",
        "career_blueprint_score": 92,
        "career_blueprint_label": "FUTURE TARGET ROLE",
    }
    original_long_term = (
        item["career_blueprint_score"],
        item["career_blueprint_label"],
    )

    decision = candidate_preference_decision(item, configuration())

    assert decision.status == "EXCLUDED"
    assert (
        item["career_blueprint_score"],
        item["career_blueprint_label"],
    ) == original_long_term
