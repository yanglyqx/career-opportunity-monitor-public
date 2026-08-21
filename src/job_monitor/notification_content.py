from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


CONTENT_GENERATION_VERSION = "phase2c-v1"
NOT_STATED = "Not explicitly stated"
BRIEF_FALLBACK = (
    "The official vacancy text does not clearly identify substantive duties; "
    "review the official posting."
)

DEFAULT_TOPIC_CONCEPTS: dict[str, tuple[str, ...]] = {
    "policy": ("policy", "policies", "policy development"),
    "regulation": ("regulation", "regulatory", "supervision"),
    "capital markets": ("capital market", "securities market", "market development"),
    "banking": ("banking", "bank", "monetary authority"),
    "audit": ("audit", "auditor", "assurance"),
    "financial reporting": (
        "financial reporting",
        "accounting standard",
        "financial statement",
    ),
    "fintech": ("fintech", "financial technology", "digital finance"),
    "sustainable finance": (
        "sustainable finance",
        "green finance",
        "sustainability finance",
    ),
    "climate finance": ("climate finance", "climate risk", "climate disclosure"),
    "investment": ("investment", "portfolio", "asset allocation"),
    "risk": ("risk", "risk management", "risk oversight"),
    "compliance": ("compliance", "anti-money laundering", "aml"),
    "data": ("data", "analytics", "database"),
    "research": ("research", "study", "studies"),
    "Greater Bay Area / Mainland China": (
        "greater bay area",
        "mainland china",
        "mainland",
        "gba",
    ),
}

DEFAULT_SKILL_CONCEPTS: dict[str, tuple[str, ...]] = {
    "policy research": ("policy research", "regulatory research", "policy analysis"),
    "quantitative analysis": (
        "quantitative analysis",
        "quantitative research",
        "econometric",
        "statistical analysis",
    ),
    "data analysis": ("data analysis", "data analytics", "analyse data", "analyze data"),
    "drafting": ("drafting", "draft reports", "draft proposals", "writing skills"),
    "consultation analysis": (
        "consultation analysis",
        "public consultation",
        "consultation responses",
    ),
    "stakeholder engagement": (
        "stakeholder engagement",
        "engage with stakeholders",
        "liaise with",
        "collaborate with",
    ),
    "project management": (
        "project management",
        "manage projects",
        "project delivery",
        "lead projects",
    ),
    "financial analysis": (
        "financial analysis",
        "financial modelling",
        "financial modeling",
        "business analysis",
    ),
    "risk assessment": ("risk assessment", "assess risk", "due diligence"),
    "programming": (
        "programming",
        "python",
        "sql",
        "r programming",
        "software development",
    ),
    "visualization": (
        "visualization",
        "visualisation",
        "power bi",
        "tableau",
        "dashboard",
    ),
}

_BOILERPLATE = (
    "equal opportunity",
    "equal opportunities",
    "personal data",
    "application form",
    "apply online",
    "submit your application",
    "only shortlisted",
    "shortlisted candidates",
    "benefits",
    "fringe benefit",
    "remuneration package",
    "salary",
    "privacy",
    "careers page",
    "charged with the responsibility",
    "wholly owned subsidiary",
    "we offer",
    "join us",
)
_ADMINISTRATIVE = (
    "administrative support",
    "filing",
    "schedule meetings",
    "calendar",
    "record maintenance",
    "maintain records",
    "clerical",
    "data entry",
)
_DUTY_VERBS = (
    "analyse",
    "analyze",
    "assess",
    "conduct",
    "contribute",
    "coordinate",
    "develop",
    "draft",
    "drive",
    "engage",
    "evaluate",
    "formulate",
    "implement",
    "investigate",
    "lead",
    "manage",
    "monitor",
    "oversee",
    "prepare",
    "provide",
    "research",
    "review",
    "support",
)
_PRIORITY_DUTY_PHRASES = (
    "research",
    "analysis",
    "analyse",
    "analyze",
    "policy",
    "regulatory",
    "market development",
    "investment",
    "risk",
    "audit",
    "oversight",
    "sustainability",
    "data",
    "consultation",
    "draft",
    "stakeholder",
    "project",
)
_SECTION_HEADINGS = {
    "responsibilities",
    "duties",
    "job responsibilities",
    "key responsibilities",
    "the role",
    "role and responsibilities",
    "requirements",
    "qualifications",
    "job requirements",
    "selection criteria",
}
_TECHNICAL_PHRASES = (
    "python",
    "sql",
    "stata",
    "r programming",
    "power bi",
    "tableau",
    "excel",
    "programming",
    "data visualization",
    "data visualisation",
    "database",
    "software",
    "system",
    "technology",
    "technical",
)


