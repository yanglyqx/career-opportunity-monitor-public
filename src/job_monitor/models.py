from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class InstitutionConfig:
    name: str
    short_name: str
    careers_url: str | None
    adapter: str
    enabled: bool
    category: str = ""
    priority: str = ""
    pilot: bool = False
    source_type: str = ""
    check_frequency: str = ""
    notes: str = ""
    manual_review_url: str | None = None
    request_config: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AppConfig:
    config_path: str
    database_path: str
    reports_dir: str
    max_jobs_per_source: int
    institutions: dict[str, InstitutionConfig]
    timezone: str = "UTC"
    candidate: dict[str, Any] | None = None
    hard_filters: dict[str, Any] | None = None
    scoring: dict[str, Any] | None = None
    career_blueprint: dict[str, Any] | None = None
    career_blueprints_dir: str = "career_blueprints"
    notifications: dict[str, Any] | None = None
    notification_previews_dir: str = "notification_previews"
    automation: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class VacancyListing:
    title: str
    official_url: str
    vacancy_identifier: str | None
    closing_date: date | None
    department: str | None = None
    posting_date: date | None = None
    location: str | None = None
    employment_type: str | None = None
    contract_type: str | None = None
    source_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class Vacancy:
    institution: str
    title: str
    official_url: str
    vacancy_identifier: str | None
    closing_date: date | None
    cleaned_text: str | None
    first_seen: datetime
    last_seen: datetime
    detail_fetch_error: str | None = None
    department: str | None = None
    posting_date: date | None = None
    location: str | None = None
    employment_type: str | None = None
    contract_type: str | None = None
    official_source_url: str | None = None
    source_retrieved_at: datetime | None = None
    source_fingerprint: str | None = None
    identifier_kind: str = "official"
    source_parser_version: str | None = None


@dataclass(frozen=True, slots=True)
class RequirementSignals:
    minimum_required_experience_years: float | None
    preferred_experience_years: float | None
    unclear_experience: list[str]
    education_level: str | None
    required_degree_fields: list[str]
    mandatory_professional_qualifications: list[str]
    preferred_professional_qualifications: list[str]
    mandatory_nationality_restrictions: list[str]
    internal_candidates_only: bool
    language_requirements: list[dict[str, Any]]
    work_authorisation_wording: list[str]
    functional_keywords: list[str]
    subject_matter_keywords: list[str]
    management_seniority_indicators: list[str]
    explicit_mandatory_requirements: list[str]
    explicit_preferred_requirements: list[str]
    required_experience_excerpts: list[str]
    preferred_experience_excerpts: list[str]
    current_student_requirements: list[str]
    non_final_year_requirements: list[str]
    local_student_requirements: list[str]
    recent_graduate_requirements: list[str]
    degree_completion_date_requirements: list[str]
    responsibility_signals: dict[str, list[str]]
    deprioritized_function_keywords: list[str]
    early_career_experience_accepted: bool = False
    early_career_experience_excerpts: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class HardFilterDecision:
    rule: str
    supporting_text_excerpt: str
    confidence: float
    automatic: bool
    requires_review: bool
    reason: str
    candidate_profile_field: str | None = None


@dataclass(frozen=True, slots=True)
class VacancyAssessment:
    vacancy_id: int | None
    signals: RequirementSignals
    eligibility_status: str
    hard_filters: list[HardFilterDecision]
    component_scores: dict[str, float]
    current_application_score: float
    current_application_category: str
    seniority_gap: str
    recommended_action: str
    career_blueprint_score: float
    career_blueprint_label: str
    preliminary_analysis: dict[str, Any]
    key_fit_reasons: list[str]
    main_gaps_or_risks: list[str]
    supporting_evidence: list[dict[str, str]]
    analysis_version: str
    text_hash: str
    config_hash: str
    analysed_at: datetime
