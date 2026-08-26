from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from job_monitor.models import AppConfig, Vacancy, VacancyAssessment


@dataclass(frozen=True, slots=True)
class CandidatePreferenceDecision:
    """Transparent preference decision for a current recommendation."""

    status: str
    rule: str | None = None
    evidence: tuple[str, ...] = ()

    @property
    def retained(self) -> bool:
        return self.status == "RETAINED"


# Keep the Phase 5D domain name available for callers porting generic rules.
OrdinaryOpportunityDecision = CandidatePreferenceDecision


Opportunity = TypeVar("Opportunity", Vacancy, Mapping[str, Any])


def _value(item: Vacancy | Mapping[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (Mapping, list, tuple)):
        return value
    try:
        return json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return fallback


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _contains(text: str, term: str) -> bool:
    normalized_term = _normalized(term)
    return bool(normalized_term) and f" {normalized_term} " in f" {text} "


def _matching_terms(texts: Iterable[str], terms: Iterable[str]) -> tuple[str, ...]:
    normalized_texts = tuple(_normalized(text) for text in texts if str(text).strip())
    matches: list[str] = []
    seen: set[str] = set()
    for term in terms:
        normalized_term = _normalized(term)
        if normalized_term in seen:
            continue
        if any(_contains(text, term) for text in normalized_texts):
            matches.append(term)
            seen.add(normalized_term)
    return tuple(matches)


def _preferences(
    configuration: AppConfig | Mapping[str, Any],
) -> Mapping[str, Any]:
    if isinstance(configuration, AppConfig):
        candidate = _mapping(configuration.candidate)
        return _mapping(candidate.get("ordinary_opportunity_preferences"))
    direct = configuration.get("ordinary_opportunity_preferences")
    if isinstance(direct, Mapping):
        return direct
    return _mapping(
        _mapping(configuration.get("candidate")).get(
            "ordinary_opportunity_preferences"
        )
    )


def _signal_mapping(
    opportunity: Vacancy | Mapping[str, Any],
    assessment: VacancyAssessment | Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if isinstance(assessment, VacancyAssessment):
        signals = assessment.signals
        return {
            "functional_keywords": signals.functional_keywords,
            "subject_matter_keywords": signals.subject_matter_keywords,
            "responsibility_signals": signals.responsibility_signals,
        }
    if isinstance(assessment, Mapping):
        if "signals" in assessment:
            return _mapping(assessment.get("signals"))
        return _mapping(_json(assessment.get("requirement_signals_json"), {}))
    if isinstance(opportunity, Mapping):
        return _mapping(
            _json(opportunity.get("requirement_signals_json"), {})
        )
    return {}


def _evidence_texts(
    opportunity: Vacancy | Mapping[str, Any],
    assessment: VacancyAssessment | Mapping[str, Any] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    signals = _signal_mapping(opportunity, assessment)
    responsibility_signals = _mapping(signals.get("responsibility_signals"))
    responsibilities = [
        excerpt
        for excerpts in responsibility_signals.values()
        for excerpt in _strings(excerpts)
    ]
    cleaned_text = str(_value(opportunity, "cleaned_text", "") or "").strip()
    if cleaned_text:
        responsibilities.append(cleaned_text)
    keywords = list(_strings(signals.get("functional_keywords")))
    keywords.extend(_strings(signals.get("subject_matter_keywords")))
    keywords.extend(str(key) for key in responsibility_signals)
    return tuple(dict.fromkeys(responsibilities)), tuple(dict.fromkeys(keywords))


def _rule_evidence(
    *,
    title_hits: Iterable[str] = (),
    responsibility_hits: Iterable[str] = (),
    keyword_hits: Iterable[str] = (),
    employment_hits: Iterable[str] = (),
    preserve_hits: Iterable[str] = (),
) -> tuple[str, ...]:
    return tuple(
        [f"title: {term}" for term in title_hits]
        + [f"responsibility: {term}" for term in responsibility_hits]
        + [f"keyword: {term}" for term in keyword_hits]
        + [f"employment: {term}" for term in employment_hits]
        + [f"substantive: {term}" for term in preserve_hits]
    )


def candidate_preference_decision(
    opportunity: Vacancy | Mapping[str, Any],
    configuration: AppConfig | Mapping[str, Any],
    *,
    assessment: VacancyAssessment | Mapping[str, Any] | None = None,
) -> CandidatePreferenceDecision:
    """Apply preferences to current recommendations without changing assessment."""

    preferences = _preferences(configuration)
    if not preferences or not bool(preferences.get("enabled", True)):
        return CandidatePreferenceDecision("RETAINED")

    title = str(_value(opportunity, "title", "") or "")
    responsibilities, keywords = _evidence_texts(opportunity, assessment)
    employment = tuple(
        str(_value(opportunity, key, "") or "")
        for key in ("employment_type", "contract_type")
    )

    internship = _mapping(preferences.get("internship"))
    if internship and bool(internship.get("enabled", True)):
        title_hits = _matching_terms((title,), _strings(internship.get("title_terms")))
        employment_hits = _matching_terms(
            employment, _strings(internship.get("employment_terms"))
        )
        if title_hits or employment_hits:
            return CandidatePreferenceDecision(
                str(internship.get("action", "EXCLUDED")).upper(),
                str(internship.get("id", "internship")),
                _rule_evidence(title_hits=title_hits, employment_hits=employment_hits),
            )

    for configured_rule in preferences.get("excluded_role_families", []):
        rule = _mapping(configured_rule)
        if not rule or not bool(rule.get("enabled", True)):
            continue
        title_hits = _matching_terms((title,), _strings(rule.get("title_terms")))
        responsibility_hits = _matching_terms(
            responsibilities, _strings(rule.get("responsibility_terms"))
        )
        keyword_hits = _matching_terms(keywords, _strings(rule.get("keyword_terms")))
        non_title_count = len(set(responsibility_hits + keyword_hits))
        if title_hits or non_title_count >= int(
            rule.get("minimum_non_title_matches", 2)
        ):
            return CandidatePreferenceDecision(
                str(rule.get("action", "EXCLUDED")).upper(),
                str(rule.get("id", "excluded_role_family")),
                _rule_evidence(
                    title_hits=title_hits,
                    responsibility_hits=responsibility_hits,
                    keyword_hits=keyword_hits,
                ),
            )

    for configured_rule in preferences.get("deprioritized_role_families", []):
        rule = _mapping(configured_rule)
        if not rule or not bool(rule.get("enabled", True)):
            continue
        title_hits = _matching_terms((title,), _strings(rule.get("title_terms")))
        responsibility_hits = _matching_terms(
            responsibilities, _strings(rule.get("responsibility_terms"))
        )
        keyword_hits = _matching_terms(keywords, _strings(rule.get("keyword_terms")))
        preserve_hits = _matching_terms(
            (title, *responsibilities, *keywords),
            _strings(rule.get("preserve_terms")),
        )
        supporting_count = len(set(responsibility_hits + keyword_hits))
        total_count = len(set(title_hits + responsibility_hits + keyword_hits))
        preserve_count = len(set(preserve_hits))
        minimum = int(rule.get("minimum_evidence_count", 2))
        dominance_ratio = float(rule.get("low_value_dominance_ratio", 1.0))
        override_minimum = int(rule.get("substantive_override_minimum", 2))
        has_execution_evidence = supporting_count >= 1 and total_count >= minimum
        rule_id = str(rule.get("id", "deprioritized_role_family"))

        if has_execution_evidence and preserve_count >= override_minimum:
            return CandidatePreferenceDecision(
                "RETAINED",
                f"{rule_id}_substantive_override",
                _rule_evidence(
                    title_hits=title_hits,
                    responsibility_hits=responsibility_hits,
                    keyword_hits=keyword_hits,
                    preserve_hits=preserve_hits,
                ),
            )
        if (
            has_execution_evidence
            and total_count > preserve_count * dominance_ratio
        ):
            return CandidatePreferenceDecision(
                str(rule.get("action", "DEPRIORITIZED")).upper(),
                rule_id,
                _rule_evidence(
                    title_hits=title_hits,
                    responsibility_hits=responsibility_hits,
                    keyword_hits=keyword_hits,
                ),
            )

    return CandidatePreferenceDecision("RETAINED")


def ordinary_opportunity_decision(
    opportunity: Vacancy | Mapping[str, Any],
    configuration: AppConfig | Mapping[str, Any],
    *,
    assessment: VacancyAssessment | Mapping[str, Any] | None = None,
) -> OrdinaryOpportunityDecision:
    """Phase 5D-compatible name for the public candidate preference decision."""

    return candidate_preference_decision(
        opportunity, configuration, assessment=assessment
    )


def filter_current_recommendations(
    opportunities: Iterable[Opportunity],
    configuration: AppConfig | Mapping[str, Any],
) -> list[Opportunity]:
    """Filter an existing current-recommendation stream by candidate preference."""

    return [
        opportunity
        for opportunity in opportunities
        if candidate_preference_decision(opportunity, configuration).retained
    ]