@dataclass(frozen=True, slots=True)
class ExperienceSummary:
    experience_years: str
    relevant_background: str
    academic_qualification: str
    professional_certification: str
    language_requirements: str
    technical_requirements: str


@dataclass(frozen=True, slots=True)
class VacancyNotificationContent:
    brief: str
    responsibilities: tuple[str, ...]
    topic_keywords: tuple[str, ...]
    skill_keywords: tuple[str, ...]
    experience_summary: ExperienceSummary
    content_generation_version: str
    source_vacancy_text_hash: str
    configuration_hash: str


def _row_value(row: Mapping[str, Any], key: str, default: Any = None) -> Any:
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n\u2022-*")


def _segments(text: str) -> list[str]:
    candidates: list[str] = []
    for line in re.split(r"[\r\n]+", text):
        line = _clean(line)
        if not line:
            continue
        parts = re.split(r"(?<=[.!?;])\s+(?=[A-Z(])", line)
        candidates.extend(_clean(part) for part in parts if _clean(part))
    return candidates


def _is_boilerplate(text: str) -> bool:
    lowered = text.casefold()
    return any(phrase in lowered for phrase in _BOILERPLATE)


def _is_heading(text: str) -> bool:
    lowered = text.casefold().rstrip(":")
    return lowered in _SECTION_HEADINGS or (
        len(text.split()) <= 5 and text.endswith(":")
    )


def _has_phrase(text: str, phrase: str) -> bool:
    phrase_pattern = r"[\s\-/]+".join(
        re.escape(part) for part in re.split(r"[\s\-/]+", phrase.casefold())
    )
    return bool(
        re.search(
            rf"(?<![\w]){phrase_pattern}(?![\w])",
            text.casefold(),
        )
    )


def _trim_words(text: str, maximum: int) -> str:
    words = text.split()
    if len(words) <= maximum:
        return text
    return " ".join(words[:maximum]).rstrip(" ,;:-") + "\u2026"


def _responsibility_score(text: str, index: int) -> tuple[float, int]:
    lowered = text.casefold()
    if _is_heading(text) or _is_boilerplate(text) or len(text.split()) < 5:
        return (-1000.0, index)
    verb_hits = sum(
        1
        for verb in _DUTY_VERBS
        if re.search(rf"(?<![\w]){re.escape(verb)}(?:s|ed|ing)?(?![\w])", lowered)
    )
    priority_hits = sum(1 for phrase in _PRIORITY_DUTY_PHRASES if phrase in lowered)
    admin_hits = sum(1 for phrase in _ADMINISTRATIVE if phrase in lowered)
    requirement_penalty = 5 if any(
        phrase in lowered
        for phrase in (
            "degree",
            "years of experience",
            "candidate should",
            "applicant should",
            "proficiency in",
            "good command of",
        )
    ) else 0
    length_penalty = max(0, len(text.split()) - 55) / 20
    return (
        verb_hits * 4 + priority_hits * 3 - admin_hits * 8
        - requirement_penalty - length_penalty,
        index,
    )


def extract_responsibilities(text: str | None) -> tuple[str, ...]:
    segments = _segments(text or "")
    scored = [
        (_responsibility_score(segment, index), segment)
        for index, segment in enumerate(segments)
    ]
    ranked = sorted(scored, key=lambda item: (-item[0][0], item[0][1]))
    selected: list[str] = []
    for (score, _), segment in ranked:
        if score <= 0:
            continue
        normalized = re.sub(r"[^a-z0-9]+", " ", segment.casefold())
        if any(
            normalized in re.sub(r"[^a-z0-9]+", " ", existing.casefold())
            or re.sub(r"[^a-z0-9]+", " ", existing.casefold()) in normalized
            for existing in selected
        ):
            continue
        selected.append(_trim_words(segment, 38))
        if len(selected) == 3:
            break
    return tuple(selected)


def generate_brief(text: str | None, responsibilities: tuple[str, ...]) -> str:
    if not responsibilities:
        return BRIEF_FALLBACK
    chosen = list(responsibilities[:2])
    if len(chosen) == 2:
        first_terms = set(re.findall(r"[a-z]{5,}", chosen[0].casefold()))
        second_terms = set(re.findall(r"[a-z]{5,}", chosen[1].casefold()))
        if len(first_terms & second_terms) >= 5:
            chosen = chosen[:1]
    brief = " ".join(
        item if item.endswith((".", "!", "?", "\u2026")) else item + "."
        for item in chosen
    )
    return _trim_words(brief, 70)


def _concept_dictionary(
    settings: Mapping[str, Any],
    group: str,
    defaults: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    concepts = settings.get("concepts", {})
    configured = concepts.get(group, {}) if isinstance(concepts, Mapping) else {}
    result = dict(defaults)
    if isinstance(configured, Mapping):
        for name, aliases in configured.items():
            if isinstance(aliases, str):
                values = (aliases,)
            elif isinstance(aliases, (list, tuple)):
                values = tuple(str(value) for value in aliases if str(value).strip())
            else:
                continue
            result[str(name)] = values
    return result


def extract_keywords(
    text: str | None,
    settings: Mapping[str, Any] | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    content_settings = settings or {}
    source = (text or "").casefold()

    def ranked(
        concepts: Mapping[str, tuple[str, ...]], maximum: int
    ) -> tuple[str, ...]:
        matches: list[tuple[int, int, int, int, str]] = []
        for order, (name, aliases) in enumerate(concepts.items()):
            count = 0
            first = len(source) + 1
            specificity = 0
            for alias in aliases:
                alias_pattern = r"[\s\-/]+".join(
                    re.escape(part)
                    for part in re.split(r"[\s\-/]+", alias.casefold())
                )
                occurrences = list(
                    re.finditer(
                        rf"(?<![\w]){alias_pattern}(?![\w])",
                        source,
                    )
                )
                if occurrences:
                    count += len(occurrences)
                    first = min(first, occurrences[0].start())
                    specificity = max(specificity, len(alias.split()))
            if count:
                matches.append((-count, -specificity, first, order, name))
        return tuple(item[4] for item in sorted(matches)[:maximum])

    topics = _concept_dictionary(
        content_settings, "topics", DEFAULT_TOPIC_CONCEPTS
    )
    skills = _concept_dictionary(
        content_settings, "skills", DEFAULT_SKILL_CONCEPTS
    )
    return ranked(topics, 5), ranked(skills, 5)


def _json_mapping(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    try:
        parsed = json.loads(str(_row_value(row, key, "{}") or "{}"))
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _excerpt(values: Any, maximum: int = 32) -> str:
    if not isinstance(values, list):
        return NOT_STATED
    cleaned = [_clean(str(value)) for value in values if _clean(str(value))]
    return _trim_words(cleaned[0], maximum) if cleaned else NOT_STATED


def extract_experience_summary(
    row: Mapping[str, Any],
) -> ExperienceSummary:
    signals = _json_mapping(row, "requirement_signals_json")
    required_years = signals.get("minimum_required_experience_years")
    preferred_years = signals.get("preferred_experience_years")
    year_parts = []
    if isinstance(required_years, (int, float)):
        year_parts.append(f"Required: {required_years:g} years")
    if isinstance(preferred_years, (int, float)):
        year_parts.append(f"Preferred: {preferred_years:g} years")

    background = _excerpt(signals.get("required_experience_excerpts"))
    if background == NOT_STATED:
        background = _excerpt(signals.get("preferred_experience_excerpts"))

    education = NOT_STATED
    level = signals.get("education_level")
    fields = signals.get("required_degree_fields")
    if level:
        education = str(level).capitalize()
        if isinstance(fields, list) and fields:
            education += " in " + ", ".join(str(value) for value in fields[:4])

    mandatory = signals.get("mandatory_professional_qualifications")
    preferred = signals.get("preferred_professional_qualifications")
    certifications: list[str] = []
    if isinstance(mandatory, list) and mandatory:
        certifications.append("Required: " + ", ".join(map(str, mandatory)))
    if isinstance(preferred, list) and preferred:
        certifications.append("Preferred: " + ", ".join(map(str, preferred)))

    languages: dict[str, tuple[int, str]] = {}
    language_signals = signals.get("language_requirements", [])
    for item in language_signals if isinstance(language_signals, list) else []:
        if not isinstance(item, Mapping) or not item.get("language"):
            continue
        language = str(item["language"])
        value = language
        status = str(item.get("status", "")).casefold()
        level_value = str(item.get("level", "")).strip()
        if level_value and level_value != "not stated":
            value += f" ({level_value})"
        if status == "preferred":
            value += " [preferred]"
        priority = (
            2 if status == "required" else 1 if status == "preferred" else 0
        ) + (1 if level_value and level_value != "not stated" else 0)
        key = language.casefold()
        if key not in languages or priority > languages[key][0]:
            languages[key] = (priority, value)

    mandatory_requirements = signals.get("explicit_mandatory_requirements", [])
    preferred_requirements = signals.get("explicit_preferred_requirements", [])
    requirements = (
        list(mandatory_requirements)
        if isinstance(mandatory_requirements, list)
        else []
    ) + (
        list(preferred_requirements)
        if isinstance(preferred_requirements, list)
        else []
    )
    technical = next(
        (
            _trim_words(_clean(str(value)), 32)
            for value in requirements
            if any(_has_phrase(str(value), phrase) for phrase in _TECHNICAL_PHRASES)
        ),
        NOT_STATED,
    )
    return ExperienceSummary(
        experience_years="; ".join(year_parts) or NOT_STATED,
        relevant_background=background,
        academic_qualification=education,
        professional_certification="; ".join(certifications) or NOT_STATED,
        language_requirements=(
            ", ".join(value for _, value in languages.values()) or NOT_STATED
        ),
        technical_requirements=technical,
    )


def content_configuration_hash(settings: Mapping[str, Any] | None) -> str:
    relevant = {
        "version": CONTENT_GENERATION_VERSION,
        "concepts": (settings or {}).get("concepts", {}),
    }
    encoded = json.dumps(
        relevant, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def generate_notification_content(
    row: Mapping[str, Any],
    settings: Mapping[str, Any] | None = None,
) -> VacancyNotificationContent:
    text = str(_row_value(row, "cleaned_text", "") or "")
    responsibilities = extract_responsibilities(text)
    topics, skills = extract_keywords(text, settings)
    source_hash = str(_row_value(row, "text_hash", "") or "")
    if not source_hash:
        normalized = re.sub(r"\s+", " ", text).strip()
        source_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    generated = VacancyNotificationContent(
        brief=generate_brief(text, responsibilities),
        responsibilities=responsibilities,
        topic_keywords=topics,
        skill_keywords=skills,
        experience_summary=extract_experience_summary(row),
        content_generation_version=CONTENT_GENERATION_VERSION,
        source_vacancy_text_hash=source_hash,
        configuration_hash=content_configuration_hash(settings),
    )
    if (
        str(_row_value(row, "notification_content_version", "") or "")
        != generated.content_generation_version
        or str(_row_value(row, "notification_source_text_hash", "") or "")
        != generated.source_vacancy_text_hash
        or str(_row_value(row, "notification_configuration_hash", "") or "")
        != generated.configuration_hash
    ):
        return generated
    try:
        cached_responsibilities = tuple(
            str(value)
            for value in json.loads(
                str(_row_value(row, "notification_responsibilities_json", "[]"))
            )
        )
        cached_topics = tuple(
            str(value)
            for value in json.loads(
                str(_row_value(row, "notification_topic_keywords_json", "[]"))
            )
        )
        cached_skills = tuple(
            str(value)
            for value in json.loads(
                str(_row_value(row, "notification_skill_keywords_json", "[]"))
            )
        )
        cached_experience = json.loads(
            str(_row_value(row, "notification_experience_summary_json", "{}"))
        )
        if not isinstance(cached_experience, dict):
            return generated
        experience = ExperienceSummary(
            **{
                field: str(cached_experience[field])
                for field in (
                    "experience_years",
                    "relevant_background",
                    "academic_qualification",
                    "professional_certification",
                    "language_requirements",
                    "technical_requirements",
                )
            }
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return generated
    return VacancyNotificationContent(
        brief=str(_row_value(row, "notification_brief", generated.brief)),
        responsibilities=cached_responsibilities,
        topic_keywords=cached_topics,
        skill_keywords=cached_skills,
        experience_summary=experience,
        content_generation_version=generated.content_generation_version,
        source_vacancy_text_hash=generated.source_vacancy_text_hash,
        configuration_hash=generated.configuration_hash,
    )
