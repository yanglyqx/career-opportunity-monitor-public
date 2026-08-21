from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from job_monitor.models import (
    AppConfig,
    HardFilterDecision,
    InstitutionConfig,
    RequirementSignals,
    Vacancy,
    VacancyAssessment,
)

ANALYSIS_VERSION = "rule-based-v5a1-experience-precedence-v1"

_PREFERRED_MARKERS = (
    "preferred",
    "preferably",
    "desirable",
    "an advantage",
    "an asset",
    "would be advantageous",
)
_REQUIRED_MARKERS = (
    "required",
    "must ",
    "must be",
    "shall ",
    "mandatory",
    "minimum",
    "at least",
    "need to",
    "needs to",
    "should have",
    "essential",
)
_LANGUAGES = (
    "english",
    "cantonese",
    "mandarin",
    "chinese",
    "french",
    "german",
    "spanish",
    "arabic",
    "japanese",
    "korean",
    "portuguese",
    "russian",
)
_QUALIFICATIONS = (
    "acca",
    "aca",
    "cpa",
    "cfa",
    "frm",
    "cisa",
    "cism",
    "cissp",
    "cia",
    "law society qualification",
    "legal qualification",
    "professional qualification",
    "professional licence",
    "professional license",
    "practising certificate",
    "practicing certificate",
    "solicitor",
    "barrister",
    "ccna",
    "ccnp",
    "aws certified",
    "azure certification",
    "oracle certified",
)
_FUNCTION_TAXONOMY: dict[str, tuple[str, ...]] = {
    "financial regulation": (
        "regulation",
        "regulatory",
        "supervision",
        "enforcement",
        "compliance",
        "banking complaints",
        "listing regulation",
        "listing enforcement",
    ),
    "monetary and financial policy": (
        "monetary policy",
        "financial policy",
        "central bank",
        "exchange fund",
    ),
    "policy research": ("policy research", "research", "policy analysis"),
    "capital markets": (
        "capital market",
        "market development",
        "private market",
        "investment",
        "collateral management",
        "listing policy",
        "listing rules",
        "market structure",
        "trading development",
        "structured products",
        "fixed income",
        "post trade",
        "post-trade",
    ),
    "financial stability": ("financial stability", "systemic risk", "macroprudential"),
    "audit and financial reporting regulation": (
        "audit regulation",
        "auditor regulation",
        "regulation of auditors",
        "audit quality policy",
        "financial reporting regulation",
        "financial reporting requirements",
        "accounting profession regulation",
        "pie audit market",
        "audit market",
    ),
    "financial reporting policy": (
        "financial reporting policy",
        "financial reporting standard",
        "accounting standard",
        "standard-setting",
        "reporting requirements",
    ),
    "regulatory policy": (
        "regulatory policy",
        "regulatory trends",
        "policy position",
        "public consultation",
        "legislative amendment",
        "regulatory consultation",
    ),
    "governance and risk oversight": (
        "governance oversight",
        "risk oversight",
        "quality management system",
        "governance framework",
        "oversight function",
    ),
    "sustainability reporting regulation": (
        "sustainability reporting",
        "sustainability disclosure",
        "sustainability assurance framework",
        "climate disclosure",
    ),
    "disclosure regulation": (
        "disclosure regulation",
        "disclosure requirements",
        "listing rules",
        "financial disclosure",
    ),
    "audit-market policy": (
        "audit market",
        "audit workforce",
        "auditor selection",
        "audit fee",
        "audit quality policy",
    ),
    "regulatory research": (
        "regulatory research",
        "regulatory trends",
        "policy research",
        "consultation analysis",
    ),
    "sustainability and climate finance": (
        "sustainability",
        "climate finance",
        "green finance",
        "climate risk",
    ),
    "sovereign investment": (
        "sovereign investment",
        "reserve management",
        "portfolio",
        "asset allocation",
    ),
    "risk management": (
        "risk management",
        "risk assessment",
        "due diligence",
        "financial crime",
        "anti-money laundering",
        "aml",
        "quantitative risk",
        "risk analytics",
    ),
    "development finance": ("development finance", "economic development"),
    "economic research": (
        "economic research",
        "economics",
        "econometric",
        "market research",
        "market intelligence",
    ),
    "policy data analysis": (
        "data analysis",
        "policy data",
        "statistics",
        "quantitative analysis",
        "commercial data interchange",
    ),
}
_DEPRIORITIZED_TAXONOMY: dict[str, tuple[str, ...]] = {
    "internal audit execution": (
        "conduct internal audit",
        "manage internal audit",
        "internal audit reviews",
        "internal audit testing",
    ),
    "IT audit": (
        "it audit",
        "technology audit",
        "general it controls",
        "application controls",
        "cybersecurity audit",
    ),
    "operational audit execution": (
        "operational audit",
        "operational audits",
    ),
    "external audit practice": (
        "external audit",
        "professional audit firms",
        "audit engagement",
    ),
    "routine audit testing": (
        "audit testing",
        "test controls",
        "substantive testing",
        "journal entry testing",
    ),
    "audit engagement delivery": (
        "deliver audit engagements",
        "perform audit engagements",
        "audit engagement delivery",
    ),
    "unrelated software engineering": (
        "software development",
        "software engineer",
        "application development",
        "programming and coding",
    ),
    "technical engineering": (
        "network engineer",
        "network operation centre",
        "network operations centre",
        "infrastructure reliability",
        "system engineer",
        "systems engineer",
        "systems administration",
        "system administration",
        "system operations",
        "devops",
        "cloud engineer",
        "cloud services",
        "database administrator",
        "database specialist",
        "cybersecurity operations",
        "technical support",
    ),
    "general administrative support": (
        "executive assistant",
        "administrative support",
        "secretarial support",
        "office administration",
        "calendar management",
        "chauffeur",
        "driver",
        "procurement",
        "human resources",
        "hr business partner",
    ),
}

_CRITICAL_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "name": "derivatives pricing",
        "family": "quantitative finance",
        "proficiency": "advanced specialist",
        "phrases": ("derivatives pricing", "derivative pricing", "pricing theory"),
        "adjacent": ("financial analysis", "capital-markets research", "economics"),
    },
    {
        "name": "stochastic calculus",
        "family": "quantitative finance",
        "proficiency": "advanced specialist",
        "phrases": ("stochastic calculus",),
        "adjacent": ("econometrics", "statistical analysis", "economics"),
    },
    {
        "name": "volatility modelling",
        "family": "quantitative finance",
        "proficiency": "advanced specialist",
        "phrases": ("volatility modelling", "volatility modeling"),
        "adjacent": ("econometrics", "statistical analysis"),
    },
    {
        "name": "Black-Scholes methodology",
        "family": "quantitative finance",
        "proficiency": "advanced specialist",
        "phrases": ("black-scholes", "black scholes"),
        "adjacent": ("econometrics", "statistical analysis"),
    },
    {
        "name": "quantitative analytics libraries",
        "family": "quantitative finance",
        "proficiency": "production / expert",
        "phrases": (
            "quantitative analytics libraries",
            "quant analytics libraries",
        ),
        "adjacent": ("python", "data analysis", "data processing"),
    },
    {
        "name": "quantitative model development",
        "family": "quantitative finance",
        "proficiency": "advanced specialist",
        "phrases": (
            "quantitative model development",
            "develop quantitative models",
            "develop quantitative risk models",
            "develop risk models",
            "risk model development",
            "quantitative modelling",
            "quantitative modeling",
        ),
        "adjacent": ("econometrics", "statistical analysis", "python"),
    },
    {
        "name": "model validation",
        "family": "quantitative finance",
        "proficiency": "advanced specialist",
        "phrases": ("model validation", "validate risk models", "model risk validation"),
        "adjacent": ("econometrics", "statistical analysis", "risk assessment"),
    },
    {
        "name": "market risk methodology",
        "family": "quantitative finance",
        "proficiency": "advanced specialist",
        "phrases": ("market risk methodology", "market risk model methodology"),
        "adjacent": ("risk management", "risk assessment", "capital-markets research"),
    },
    {
        "name": "liquidity risk methodology",
        "family": "quantitative finance",
        "proficiency": "advanced specialist",
        "phrases": ("liquidity risk methodology", "liquidity risk model"),
        "adjacent": ("risk management", "risk assessment"),
    },
    {
        "name": "programming",
        "family": "applied analytics",
        "proficiency": "applied",
        "phrases": ("programming", "python"),
        "adjacent": ("data analysis", "data processing"),
    },
    {
        "name": "production-grade software development",
        "family": "advanced software/data",
        "proficiency": "production / expert",
        "phrases": (
            "production-grade software",
            "production software development",
            "software development lifecycle",
            "enterprise software development",
            "deploy code to production",
        ),
        "adjacent": ("python", "programming", "data processing"),
    },
    {
        "name": "systems architecture",
        "family": "advanced software/data",
        "proficiency": "advanced specialist",
        "phrases": ("systems architecture", "system architecture", "solution architecture"),
        "adjacent": ("information systems", "programming"),
    },
    {
        "name": "data engineering pipelines",
        "family": "advanced software/data",
        "proficiency": "production / expert",
        "phrases": (
            "data engineering pipeline",
            "data engineering pipelines",
            "production data pipeline",
            "building data pipelines",
            "data pipelines",
            "etl pipeline",
            "etl development",
        ),
        "adjacent": ("data analysis", "data processing", "python"),
    },
    {
        "name": "data modelling and warehousing",
        "family": "advanced software/data",
        "proficiency": "production / expert",
        "phrases": (
            "data modeling",
            "data modelling",
            "data warehousing",
            "data warehouse",
        ),
        "adjacent": ("data analysis", "data processing", "power bi"),
    },
    {
        "name": "cloud infrastructure",
        "family": "advanced software/data",
        "proficiency": "production / expert",
        "phrases": (
            "cloud infrastructure",
            "cloud engineering",
            "aws",
            "cloud platform",
        ),
        "adjacent": ("programming", "information systems"),
    },
    {
        "name": "DevOps",
        "family": "advanced software/data",
        "proficiency": "production / expert",
        "phrases": ("devops", "ci/cd", "continuous deployment"),
        "adjacent": ("programming", "python"),
    },
    {
        "name": "production ML engineering",
        "family": "advanced software/data",
        "proficiency": "production / expert",
        "phrases": (
            "production ml",
            "machine learning engineering",
            "deploy machine learning models",
            "mlops",
        ),
        "adjacent": ("statistical analysis", "python", "data analysis"),
    },
    {
        "name": "financial-platform delivery",
        "family": "platform delivery",
        "proficiency": "applied",
        "phrases": (
            "platform delivery",
            "system implementation",
            "systems implementation",
            "operational readiness",
            "production readiness",
            "implementation and rollout",
        ),
        "adjacent": ("project management", "stakeholder and institutional exposure"),
    },
    {
        "name": "litigation",
        "family": "legal practice",
        "proficiency": "applied",
        "phrases": ("litigation", "legal proceedings", "court/tribunal cases"),
        "adjacent": ("policy research", "regulatory research"),
    },
    {
        "name": "pleadings and court documents",
        "family": "legal practice",
        "proficiency": "applied",
        "phrases": ("pleadings", "court documents", "document bundles"),
        "adjacent": ("drafting", "research"),
    },
    {
        "name": "witness statements",
        "family": "legal practice",
        "proficiency": "applied",
        "phrases": ("witness statements", "witness statement"),
        "adjacent": ("drafting", "research"),
    },
    {
        "name": "legal advice",
        "family": "legal practice",
        "proficiency": "applied",
        "phrases": ("legal advice", "advise on legal", "provide legal counsel"),
        "adjacent": ("policy analysis", "regulatory policy"),
    },
    {
        "name": "solicitor qualification",
        "family": "legal practice",
        "proficiency": "advanced specialist",
        "phrases": ("qualified solicitor", "solicitor qualification", "admitted solicitor"),
        "adjacent": ("law", "legal studies"),
    },
    {
        "name": "legal executive / paralegal practice",
        "family": "legal practice",
        "proficiency": "applied",
        "phrases": ("legal executive", "paralegal"),
        "adjacent": ("law", "legal studies", "policy research"),
    },
)

_LOW_CAREER_DIRECTION_PHRASES = (
    "outdoor duties",
    "address checks",
    "document delivery",
    "document collection",
    "appointment arrangements",
    "data input",
    "data upload",
    "data download",
    "time logs",
    "operational support",
    "search operations",
    "field activities",
)

_HKEX_TARGET_FUNCTION_ALIASES: dict[str, tuple[str, ...]] = {
    "listing policy": ("listing policy", "listing rules", "listing regime"),
    "listing regulation and enforcement": (
        "listing regulation",
        "listing enforcement",
        "listing compliance",
        "enforcement action",
    ),
    "market development": ("market development", "develop the market"),
    "market structure": ("market structure", "microstructure"),
    "trading development": ("trading development", "trading platform development"),
    "structured products and fixed income": (
        "structured products",
        "fixed income",
        "debt securities",
        "derivatives market",
    ),
    "risk management": ("risk management", "risk framework", "risk methodology"),
    "quantitative risk": ("quantitative risk", "risk model", "risk analytics"),
    "strategy": ("group strategy", "corporate strategy", "strategic planning"),
    "sustainability / carbon / ESG": (
        "carbon market",
        "carbon & esg",
        "carbon and esg",
        "esg product",
        "sustainability strategy",
        "sustainable finance",
    ),
    "economic or market research": (
        "economic research",
        "market research",
        "market intelligence",
        "market analysis",
    ),
    "post-trade market infrastructure strategy": (
        "post trade, market structure",
        "post-trade market structure",
        "post trade strategy",
        "post-trade strategy",
        "clearing strategy",
        "depository strategy",
    ),
}

_HKEX_DEPRIORITIZED_FUNCTION_ALIASES: dict[str, tuple[str, ...]] = {
    "network engineering": (
        "network engineer",
        "network connectivity engineer",
        "network operation centre",
        "network operations centre",
        "network infrastructure",
    ),
    "infrastructure reliability": (
        "infrastructure reliability",
        "site reliability",
        "production reliability",
    ),
    "DevOps": ("devops", "ci/cd", "continuous deployment"),
    "systems administration and operations": (
        "system engineer",
        "systems engineer",
        "system administrator",
        "systems administrator",
        "systems administration",
        "system operations",
        "server administration",
        "computer operator",
        "infrastructure critical service",
        "it service management",
        "technology service operations",
        "workplace technology",
    ),
    "cloud engineering": (
        "cloud engineer",
        "cloud engineering",
        "cloud services",
        "cloud infrastructure",
    ),
    "database administration": (
        "database administrator",
        "database administration",
        "database specialist",
        "oracle database",
    ),
    "software development": (
        "data engineer",
        "software developer",
        "software engineer",
        "software development",
        "application development",
        "systems development",
        "system development",
        "systems analyst",
        "system analyst",
        "java developer",
    ),
    "cybersecurity operations": (
        "information security",
        "application security",
        "identity and access management",
        "network security",
        "security operations centre",
        "security operations center",
        "cybersecurity operations",
        "incident response",
    ),
    "UAT / QA testing": (
        "user acceptance testing",
        "uat execution",
        "uat testing",
        "qa testing",
        "quality assurance testing",
        "test cases",
        "test scripts",
    ),
    "routine clearing operations": (
        "clearing operations",
        "clearing operation",
        "settlement operations",
        "daily settlement",
        "derivative trading operations",
        "derivatives trading operations",
        "trading operations",
    ),
    "routine depository operations": (
        "depository operations",
        "depository operation",
        "custody operations",
        "share registrar operations",
        "nominee services",
        "issuer service operations",
        "participant services",
    ),
    "audit execution": (
        "it audit",
        "internal audit",
        "audit manager",
        "audit testing",
        "control assurance",
    ),
    "HR": (
        "human resources",
        "hr business partner",
        "talent acquisition",
        "employee relations",
    ),
    "administrative support": (
        "executive assistant",
        "administrative support",
        "secretarial support",
        "office administration",
        "calendar management",
        "meeting logistics",
        "procurement",
        "chauffeur",
        "driver",
    ),
}

_HKEX_DUTY_VERBS = (
    "analyse",
    "analyze",
    "assess",
    "design",
    "develop",
    "formulate",
    "lead",
    "own",
    "research",
    "review",
    "shape",
)

_HKEX_MARKET_CONTEXT = (
    "capital market",
    "financial market",
    "securities market",
    "listing",
    "trading",
    "post-trade",
    "post trade",
    "clearing",
    "regulation",
    "regulatory",
    "market structure",
    "strategy",
)
_RESPONSIBILITY_TAXONOMY: dict[str, tuple[str, ...]] = {
    "policy_research": ("policy research", "research", "analyse", "analyze"),
    "regulatory_or_legislative": (
        "regulatory",
        "legislative",
        "public consultation",
        "ordinance",
        "standard-setting",
    ),
    "stakeholder_engagement": (
        "stakeholder",
        "liaise",
        "collaborate",
        "professional bodies",
        "government",
    ),
    "management": ("manage a team", "lead a team", "supervise", "people management"),
    "enforcement": ("enforcement", "discipline", "sanction"),
    "inspection": ("inspect", "inspection", "audit working papers"),
    "investigation": ("investigation", "investigate", "enquiries", "complaints"),
    "legal_drafting": (
        "legal drafting",
        "drafting of legislative",
        "legislative amendments",
    ),
    "accounting_operations": (
        "accounts payable",
        "accounts receivable",
        "bookkeeping",
        "financial accounting operations",
    ),
    "administrative_support": (
        "administrative support",
        "clerical",
        "office administration",
    ),
    "data_analysis": (
        "data analysis",
        "quantitative data",
        "analytical tools",
        "statistics",
    ),
    "ai_or_technology_regulation": (
        "ai in audit",
        "artificial intelligence",
        "modern analytical tools",
        "technology applications",
    ),
    "sustainability": (
        "sustainability reporting",
        "sustainability disclosure",
        "sustainability assurance",
    ),
}
_SUBJECT_KEYWORDS = (
    "banking",
    "financial markets",
    "fintech",
    "financial crime",
    "anti-money laundering",
    "aml",
    "climate",
    "sustainability",
    "investment",
    "audit",
    "risk",
    "compliance",
    "economics",
    "policy",
    "data",
    "research",
)
_SENIORITY_INDICATORS = (
    "executive director",
    "associate director",
    "director",
    "head of",
    "senior manager",
    "manager",
    "team lead",
    "lead a team",
    "supervisory experience",
)


def _sentences(text: str) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        cleaned = " ".join(line.split()).strip(" \t•*-")
        if not cleaned:
            continue
        for sentence in re.split(r"(?<=[.!?;])\s+", cleaned):
            if sentence and sentence not in result:
                result.append(sentence[:500])
    return result


def classify_hkex_primary_function(
    *,
    title: str,
    cleaned_text: str | None,
    department: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Classify HKEX work by evidenced primary duties, not generic finance words."""
    title_lower = title.lower()
    context = "\n".join(
        value for value in (title, department or "", cleaned_text or "") if value
    )
    sentences = _sentences(context)

    target_evidence: list[str] = []
    target_functions: list[str] = []
    for function, aliases in _HKEX_TARGET_FUNCTION_ALIASES.items():
        excerpts = [
            sentence
            for sentence in sentences
            if any(alias in sentence.lower() for alias in aliases)
            and (
                sentence.lower() == title_lower
                or any(verb in sentence.lower() for verb in _HKEX_DUTY_VERBS)
            )
        ]
        if any(alias in title_lower for alias in aliases) and title not in excerpts:
            excerpts.insert(0, title)
        if excerpts:
            target_functions.append(function)
            target_evidence.extend(excerpts)

    # Data/analytics is relevant only when the same evidenced work is tied to
    # markets, regulation, strategy, or substantive risk ownership.
    analytics_evidence = [
        sentence
        for sentence in sentences
        if re.search(
            r"\b(?:data analytics|data analysis|quantitative analysis)\b",
            sentence,
            re.I,
        )
        and any(value in sentence.lower() for value in _HKEX_MARKET_CONTEXT)
        and any(verb in sentence.lower() for verb in _HKEX_DUTY_VERBS)
    ]
    if analytics_evidence:
        target_functions.append("substantive market/regulatory data analytics")
        target_evidence.extend(analytics_evidence)

    deprioritized_evidence: list[str] = []
    deprioritized_functions: list[str] = []
    for function, aliases in _HKEX_DEPRIORITIZED_FUNCTION_ALIASES.items():
        excerpts = [
            sentence
            for sentence in sentences
            if any(alias in sentence.lower() for alias in aliases)
        ]
        if excerpts:
            deprioritized_functions.append(function)
            deprioritized_evidence.extend(excerpts)

    target_evidence = list(dict.fromkeys(target_evidence))[:8]
    deprioritized_evidence = list(dict.fromkeys(deprioritized_evidence))[:8]
    title_has_target = any(
        alias in title_lower
        for aliases in _HKEX_TARGET_FUNCTION_ALIASES.values()
        for alias in aliases
    )
    title_has_deprioritized = any(
        alias in title_lower
        for aliases in _HKEX_DEPRIORITIZED_FUNCTION_ALIASES.values()
        for alias in aliases
    ) or bool(re.search(r"(?:^|[\s,(/-])it(?:$|[\s,)/-])", title_lower))
    if title_has_deprioritized and title not in deprioritized_evidence:
        deprioritized_evidence.insert(0, title)
    dominated = bool(
        deprioritized_evidence
        and (
            title_has_deprioritized
            or not title_has_target
        )
        and (
            title_has_deprioritized
            or
            not target_evidence
            or len(deprioritized_evidence) > len(target_evidence) * 1.5
        )
    )
    classification = (
        "DEPRIORITIZED"
        if dominated
        else "TARGET"
        if target_evidence
        else "NON_TARGET"
    )
    location_lower = (location or "").lower()
    organisational_context = (
        "LONDON_LME"
        if "london" in location_lower or "lme" in context.lower()
        else "SHENZHEN"
        if "shenzhen" in location_lower or "shenzhen" in context.lower()
        else "HONG_KONG"
        if "hong kong" in location_lower or location_lower.startswith("hk-")
        else "OTHER_OR_UNCLEAR"
    )
    return {
        "classification": classification,
        "target_functions": list(dict.fromkeys(target_functions)),
        "deprioritized_functions": deprioritized_functions,
        "target_evidence": target_evidence,
        "deprioritized_evidence": deprioritized_evidence,
        "organisational_context": organisational_context,
    }


def _requirement_section_sentences(text: str) -> set[str]:
    result: set[str] = set()
    in_requirements = False
    stop_headings = {
        "selection process",
        "conditions of service",
        "remuneration",
        "honorarium",
        "how to apply",
        "application",
        "notes",
    }
    for line in text.splitlines():
        cleaned = " ".join(line.split()).strip(" \t•*-")
        lowered = cleaned.lower().rstrip(":")
        if lowered in {"requirements", "entry requirements", "qualifications"}:
            in_requirements = True
            continue
        if in_requirements and lowered in stop_headings:
            in_requirements = False
            continue
        if in_requirements and cleaned:
            result.update(_sentences(cleaned))
    return result


def _requirement_kind(sentence: str) -> str:
    lowered = sentence.lower()
    number = (
        r"(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|"
        r"nine|ten|eleven|twelve)"
    )
    if "experience" in lowered and re.search(
        rf"\b(?:at\s+least|minimum(?:\s+of)?|more\s+than|over)\s+{number}\b",
        lowered,
    ):
        return "required"
    if any(marker in lowered for marker in _PREFERRED_MARKERS):
        return "preferred"
    if any(marker in lowered for marker in _REQUIRED_MARKERS):
        return "required"
    return "unclear"


def _number(value: str) -> float:
    return float(value)


def _experience_signal(sentence: str) -> tuple[float | None, str] | None:
    lowered = sentence.lower().replace("–", "-").replace("—", "-")
    lowered = re.sub(r"[\u2013\u2014]", "-", lowered)
    if "even if" in lowered and "do not meet" in lowered:
        return None
    if "additional experience" in lowered or "remuneration package" in lowered:
        return None
    number_words = {
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
    }
    lowered = re.sub(
        r"\b(" + "|".join(number_words) + r")\b",
        lambda match: number_words[match.group(1)],
        lowered,
    )
    lowered = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*\(\s*\1\s*\)", r"\1", lowered
    )
    if "experience" not in lowered:
        return None
    range_match = re.search(
        r"(?:(at least|minimum(?:\s+of)?|more than|over)\s+)?"
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s+years?",
        lowered,
    )
    single_match = re.search(
        r"(?:(at least|minimum(?:\s+of)?|more than|over)\s+)"
        r"(\d+(?:\.\d+)?)\s*\+?\s+years?",
        lowered,
    )
    plus_match = re.search(r"(\d+(?:\.\d+)?)\s*\+\s*years?", lowered)
    trailing_match = re.search(
        r"(\d+(?:\.\d+)?)\s+years?[^.;]{0,100}\b(required|mandatory|essential)\b",
        lowered,
    )
    if range_match:
        years = _number(range_match.group(2))
        kind = "required" if range_match.group(1) else _requirement_kind(sentence)
        if kind == "unclear":
            kind = "required"
        return years, kind
    if single_match:
        return _number(single_match.group(2)), "required"
    if plus_match:
        return _number(plus_match.group(1)), (
            "preferred" if _requirement_kind(sentence) == "preferred" else "required"
        )
    if trailing_match:
        return _number(trailing_match.group(1)), "required"
    numeric = re.search(r"(\d+(?:\.\d+)?)\s+years?", lowered)
    if numeric:
        kind = _requirement_kind(sentence)
        if kind == "unclear" and (
            "direct hands-on experience" in lowered
            or re.search(r"\bpost[- ]qualification experience\b", lowered)
        ):
            kind = "required"
        return _number(numeric.group(1)), kind
    return None, _requirement_kind(sentence)


def _preferred_higher_experience_years(
    sentence: str, required_years: float | None
) -> float | None:
    if required_years is None:
        return None
    lowered = sentence.casefold()
    number_words = {
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
    }
    lowered = re.sub(
        r"\b(" + "|".join(number_words) + r")\b",
        lambda match: number_words[match.group(1)],
        lowered,
    )
    match = re.search(
        r"\bpreferably\s+(?:at\s+least\s+)?(\d+(?:\.\d+)?)"
        r"(?:\s+years?)?(?:\s*(?:\+|or\s+(?:above|more)))?",
        lowered,
    )
    if not match:
        return None
    preferred_years = _number(match.group(1))
    return preferred_years if preferred_years > required_years else None


def _accepts_early_career_experience(sentence: str) -> bool:
    """Return true only for explicit wording that permits near-zero experience."""
    lowered = sentence.casefold().replace("â€“", "-").replace("â€”", "-")
    lowered = re.sub(r"[\u2013\u2014]", "-", lowered)
    acceptance = (
        r"accepted|welcome|encouraged|may\s+apply|"
        r"(?:will|could)(?:\s+also)?\s+be\s+considered"
    )
    return bool(
        re.search(
            rf"\bfresh\s+graduates?\b[^.;]{{0,160}}\b(?:{acceptance})\b",
            lowered,
        )
        or re.search(
            r"\b(?:candidates?\s+with\s+)?less\s+than\s+"
            r"(?:one|1)[-\s]+year(?:'s)?(?:\s+of)?\s+"
            r"(?:professional\s+|work\s+)?experience\b[^.;]{0,160}"
            rf"\b(?:{acceptance})\b",
            lowered,
        )
        or re.search(
            r"\bno\s+prior\s+(?:professional\s+|work\s+)?experience\s+"
            r"(?:is\s+)?required\b",
            lowered,
        )
        or re.search(
            r"\b(?:prior\s+)?(?:professional\s+|work\s+)?experience\s+"
            r"(?:is\s+)?not\s+required\b",
            lowered,
        )
    )


def _extract_degree_fields(sentence: str) -> list[str]:
    if re.search(
        r"\blaw degree\b|\bdegree of law\b|\blaw graduate\b",
        sentence,
        re.IGNORECASE,
    ):
        return ["law"]
    match = re.search(
        r"(?:degree|bachelor(?:'s)?|master(?:'s)?)\s+(?:degree\s+)?in\s+"
        r"([^.;]{2,160})",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        return []
    value = re.split(
        r"\b(?:with|and at least|plus|is required|is preferred)\b",
        match.group(1),
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return [
        part.strip(" ,")
        for part in re.split(r",|/|\bor\b|\band\b", value, flags=re.IGNORECASE)
        if 2 <= len(part.strip(" ,")) <= 80
    ]


def extract_requirement_signals(
    cleaned_text: str | None,
    *,
    title: str = "",
    target_functions: list[str] | None = None,
    deprioritized_functions: list[str] | None = None,
) -> RequirementSignals:
    text = cleaned_text or ""
    sentences = _sentences(text)
    requirement_section = _requirement_section_sentences(text)
    required_years: list[float] = []
    preferred_years: list[float] = []
    unclear_experience: list[str] = []
    required_excerpts: list[str] = []
    preferred_excerpts: list[str] = []
    mandatory_qualifications: list[str] = []
    preferred_qualifications: list[str] = []
    nationality_restrictions: list[str] = []
    language_requirements: list[dict[str, Any]] = []
    work_authorisation: list[str] = []
    mandatory_requirements: list[str] = []
    preferred_requirements: list[str] = []
    degree_fields: list[str] = []
    education_level: str | None = None
    internal_only = False
    current_student_requirements: list[str] = []
    non_final_year_requirements: list[str] = []
    local_student_requirements: list[str] = []
    recent_graduate_requirements: list[str] = []
    degree_completion_requirements: list[str] = []
    early_career_experience_excerpts: list[str] = []

    for sentence in sentences:
        lowered = sentence.lower()
        if _accepts_early_career_experience(sentence):
            early_career_experience_excerpts.append(sentence)
        kind = _requirement_kind(sentence)
        if kind == "unclear" and sentence in requirement_section:
            kind = "required"
        if kind == "required":
            mandatory_requirements.append(sentence)
        elif kind == "preferred":
            preferred_requirements.append(sentence)

        experience = _experience_signal(sentence)
        if experience:
            years, experience_kind = experience
            if experience_kind == "unclear" and sentence in requirement_section:
                experience_kind = "required"
            if experience_kind == "required":
                if years is not None:
                    required_years.append(years)
                required_excerpts.append(sentence)
                preferred_higher = _preferred_higher_experience_years(
                    sentence, years
                )
                if preferred_higher is not None:
                    preferred_years.append(preferred_higher)
                    if sentence not in preferred_excerpts:
                        preferred_excerpts.append(sentence)
            elif experience_kind == "preferred":
                if years is not None:
                    preferred_years.append(years)
                preferred_excerpts.append(sentence)
            else:
                unclear_experience.append(sentence)

        if re.search(r"\b(phd|doctorate)\b", lowered):
            education_level = "doctorate"
        elif re.search(r"\bmaster(?:'s)?(?: degree)?\b", lowered):
            education_level = education_level or "master"
        elif re.search(r"\b(bachelor(?:'s)?|university degree|degree holder)\b", lowered):
            education_level = education_level or "bachelor"
        elif re.search(r"\b(diploma|associate degree)\b", lowered):
            education_level = education_level or "diploma"
        degree_fields.extend(_extract_degree_fields(sentence))

        for qualification in _QUALIFICATIONS:
            if re.search(rf"\b{re.escape(qualification)}\b", lowered):
                target = (
                    preferred_qualifications
                    if kind == "preferred"
                    else mandatory_qualifications
                )
                if qualification.upper() not in target:
                    target.append(qualification.upper())
        if (
            kind == "required"
            and re.search(
                r"\bmandatory technical certification\b"
                r"|\btechnical certification (?:is )?required\b",
                lowered,
            )
            and "TECHNICAL CERTIFICATION" not in mandatory_qualifications
        ):
            mandatory_qualifications.append("TECHNICAL CERTIFICATION")

        if (
            any(word in lowered for word in ("nationality", "citizen", "nationals of"))
            and kind == "required"
        ):
            nationality_restrictions.append(sentence)
        if re.search(r"\binternal candidates? only\b|\bonly internal applicants?\b", lowered):
            internal_only = True

        for language in _LANGUAGES:
            if re.search(rf"\b{language}\b", lowered):
                language_requirements.append(
                    {
                        "language": language.title(),
                        "status": kind,
                        "level": (
                            "professional command"
                            if any(
                                phrase in lowered
                                for phrase in (
                                    "excellent command",
                                    "professional command",
                                    "fluent",
                                    "proficiency",
                                    "written and spoken",
                                )
                            )
                            else "not stated"
                        ),
                        "excerpt": sentence,
                    }
                )

        if any(
            phrase in lowered
            for phrase in (
                "work authorisation",
                "work authorization",
                "right to work",
                "visa",
                "sponsorship",
                "permanent resident",
            )
        ):
            work_authorisation.append(sentence)

        if kind == "required":
            if re.search(
                r"\b(current(?:ly)?|enrolled).{0,30}(?:university|college|student)"
                r"|\b(?:university|college) students?\b",
                lowered,
            ):
                current_student_requirements.append(sentence)
            if re.search(r"\bnon[- ]final[- ]year\b", lowered):
                non_final_year_requirements.append(sentence)
            if re.search(r"\blocal (?:university )?students?\b", lowered):
                local_student_requirements.append(sentence)
            if re.search(r"\brecent graduates?\b|\bgraduated within\b", lowered):
                recent_graduate_requirements.append(sentence)
            if re.search(
                r"\b(?:complete|completed|completing|obtain).{0,60}"
                r"(?:degree|graduat).{0,40}(?:by|before|no later than)\b",
                lowered,
            ):
                degree_completion_requirements.append(sentence)

    combined = f"{title}\n{text}".lower()
    configured_targets = target_functions or list(_FUNCTION_TAXONOMY)
    functional_keywords: list[str] = []
    for function in configured_targets:
        aliases = _FUNCTION_TAXONOMY.get(function, (function,))
        if any(alias in combined for alias in aliases):
            functional_keywords.append(function)
    subject_keywords = sorted(
        {keyword for keyword in _SUBJECT_KEYWORDS if keyword in combined}
    )
    seniority = [
        indicator for indicator in _SENIORITY_INDICATORS if indicator in combined
    ]
    configured_deprioritized = deprioritized_functions or list(
        _DEPRIORITIZED_TAXONOMY
    )
    deprioritized_keywords = sorted(
        {
            function
            for function in configured_deprioritized
            if any(
                alias in combined
                for alias in _DEPRIORITIZED_TAXONOMY.get(function, (function,))
            )
        }
    )
    if "internal audit" in title.lower():
        deprioritized_keywords = sorted(
            set(deprioritized_keywords) | {"internal audit execution"}
        )
    responsibility_signals = {
        name: [
            sentence
            for sentence in sentences
            if any(alias in sentence.lower() for alias in aliases)
        ][:5]
        for name, aliases in _RESPONSIBILITY_TAXONOMY.items()
    }
    responsibility_signals = {
        name: excerpts
        for name, excerpts in responsibility_signals.items()
        if excerpts
    }

    return RequirementSignals(
        minimum_required_experience_years=(
            max(required_years) if required_years else None
        ),
        preferred_experience_years=max(preferred_years) if preferred_years else None,
        unclear_experience=unclear_experience,
        education_level=education_level,
        required_degree_fields=sorted(set(degree_fields)),
        mandatory_professional_qualifications=mandatory_qualifications,
        preferred_professional_qualifications=preferred_qualifications,
        mandatory_nationality_restrictions=nationality_restrictions,
        internal_candidates_only=internal_only,
        language_requirements=language_requirements,
        work_authorisation_wording=work_authorisation,
        functional_keywords=sorted(set(functional_keywords)),
        subject_matter_keywords=subject_keywords,
        management_seniority_indicators=seniority,
        explicit_mandatory_requirements=mandatory_requirements,
        explicit_preferred_requirements=preferred_requirements,
        required_experience_excerpts=required_excerpts,
        preferred_experience_excerpts=preferred_excerpts,
        current_student_requirements=current_student_requirements,
        non_final_year_requirements=non_final_year_requirements,
        local_student_requirements=local_student_requirements,
        recent_graduate_requirements=recent_graduate_requirements,
        degree_completion_date_requirements=degree_completion_requirements,
        responsibility_signals=responsibility_signals,
        deprioritized_function_keywords=deprioritized_keywords,
        early_career_experience_accepted=bool(early_career_experience_excerpts),
        early_career_experience_excerpts=early_career_experience_excerpts,
    )


def analysis_config_hash(
    config: AppConfig, institution: InstitutionConfig
) -> str:
    payload = {
        "candidate": config.candidate or {},
        "hard_filters": config.hard_filters or {},
        "scoring": config.scoring or {},
        "career_blueprint": config.career_blueprint or {},
        "institution": {
            "short_name": institution.short_name,
            "category": institution.category,
            "priority": institution.priority,
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def vacancy_text_hash(vacancy: Vacancy) -> str:
    payload = "\n".join(
        (
            vacancy.title,
            vacancy.cleaned_text or "",
            vacancy.closing_date.isoformat() if vacancy.closing_date else "",
        )
    )
    normalized = " ".join(payload.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _candidate_language_names(candidate: dict[str, Any]) -> set[str]:
    languages = {str(value).lower() for value in candidate.get("languages", {})}
    if "mandarin" in languages or "cantonese" in languages:
        languages.add("chinese")
    return languages


def _nationality_matches(excerpt: str, nationalities: list[str]) -> bool:
    lowered = excerpt.lower()
    aliases: set[str] = set()
    for nationality in nationalities:
        value = nationality.lower()
        aliases.add(value)
        if value == "china":
            aliases.update(("chinese", "prc"))
    return any(alias in lowered for alias in aliases)


def evaluate_hard_filters(
    vacancy: Vacancy,
    signals: RequirementSignals,
    config: AppConfig,
    *,
    assessed_at: datetime,
) -> tuple[str, list[HardFilterDecision]]:
    candidate = config.candidate or {}
    exclusions = (config.hard_filters or {}).get("exclude_if", {})
    decisions: list[HardFilterDecision] = []

    def add(
        rule: str,
        excerpt: str,
        confidence: float,
        *,
        automatic: bool,
        reason: str,
        candidate_profile_field: str | None = None,
    ) -> None:
        decisions.append(
            HardFilterDecision(
                rule=rule,
                supporting_text_excerpt=excerpt[:500],
                confidence=confidence,
                automatic=automatic,
                requires_review=not automatic,
                reason=reason,
                candidate_profile_field=candidate_profile_field,
            )
        )

    if (
        exclusions.get("internal_candidates_only")
        and signals.internal_candidates_only
    ):
        excerpt = next(
            (
                value
                for value in signals.explicit_mandatory_requirements
                if "internal" in value.lower()
            ),
            "Internal candidates only",
        )
        add(
            "internal_candidates_only",
            excerpt,
            0.99,
            automatic=True,
            reason="The vacancy explicitly limits applications to internal candidates.",
        )

    threshold = 6.0
    years = (
        None
        if signals.early_career_experience_accepted
        else signals.minimum_required_experience_years
    )
    if exclusions.get("minimum_required_experience_years_gt") and years is not None:
        if years > threshold:
            add(
                "minimum_required_experience_years_gt",
                signals.required_experience_excerpts[0],
                0.98,
                automatic=True,
                reason=f"The mandatory minimum of {years:g} years exceeds {threshold:g}.",
            )
    elif exclusions.get("minimum_required_experience_years_gt") and signals.unclear_experience:
        add(
            "minimum_required_experience_years_gt",
            signals.unclear_experience[0],
            0.55,
            automatic=False,
            reason="Experience wording was found but its mandatory minimum is unclear.",
        )

    if (
        exclusions.get("mandatory_nationality_not_met")
        and signals.mandatory_nationality_restrictions
    ):
        excerpt = signals.mandatory_nationality_restrictions[0]
        nationalities = [str(value) for value in candidate.get("nationalities", [])]
        if nationalities and not _nationality_matches(excerpt, nationalities):
            add(
                "mandatory_nationality_not_met",
                excerpt,
                0.95,
                automatic=True,
                reason="The explicit nationality restriction does not match the configured nationality.",
            )
        elif not nationalities:
            add(
                "mandatory_nationality_not_met",
                excerpt,
                0.7,
                automatic=False,
                reason="A mandatory nationality restriction exists but candidate nationality is unavailable.",
            )

    held_qualifications = {
        str(value).lower()
        for value in candidate.get("professional_qualifications", [])
    }
    if (
        exclusions.get("mandatory_unheld_license")
        and signals.mandatory_professional_qualifications
    ):
        missing = [
            value
            for value in signals.mandatory_professional_qualifications
            if value.lower() not in held_qualifications
        ]
        qualification_excerpt = next(
            (
                requirement
                for requirement in signals.explicit_mandatory_requirements
                if any(
                    qualification.lower() in requirement.lower()
                    for qualification in missing
                )
            ),
            ", ".join(missing),
        )
        if missing and "professional_qualifications" in candidate:
            add(
                "mandatory_unheld_license",
                qualification_excerpt,
                0.95,
                automatic=True,
                reason="A mandatory professional qualification is not in the configured holdings.",
            )
        elif missing:
            add(
                "mandatory_unheld_license",
                qualification_excerpt,
                0.65,
                automatic=False,
                reason="A mandatory qualification is stated, but candidate holdings are not configured.",
            )

    required_degree_fields = {
        value.lower() for value in signals.required_degree_fields
    }
    supported_background = {
        str(value).lower()
        for value in candidate.get("education_fields", [])
    }
    if candidate.get("experience_profile", {}).get("accounting_background"):
        supported_background.update(("accounting", "finance"))
    legal_degree_required = any(
        "law" in value or "legal" in value for value in required_degree_fields
    )
    legal_experience_excerpt = next(
        (
            value
            for value in signals.explicit_mandatory_requirements
            if re.search(r"\bparalegal experience\b", value, re.IGNORECASE)
        ),
        None,
    )
    has_legal_background = bool(
        {"law", "legal studies"}.intersection(supported_background)
        or {"solicitor", "barrister"}.intersection(held_qualifications)
        or candidate.get("legal_background")
    )
    if (legal_degree_required or legal_experience_excerpt) and not has_legal_background:
        excerpt = legal_experience_excerpt or next(
            (
                value
                for value in signals.explicit_mandatory_requirements
                if "law" in value.lower() or "legal" in value.lower()
            ),
            "Mandatory law degree or legal background",
        )
        add(
            "mandatory_legal_background_not_met",
            excerpt,
            0.97,
            automatic=True,
            reason="The vacancy explicitly requires legal education or paralegal experience that is not in the configured candidate profile.",
            candidate_profile_field="candidate.education_fields/legal_background",
        )

    technical_fields = {
        value
        for value in required_degree_fields
        if any(
            term in value
            for term in (
                "computer science",
                "information technology",
                "engineering",
                "computer engineering",
            )
        )
    }
    has_technical_degree = any(
        any(
            term in value
            for term in ("computer science", "information technology", "engineering")
        )
        for value in supported_background
    )
    if (
        technical_fields
        and technical_fields == required_degree_fields
        and not has_technical_degree
    ):
        add(
            "mandatory_technical_degree_not_met",
            next(
                (
                    value
                    for value in signals.explicit_mandatory_requirements
                    if any(field in value.lower() for field in technical_fields)
                ),
                "Mandatory engineering or computer science degree",
            ),
            0.95,
            automatic=True,
            reason="The vacancy explicitly requires a technical-specialist degree that is not in the configured candidate profile.",
            candidate_profile_field="candidate.education_fields",
        )

    candidate_languages = _candidate_language_names(candidate)
    if exclusions.get("mandatory_other_language"):
        for requirement in signals.language_requirements:
            language = str(requirement["language"]).lower()
            if (
                requirement["status"] == "required"
                and requirement["level"] == "professional command"
                and language not in candidate_languages
            ):
                add(
                    "mandatory_other_language",
                    str(requirement["excerpt"]),
                    0.95,
                    automatic=True,
                    reason=f"Mandatory professional command of {requirement['language']} is not configured.",
                )
                break

    if (
        exclusions.get("deadline_passed")
        and vacancy.closing_date
        and vacancy.closing_date < assessed_at.date()
    ):
        add(
            "deadline_passed",
            f"Closing date: {vacancy.closing_date.isoformat()}",
            1.0,
            automatic=True,
            reason="The stated application deadline has passed.",
        )

    lowered_title = vacancy.title.lower()
    unrelated_phrases = (
        "software engineer",
        "system development",
        "technical engineer",
        "administrative support",
        "pure sales",
    )
    if (
        exclusions.get("clearly_unrelated_function")
        and any(phrase in lowered_title for phrase in unrelated_phrases)
        and not signals.functional_keywords
    ):
        add(
            "clearly_unrelated_function",
            vacancy.title,
            0.92,
            automatic=True,
            reason="The title clearly describes a configured deprioritized function and no target-function signal was found.",
        )

    mandatory_work_auth = [
        value
        for value in signals.work_authorisation_wording
        if _requirement_kind(value) == "required"
    ]
    if mandatory_work_auth and "work_authorisation" not in candidate:
        add(
            "work_authorisation_unclear",
            mandatory_work_auth[0],
            0.6,
            automatic=False,
            reason="Mandatory work-authorisation wording exists, but candidate status is not configured.",
        )

    current_status = candidate.get("current_status", {})
    if not isinstance(current_status, dict):
        current_status = {}

    def assess_status_requirement(
        requirements: list[str],
        *,
        rule: str,
        field: str,
        missing_reason: str,
        failed_reason: str,
    ) -> None:
        if not requirements:
            return
        profile_path = f"candidate.current_status.{field}"
        if field not in current_status:
            add(
                f"{rule}_unclear",
                requirements[0],
                0.8,
                automatic=False,
                reason=missing_reason,
                candidate_profile_field=profile_path,
            )
        elif not bool(current_status[field]):
            add(
                rule,
                requirements[0],
                0.98,
                automatic=True,
                reason=failed_reason,
                candidate_profile_field=profile_path,
            )

    assess_status_requirement(
        signals.current_student_requirements,
        rule="currently_enrolled_student_required",
        field="currently_enrolled_student",
        missing_reason="Current student status is mandatory but is not configured.",
        failed_reason="The vacancy requires current student status, but the configured candidate is not currently enrolled.",
    )
    assess_status_requirement(
        signals.non_final_year_requirements,
        rule="non_final_year_student_required",
        field="non_final_year_student",
        missing_reason="Non-final-year status is mandatory but is not configured.",
        failed_reason="The vacancy requires non-final-year status, which the configured candidate does not have.",
    )
    assess_status_requirement(
        signals.local_student_requirements,
        rule="local_student_status_required",
        field="local_student",
        missing_reason="Local-student status is mandatory but is not configured.",
        failed_reason="The vacancy requires local-student status, which the configured candidate does not have.",
    )
    assess_status_requirement(
        signals.recent_graduate_requirements,
        rule="recent_graduate_status_required",
        field="recent_graduate",
        missing_reason="Recent-graduate status is mandatory but is not configured.",
        failed_reason="The vacancy requires recent-graduate status, which the configured candidate does not have.",
    )
    assess_status_requirement(
        signals.degree_completion_date_requirements,
        rule="degree_completion_by_date_required",
        field="completed_or_completing_postgraduate_degree",
        missing_reason="Degree-completion status is mandatory but is not configured.",
        failed_reason="The vacancy requires degree completion by a stated date, but the configured completion status is false.",
    )

    if any(decision.automatic for decision in decisions):
        return "INELIGIBLE", decisions
    if any(decision.requires_review for decision in decisions):
        return "UNCLEAR", decisions
    return "ELIGIBLE", decisions


def _seniority_gap(title: str, signals: RequirementSignals) -> str:
    lowered = title.lower()
    if "executive director" in lowered or "associate director" in lowered:
        return "high"
    if "director" in lowered or "head " in lowered:
        return "high"
    if "senior manager" in lowered:
        return "high"
    if (
        lowered.startswith("manager")
        or "assistant manager" in lowered
        or "senior analyst" in lowered
        or "senior " in lowered
    ):
        return "moderate"
    years = (
        0.0
        if signals.early_career_experience_accepted
        else signals.minimum_required_experience_years
    )
    clearly_junior = any(
        value in lowered
        for value in ("assistant,", "assistant (", "analyst", "officer", "student")
    )
    if years is not None and years >= 5:
        return "moderate" if clearly_junior else "high"
    if years is not None and years >= 3 and not clearly_junior:
        return "moderate"
    if any(value in lowered for value in ("assistant", "analyst", "officer", "student")):
        return "low"
    return "unknown"


def _seniority_penalty(title: str, seniority_gap: str) -> float:
    lowered = title.lower()
    if seniority_gap == "high":
        if "executive director" in lowered:
            return 42.0
        if "associate director" in lowered:
            return 34.0
        return 32.0
    if seniority_gap == "moderate":
        if "assistant manager" in lowered:
            return 12.0
        if "senior " in lowered:
            return 14.0
        return 16.0
    return 0.0


_DEFAULT_EXPERIENCE_FEASIBILITY = {
    "early_career": {"classification": "STRONG", "adjustment": 12.0},
    "unknown": {"classification": "NEUTRAL", "adjustment": 0.0},
    "required": {
        "up_to_1": {"classification": "STRONG", "adjustment": 10.0},
        "2": {"classification": "GOOD", "adjustment": 6.0},
        "3": {"classification": "NEUTRAL", "adjustment": 0.0},
        "4": {"classification": "STRETCH", "adjustment": -10.0},
        "5": {"classification": "LOW", "adjustment": -18.0},
        "6_to_7": {"classification": "VERY_LOW", "adjustment": -25.0},
        "8_plus": {"classification": "VERY_LOW", "adjustment": -32.0},
    },
    "preferred": {
        "up_to_1": {"classification": "STRONG", "adjustment": 7.0},
        "2": {"classification": "GOOD", "adjustment": 3.0},
        "3": {"classification": "NEUTRAL", "adjustment": 0.0},
        "4": {"classification": "STRETCH", "adjustment": -3.0},
        "5": {"classification": "STRETCH", "adjustment": -7.0},
        "6_to_7": {"classification": "LOW", "adjustment": -10.0},
        "8_plus": {"classification": "VERY_LOW", "adjustment": -14.0},
    },
}


def _experience_bucket(years: float) -> str:
    if years <= 1:
        return "up_to_1"
    if years < 3:
        return "2"
    if years < 4:
        return "3"
    if years < 5:
        return "4"
    if years < 6:
        return "5"
    if years < 8:
        return "6_to_7"
    return "8_plus"


def classify_experience_feasibility(
    *,
    required_years: float | None,
    preferred_years: float | None,
    early_career_accepted: bool,
    candidate_years: float = 0.0,
    scoring: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify candidate-relative experience fit without affecting blueprint score."""
    configured = (scoring or {}).get("experience_feasibility", {})

    def setting(kind: str, bucket: str | None = None) -> dict[str, Any]:
        default = _DEFAULT_EXPERIENCE_FEASIBILITY[kind]
        override = configured.get(kind, {})
        if bucket is None:
            return {**default, **(override if isinstance(override, dict) else {})}
        default_bucket = default[bucket]
        override_bucket = (
            override.get(bucket, {}) if isinstance(override, dict) else {}
        )
        return {
            **default_bucket,
            **(override_bucket if isinstance(override_bucket, dict) else {}),
        }

    if early_career_accepted:
        selected = setting("early_career")
        return {
            "classification": str(selected["classification"]),
            "adjustment": float(selected["adjustment"]),
            "basis": "EARLY-CAREER",
            "threshold_years": 0.0,
            "candidate_years": candidate_years,
        }
    kind = "required" if required_years is not None else (
        "preferred" if preferred_years is not None else None
    )
    if kind is None:
        selected = setting("unknown")
        return {
            "classification": str(selected["classification"]),
            "adjustment": float(selected["adjustment"]),
            "basis": "NOT_EXPLICITLY_STATED",
            "threshold_years": None,
            "candidate_years": candidate_years,
        }
    threshold = float(required_years if kind == "required" else preferred_years)
    gap = max(0.0, threshold - candidate_years)
    selected = setting(kind, _experience_bucket(gap))
    return {
        "classification": str(selected["classification"]),
        "adjustment": float(selected["adjustment"]),
        "basis": kind.upper(),
        "threshold_years": threshold,
        "candidate_years": candidate_years,
    }


def _experience_feasibility(
    signals: RequirementSignals, config: AppConfig
) -> dict[str, Any]:
    profile = (config.candidate or {}).get("experience_profile", {})
    try:
        candidate_years = float(
            profile.get("full_time_financial_sector_or_regulatory_years", 0)
        )
    except (TypeError, ValueError):
        candidate_years = 0.0
    return classify_experience_feasibility(
        required_years=signals.minimum_required_experience_years,
        preferred_years=signals.preferred_experience_years,
        early_career_accepted=signals.early_career_experience_accepted,
        candidate_years=candidate_years,
        scoring=config.scoring or {},
    )


def _candidate_capability_terms(candidate: dict[str, Any]) -> set[str]:
    profile = candidate.get("experience_profile", {})
    supported = {
        str(value).casefold()
        for value in profile.get("supported_skills", [])
    }
    supported.update(
        str(value).casefold() for value in candidate.get("education_fields", [])
    )
    supported.update(
        str(value).casefold()
        for value in candidate.get("professional_qualifications", [])
    )
    if profile.get("accounting_background"):
        supported.update(("accounting", "financial reporting"))
    expansions = {
        "python": {"programming", "data processing"},
        "data analysis": {"statistical analysis"},
        "economics": {"econometrics"},
        "power bi": {"dashboard development", "business intelligence"},
        "policy analysis": {"policy research", "regulatory research"},
    }
    for term, implied in expansions.items():
        if term in supported:
            supported.update(implied)
    return supported


def _critical_capability_assessment(
    vacancy: Vacancy,
    signals: RequirementSignals,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    text = vacancy.cleaned_text or ""
    lowered_text = text.casefold()
    title = vacancy.title.casefold()
    requirement_text = " ".join(
        signals.explicit_mandatory_requirements
    ).casefold()
    responsibilities_text = lowered_text.split("requirements", maxsplit=1)[0]
    labelled_requirements_text = (
        lowered_text.split("requirements", maxsplit=1)[1]
        if "requirements" in lowered_text
        else ""
    )
    supported = _candidate_capability_terms(candidate)
    entries: list[dict[str, Any]] = []

    for definition in _CRITICAL_CAPABILITIES:
        phrases = tuple(str(value).casefold() for value in definition["phrases"])
        if not any(phrase in lowered_text or phrase in title for phrase in phrases):
            continue
        excerpts = [
            sentence
            for sentence in _sentences(f"{vacancy.title}\n{text}")
            if any(phrase in sentence.casefold() for phrase in phrases)
        ][:3]
        preferred_only = bool(excerpts) and all(
            _requirement_kind(excerpt) == "preferred" for excerpt in excerpts
        )
        appears_in_duties = any(
            phrase in responsibilities_text or phrase in title for phrase in phrases
        )
        explicitly_required = any(phrase in requirement_text for phrase in phrases)
        appears_after_requirements_heading = any(
            phrase in labelled_requirements_text for phrase in phrases
        )
        exact_evidence = definition["name"].casefold() in supported or any(
            phrase in supported for phrase in phrases
        )
        adjacent_evidence = sorted(
            term for term in definition["adjacent"] if term.casefold() in supported
        )
        central = bool(
            appears_in_duties
            or explicitly_required
            or (appears_after_requirements_heading and not preferred_only)
            or any(phrase in title for phrase in phrases)
        )
        if exact_evidence:
            classification = "evidenced capability"
        elif adjacent_evidence and not central:
            classification = "adjacent / transferable capability"
        elif preferred_only and not appears_in_duties:
            classification = "unknown capability"
        else:
            classification = "missing critical capability"
        entries.append(
            {
                "capability": definition["name"],
                "family": definition["family"],
                "required_proficiency": definition["proficiency"],
                "classification": classification,
                "central": central,
                "evidence": excerpts[0] if excerpts else vacancy.title,
                "candidate_evidence": (
                    definition["name"]
                    if exact_evidence
                    else ", ".join(adjacent_evidence)
                    if adjacent_evidence
                    else "No explicit profile evidence"
                ),
            }
        )

    missing = [
        item
        for item in entries
        if item["classification"] == "missing critical capability"
        and item["central"]
    ]
    family_counts: dict[str, int] = {}
    for item in missing:
        family = str(item["family"])
        family_counts[family] = family_counts.get(family, 0) + 1
    central_to_most = any(
        count >= (2 if family == "legal practice" else 3)
        for family, count in family_counts.items()
    )
    major_gap = bool(missing) and not central_to_most
    adjacent_count = sum(
        item["classification"] == "adjacent / transferable capability"
        for item in entries
    )
    capability_fit = max(
        0.0,
        100.0
        - (55.0 if central_to_most else 38.0 if major_gap else 0.0)
        - adjacent_count * 4.0,
    )
    ceiling_reason = (
        "central core specialist capability missing"
        if central_to_most
        else "major learnable capability gap"
        if major_gap
        else None
    )
    return {
        "requirements": entries,
        "evidenced_capabilities": [
            item for item in entries if item["classification"] == "evidenced capability"
        ],
        "adjacent_or_transferable_capabilities": [
            item
            for item in entries
            if item["classification"] == "adjacent / transferable capability"
        ],
        "missing_critical_capabilities": missing,
        "unknown_capabilities": [
            item for item in entries if item["classification"] == "unknown capability"
        ],
        "central_to_most_duties": central_to_most,
        "major_learnable_gap": major_gap,
        "current_score_ceiling_reason": ceiling_reason,
        "capability_fit_score": round(capability_fit, 1),
    }


def _career_direction_fit_score(
    signals: RequirementSignals,
    components: dict[str, float],
    vacancy_text: str | None,
) -> tuple[float, bool]:
    functional = float(components.get("functional_fit", 0.0)) / 25.0
    subject = (
        float(components.get("subject_matter_and_institutional_fit", 0.0))
        / 20.0
    )
    strategic = float(components.get("strategic_value", 0.0)) / 10.0
    score = min(100.0, functional * 50.0 + subject * 30.0 + strategic * 20.0)
    lowered = (vacancy_text or "").casefold()
    execution_hits = sum(
        phrase in lowered for phrase in _LOW_CAREER_DIRECTION_PHRASES
    )
    low_direction = execution_hits >= 3
    if low_direction:
        score = min(score, 39.0)
    return round(score, 1), low_direction


def _current_scores(
    signals: RequirementSignals,
    eligibility: str,
    institution: InstitutionConfig,
    config: AppConfig,
    *,
    substantive_duty: bool,
) -> dict[str, float]:
    weights = (config.scoring or {}).get(
        "weights",
        {
            "eligibility": 30,
            "functional_fit": 25,
            "subject_matter_and_institutional_fit": 20,
            "transferable_skills": 15,
            "strategic_value": 10,
        },
    )
    eligibility_ratio = {"ELIGIBLE": 1.0, "UNCLEAR": 0.6, "INELIGIBLE": 0.0}[
        eligibility
    ]
    candidate = config.candidate or {}
    experience_profile = candidate.get("experience_profile", {})
    function_count = len(signals.functional_keywords)
    deprioritized_count = len(signals.deprioritized_function_keywords)
    functional_ratio = (
        0.9
        if function_count >= 4
        else 0.85
        if function_count >= 2
        else 0.84
        if function_count and substantive_duty
        else 0.7
        if function_count
        else 0.15
    )
    if deprioritized_count:
        functional_ratio = min(functional_ratio, 0.35)
    subject_count = len(signals.subject_matter_keywords)
    institution_points = (
        5.0
        if institution.priority.upper() == "A"
        else 3.0
        if institution.priority.upper() == "B"
        else 1.0
    )
    subject_weight = float(
        weights.get("subject_matter_and_institutional_fit", 20)
    )
    subject_points = min(
        subject_weight,
        institution_points + min(subject_count, 4) * 3.0,
    )

    candidate_languages = _candidate_language_names(candidate)
    required_languages = {
        str(item["language"]).lower()
        for item in signals.language_requirements
        if item["status"] == "required"
    }
    transferable_points = 1.0
    research_functions = {
        "policy research",
        "economic research",
        "policy data analysis",
        "development finance",
    }
    if function_count and experience_profile.get("transferable_experience"):
        transferable_points += 2.0
    if (
        function_count
        and experience_profile.get("academic_and_research_experience") == "strong"
    ):
        transferable_points += 2.0
    if function_count and experience_profile.get("policy_and_data_experience"):
        transferable_points += 1.0
    if (
        experience_profile.get("academic_and_research_experience") == "strong"
        and research_functions.intersection(signals.functional_keywords)
    ):
        transferable_points += 4.0
    if (
        experience_profile.get("policy_and_data_experience")
        and research_functions.intersection(signals.functional_keywords)
    ):
        transferable_points += 3.0
    if required_languages and required_languages.issubset(candidate_languages):
        transferable_points += 2.0
    if (
        experience_profile.get("accounting_background")
        and {
            "audit and financial reporting regulation",
            "financial reporting policy",
            "audit-market policy",
        }.intersection(signals.functional_keywords)
        and not deprioritized_count
    ):
        transferable_points += 2.0
    transferable_points = min(
        float(weights.get("transferable_skills", 15)), transferable_points
    )

    strategic_weight = float(weights.get("strategic_value", 10))
    institution_strategy_points = (
        min(2.0, institution_points)
        if institution.short_name.upper() == "HKEX"
        else min(5.0, institution_points)
    )
    strategic_points = min(
        strategic_weight,
        institution_strategy_points + min(5.0, function_count * 2.0),
    )
    return {
        "eligibility": round(
            float(weights.get("eligibility", 30)) * eligibility_ratio, 1
        ),
        "functional_fit": round(
            float(weights.get("functional_fit", 25)) * functional_ratio, 1
        ),
        "subject_matter_and_institutional_fit": round(subject_points, 1),
        "transferable_skills": round(transferable_points, 1),
        "strategic_value": round(strategic_points, 1),
    }


def _blueprint_score(
    signals: RequirementSignals, institution: InstitutionConfig, title: str
) -> tuple[float, dict[str, float]]:
    institution_alignment = (
        10.0 if institution.priority.upper() == "A" else 7.0
        if institution.priority.upper() == "B"
        else 4.0
    )
    function_alignment = min(35.0, len(signals.functional_keywords) * 12.0)
    work_attractiveness = min(25.0, len(signals.subject_matter_keywords) * 5.0)
    requirement_count = len(signals.explicit_mandatory_requirements) + len(
        signals.explicit_preferred_requirements
    )
    skill_clarity = min(15.0, requirement_count * 2.5)
    model_usefulness = min(
        15.0,
        len(signals.functional_keywords) * 3.0
        + len(signals.required_degree_fields) * 2.0
        + len(signals.mandatory_professional_qualifications) * 2.0,
    )
    lowered_title = title.lower()
    if signals.deprioritized_function_keywords:
        institution_alignment = min(institution_alignment, 5.0)
        function_alignment = min(function_alignment, 8.0)
        work_attractiveness = min(work_attractiveness, 10.0)
        model_usefulness = min(model_usefulness, 6.0)
    if any(
        phrase in lowered_title
        for phrase in (
            "software engineer",
            "system development",
            "technical engineer",
            "administrative support",
            "pure sales",
        )
    ):
        institution_alignment = min(institution_alignment, 5.0)
        function_alignment = min(function_alignment, 5.0)
        work_attractiveness = min(work_attractiveness, 5.0)
        model_usefulness = min(model_usefulness, 5.0)
    parts = {
        "institution_alignment": institution_alignment,
        "function_alignment": function_alignment,
        "work_attractiveness": work_attractiveness,
        "skill_clarity": skill_clarity,
        "model_usefulness": model_usefulness,
    }
    return round(min(100.0, sum(parts.values())), 1), parts


def _category_and_action(
    score: float,
    eligibility: str,
    seniority_gap: str,
    title: str,
    config: AppConfig,
) -> tuple[str, str]:
    thresholds = (config.scoring or {}).get("thresholds", {})
    strong = float(thresholds.get("immediate_alert", 78))
    stretch = float(thresholds.get("retain_and_analyse", 62))
    monitor = float(thresholds.get("discard_below", 40))
    if eligibility == "INELIGIBLE":
        return "NOT SUITABLE", "SKIP"
    if eligibility == "UNCLEAR":
        category = "ELIGIBILITY UNCLEAR"
    elif score >= strong:
        category = "STRONG MATCH"
    elif score >= stretch:
        category = "STRETCH BUT WORTHWHILE"
    elif score >= monitor:
        category = "MONITOR ONLY"
    else:
        category = "NOT SUITABLE"

    lowered_title = title.lower()
    if "executive director" in lowered_title:
        return category, "SKIP"
    if eligibility == "UNCLEAR":
        return category, "REVIEW"
    if seniority_gap == "high" or "associate director" in lowered_title:
        return category, "REVIEW" if score >= stretch else (
            "MONITOR" if score >= monitor else "SKIP"
        )
    if score >= strong and seniority_gap == "low":
        return category, "APPLY"
    if score >= stretch:
        return category, "REVIEW"
    if score >= monitor:
        return category, "MONITOR"
    return category, "SKIP"


def _blueprint_label(
    blueprint_score: float,
    blueprint_parts: dict[str, float],
    current_score: float,
    eligibility: str,
    config: AppConfig,
) -> str:
    threshold = float(
        (config.career_blueprint or {}).get(
            "retain_if_score_at_least",
            (config.scoring or {}).get("thresholds", {}).get("career_blueprint", 55),
        )
    )
    if blueprint_score < threshold:
        return "NOT RETAINED"
    strong = float(
        (config.scoring or {}).get("thresholds", {}).get("immediate_alert", 78)
    )
    if eligibility == "ELIGIBLE" and current_score >= strong:
        return "CLOSE CURRENT MATCH"
    if blueprint_score >= strong and (
        eligibility == "INELIGIBLE" or current_score < strong
    ):
        return "FUTURE TARGET ROLE"
    if blueprint_parts["skill_clarity"] >= 10:
        return "SKILL BUILDING REFERENCE"
    return "CAREER DIRECTION SIGNAL"


def _blueprint_execution_ceiling(
    score: float,
    vacancy_text: str | None,
    signals: RequirementSignals,
    config: AppConfig,
) -> float:
    settings = config.career_blueprint or {}
    concepts = [
        str(value).lower()
        for value in settings.get("deprioritized_concepts", [])
    ]
    if not concepts:
        return score
    text = (vacancy_text or "").lower()
    deprioritized_hits = sum(1 for concept in concepts if concept in text)
    meaningful_verbs = (
        "analyse", "analyze", "assess", "conduct", "develop", "evaluate",
        "formulate", "lead", "research", "regulate", "supervise", "investigate",
    )
    has_substantive_context = bool(
        signals.functional_keywords
        and any(verb in text for verb in meaningful_verbs)
    )
    if deprioritized_hits and not has_substantive_context:
        return min(
            score,
            float(settings.get("deprioritized_blueprint_ceiling", 69)),
        )
    return score


def _contains_substantive_duty(text: str | None) -> bool:
    verbs = (
        "analyse",
        "analyze",
        "assist",
        "collaborate",
        "conduct",
        "coordinate",
        "develop",
        "evaluate",
        "formulate",
        "identify",
        "implement",
        "lead",
        "maintain",
        "manage",
        "monitor",
        "plan",
        "provide",
        "report",
        "review",
        "support",
    )
    verb_pattern = "|".join(verbs)
    for sentence in _sentences(text or ""):
        lowered = sentence.lower()
        if re.match(rf"(?:{verb_pattern})\w*\b", lowered):
            return True
        if re.search(
            rf"\b(?:will|to|responsible for|duties include|including)\s+"
            rf"(?:{verb_pattern})\w*\b",
            lowered,
        ):
            return True
    return False


def _supporting_evidence(
    vacancy: Vacancy,
    signals: RequirementSignals,
    decisions: list[HardFilterDecision],
) -> list[dict[str, str]]:
    sentences = _sentences(vacancy.cleaned_text or "")
    evidence: list[dict[str, str]] = []

    def add(excerpt: str, component: str, concern: str) -> None:
        cleaned = " ".join(excerpt.split())[:260]
        if not cleaned or any(item["excerpt"] == cleaned for item in evidence):
            return
        evidence.append(
            {
                "excerpt": cleaned,
                "component": component,
                "concern": concern,
            }
        )

    if decisions:
        add(
            decisions[0].supporting_text_excerpt,
            "eligibility",
            "current eligibility",
        )
    elif signals.required_experience_excerpts:
        add(
            signals.required_experience_excerpts[0],
            "eligibility",
            "current eligibility",
        )
    elif signals.explicit_mandatory_requirements:
        add(
            signals.explicit_mandatory_requirements[0],
            "eligibility",
            "current eligibility",
        )

    aliases = [
        alias
        for function in signals.functional_keywords
        for alias in _FUNCTION_TAXONOMY.get(function, (function,))
    ]
    duty_sentences = [
        sentence
        for sentence in sentences
        if sentence != vacancy.title and _contains_substantive_duty(sentence)
    ]
    functional_excerpt = next(
        (
            sentence
            for sentence in sentences
            if sentence != vacancy.title
            and any(alias in sentence.lower() for alias in aliases)
            and _contains_substantive_duty(sentence)
        ),
        next(
            (
                sentence
                for sentence in duty_sentences
                if sentence not in signals.required_experience_excerpts
            ),
            next(
                (
                    sentence
                    for sentence in sentences
                    if sentence != vacancy.title
                    and any(alias in sentence.lower() for alias in aliases)
                ),
                "",
            ),
        ),
    )
    if functional_excerpt:
        add(functional_excerpt, "functional_fit", "functional fit")
    if signals.deprioritized_function_keywords:
        deprioritized_aliases = [
            alias
            for function in signals.deprioritized_function_keywords
            for alias in _DEPRIORITIZED_TAXONOMY.get(function, (function,))
        ]
        execution_excerpt = next(
            (
                sentence
                for sentence in sentences
                if any(alias in sentence.lower() for alias in deprioritized_aliases)
            ),
            vacancy.title,
        )
        add(execution_excerpt, "functional_fit", "deprioritized function")

    seniority_excerpt = (
        signals.required_experience_excerpts[0]
        if signals.required_experience_excerpts
        else vacancy.title
    )
    add(seniority_excerpt, "seniority_penalty", "seniority")

    long_term_excerpt = next(
        (
            sentence
            for sentence in sentences
            if sentence != functional_excerpt
            and any(
                keyword in sentence.lower()
                for keyword in signals.subject_matter_keywords
            )
            and _contains_substantive_duty(sentence)
        ),
        next(
            (
                sentence
                for sentence in duty_sentences
                if sentence != functional_excerpt
            ),
            "",
        ),
    )
    if long_term_excerpt:
        add(
            long_term_excerpt,
            "career_blueprint",
            "long-term career value",
        )

    if len(evidence) < 2:
        add(vacancy.title, "functional_fit", "functional fit")
    return evidence[:4]


def _preliminary_analysis(
    vacancy: Vacancy,
    signals: RequirementSignals,
    decisions: list[HardFilterDecision],
    evidence: list[dict[str, str]],
    seniority_gap: str,
    seniority_penalty: float,
    experience_penalty: float,
    eligibility: str,
    candidate: dict[str, Any],
    capability_assessment: dict[str, Any],
    career_direction_fit_score: float,
) -> tuple[dict[str, Any], list[str], list[str]]:
    candidate_matches: list[str] = []
    functions = set(signals.functional_keywords)
    if functions.intersection(
        {"policy research", "economic research", "policy data analysis"}
    ):
        candidate_matches.append(
            "Academic research and UNCTAD policy/data work are transferable to the extracted research and analytical duties."
        )
    if "audit and financial reporting regulation" in functions:
        candidate_matches.append(
            "The accounting background is adjacent, but is not counted as full-time internal-audit experience."
        )
    if signals.deprioritized_function_keywords:
        candidate_matches.append(
            "Accounting knowledge may help interpret controls and reporting, but it is not treated as evidence of interest or experience in audit execution."
        )
    if not candidate_matches:
        candidate_matches.append(
            "Research-assistant and internship experience may transfer, but is not counted as several years of full-time sector experience."
        )

    fits = [
        f"{item['concern']}: “{item['excerpt']}”"
        for item in evidence
        if item["concern"] in {"functional fit", "long-term career value"}
    ]
    gaps = [decision.reason for decision in decisions]
    if seniority_penalty:
        gaps.append(
            f"The {seniority_gap} seniority gap subtracts {seniority_penalty:g} current-score points."
        )
    if experience_penalty:
        gaps.append(
            f"The stated full-time experience minimum subtracts {experience_penalty:g} additional current-score points."
        )
    if signals.mandatory_professional_qualifications:
        gaps.append(
            "Verify mandatory qualifications: "
            + ", ".join(signals.mandatory_professional_qualifications)
            + "."
        )
    if not signals.explicit_mandatory_requirements:
        gaps.append("The rule extractor found limited explicit requirement wording.")
    if signals.deprioritized_function_keywords:
        gaps.append(
            "The duties include configured deprioritized execution work: "
            + ", ".join(signals.deprioritized_function_keywords)
            + "."
        )
    missing_capabilities = capability_assessment["missing_critical_capabilities"]
    if missing_capabilities:
        gaps.append(
            "CORE SKILL GAP: "
            + ", ".join(
                str(item["capability"]) for item in missing_capabilities[:6]
            )
            + "."
        )

    skills = sorted(
        set(
            signals.functional_keywords
            + signals.subject_matter_keywords
            + [
                value.lower()
                for value in signals.mandatory_professional_qualifications
            ]
        )
    )
    attractive_excerpts = [
        item["excerpt"]
        for item in evidence
        if item["concern"] in {"functional fit", "long-term career value"}
    ]
    current_viability = (
        "Not currently viable because a configured hard filter was triggered."
        if eligibility == "INELIGIBLE"
        else "Requires manual eligibility verification before any application decision."
        if eligibility == "UNCLEAR"
        else (
            f"Current viability is constrained by a {seniority_gap} seniority gap"
            + (
                " and a material full-time experience gap."
                if experience_penalty
                else "."
            )
        )
        if seniority_penalty or experience_penalty
        else "No clear hard filter and a low or unknown seniority gap make this comparatively more viable now."
    )
    primary_direction = (
        signals.functional_keywords[0]
        if signals.functional_keywords
        else "policy or regulatory work"
    )
    analysis = {
        "preliminary": True,
        "why_the_work_is_attractive": (
            attractive_excerpts
            or [
                "No specific attractive duty was extracted; manual review is needed."
            ]
        ),
        "which_current_experience_matches": candidate_matches,
        "transferable_experience_already_available": [
            str(value)
            for value in (
                candidate.get("experience_profile", {}).get("supported_skills", [])
            )
        ],
        "target_functions_represented": signals.functional_keywords,
        "deprioritized_functions_detected": signals.deprioritized_function_keywords,
        "which_requirements_are_currently_missing": gaps,
        "skills_to_build": skills[:8],
        "experience_to_seek_in_next_role": [
            f"A full-time analyst or assistant-level role with hands-on {primary_direction} responsibilities and measurable delivery experience."
        ],
        "useful_keywords_for_future_searches": skills[:10],
        "possible_long_term_career_path": [
            f"Build full-time evidence in {primary_direction}, then progress toward roles with broader ownership and institutional responsibility."
        ],
        "current_viability": current_viability,
        "capability_fit": {
            "score": capability_assessment["capability_fit_score"],
            "assessment": capability_assessment,
        },
        "career_direction_fit": {
            "score": career_direction_fit_score,
            "target_functions": signals.functional_keywords,
        },
    }
    return analysis, fits, gaps


def assess_vacancy(
    vacancy: Vacancy,
    config: AppConfig,
    institution: InstitutionConfig,
    *,
    vacancy_id: int | None = None,
    analysed_at: datetime | None = None,
) -> VacancyAssessment:
    timestamp = analysed_at or datetime.now(timezone.utc)
    target_functions = [
        str(value) for value in (config.candidate or {}).get("target_functions", [])
    ]
    deprioritized_functions = [
        str(value)
        for value in (config.candidate or {}).get("deprioritized_functions", [])
    ]
    signals = extract_requirement_signals(
        vacancy.cleaned_text,
        title=vacancy.title,
        target_functions=target_functions,
        deprioritized_functions=deprioritized_functions,
    )
    eligibility, decisions = evaluate_hard_filters(
        vacancy, signals, config, assessed_at=timestamp
    )
    capability_assessment = _critical_capability_assessment(
        vacancy, signals, config.candidate or {}
    )
    missing_legal = [
        item
        for item in capability_assessment["missing_critical_capabilities"]
        if item["family"] == "legal practice"
    ]
    if missing_legal and eligibility == "ELIGIBLE":
        decisions.append(
            HardFilterDecision(
                rule="legal_core_capability_requires_review",
                supporting_text_excerpt=str(missing_legal[0]["evidence"])[:500],
                confidence=0.85,
                automatic=False,
                requires_review=True,
                reason=(
                    "The core duties are legal-practice work, but the candidate "
                    "profile has no explicit legal-practice evidence."
                ),
                candidate_profile_field=(
                    "candidate.education_fields/legal_background/"
                    "experience_profile.supported_skills"
                ),
            )
        )
        eligibility = "UNCLEAR"
    seniority_gap = _seniority_gap(vacancy.title, signals)
    seniority_penalty = _seniority_penalty(vacancy.title, seniority_gap)
    experience_feasibility = _experience_feasibility(signals, config)
    experience_adjustment = float(experience_feasibility["adjustment"])
    substantive_duty = _contains_substantive_duty(vacancy.cleaned_text)
    hkex_function = (
        classify_hkex_primary_function(
            title=vacancy.title,
            cleaned_text=vacancy.cleaned_text,
            department=vacancy.department,
            location=vacancy.location,
        )
        if institution.short_name.upper() == "HKEX"
        else None
    )
    components = _current_scores(
        signals,
        eligibility,
        institution,
        config,
        substantive_duty=substantive_duty,
    )
    career_direction_fit_score, low_career_direction = (
        _career_direction_fit_score(
            signals, components, vacancy.cleaned_text
        )
    )
    if hkex_function and hkex_function["classification"] == "TARGET":
        components["functional_fit"] = max(20.0, components["functional_fit"])
        components["strategic_value"] = max(7.0, components["strategic_value"])
    components["seniority_penalty"] = -seniority_penalty
    components["full_time_experience_gap_penalty"] = min(
        0.0, experience_adjustment
    )
    components["experience_feasibility_boost"] = max(
        0.0, experience_adjustment
    )
    if hkex_function:
        context = hkex_function["organisational_context"]
        location_penalty = (
            4.0
            if context == "LONDON_LME"
            else 6.0
            if context == "SHENZHEN"
            else 0.0
        )
        components["hkex_location_context_adjustment"] = -location_penalty
    current_score = round(
        min(
            float((config.scoring or {}).get("scale", 100)),
            max(0.0, sum(components.values())),
        ),
        1,
    )
    strong_threshold = float(
        (config.scoring or {}).get("thresholds", {}).get("immediate_alert", 78)
    )
    if seniority_gap == "high":
        current_score = min(current_score, strong_threshold - 0.1)
    if not substantive_duty:
        current_score = min(current_score, strong_threshold - 1.0)
    pre_capability_score = current_score
    capability_gate = (config.scoring or {}).get(
        "critical_capability_gate", {}
    )
    if capability_assessment["central_to_most_duties"]:
        current_score = min(
            current_score,
            float(capability_gate.get("central_core_ceiling", 54)),
        )
    elif capability_assessment["major_learnable_gap"]:
        current_score = min(
            current_score,
            float(capability_gate.get("major_gap_ceiling", 61)),
        )
    capability_adjustment = round(
        min(0.0, current_score - pre_capability_score), 1
    )
    pre_direction_score = current_score
    if low_career_direction:
        current_score = min(
            current_score,
            float(capability_gate.get("low_career_direction_ceiling", 61)),
        )
    direction_adjustment = round(
        min(0.0, current_score - pre_direction_score), 1
    )
    if hkex_function:
        gate = (config.scoring or {}).get("hkex_primary_function_gate", {})
        classification = hkex_function["classification"]
        if classification == "DEPRIORITIZED":
            current_score = min(
                current_score,
                float(gate.get("deprioritized_current_score_ceiling", 39)),
            )
        elif classification == "NON_TARGET":
            current_score = min(
                current_score,
                float(gate.get("non_target_current_score_ceiling", 59)),
            )
    components["core_skill_gap_penalty"] = capability_adjustment
    components["career_direction_ceiling_adjustment"] = (
        direction_adjustment
    )
    components["capability_fit_score"] = float(
        capability_assessment["capability_fit_score"]
    )
    components["career_direction_fit_score"] = career_direction_fit_score
    category, action = _category_and_action(
        current_score,
        eligibility,
        seniority_gap,
        vacancy.title,
        config,
    )
    if hkex_function and hkex_function["classification"] == "DEPRIORITIZED":
        category, action = "NOT SUITABLE", "SKIP"
    blueprint_score, blueprint_parts = _blueprint_score(
        signals, institution, vacancy.title
    )
    if hkex_function and hkex_function["classification"] == "TARGET":
        blueprint_score = max(70.0, blueprint_score)
    blueprint_score = round(
        _blueprint_execution_ceiling(
            blueprint_score, vacancy.cleaned_text, signals, config
        ),
        1,
    )
    if hkex_function:
        gate = (config.scoring or {}).get("hkex_primary_function_gate", {})
        classification = hkex_function["classification"]
        if classification == "DEPRIORITIZED":
            blueprint_score = min(
                blueprint_score,
                float(gate.get("deprioritized_blueprint_score_ceiling", 39)),
            )
        elif classification == "NON_TARGET":
            blueprint_score = min(
                blueprint_score,
                float(gate.get("non_target_blueprint_score_ceiling", 54)),
            )
    blueprint_label = _blueprint_label(
        blueprint_score,
        blueprint_parts,
        current_score,
        eligibility,
        config,
    )
    evidence = _supporting_evidence(vacancy, signals, decisions)
    for item in capability_assessment["missing_critical_capabilities"][:2]:
        excerpt = " ".join(str(item["evidence"]).split())[:260]
        if excerpt and not any(
            existing["excerpt"] == excerpt for existing in evidence
        ):
            evidence.append(
                {
                    "excerpt": excerpt,
                    "component": "capability_fit",
                    "concern": "CORE SKILL GAP",
                }
            )
    if hkex_function:
        gate_excerpts = (
            hkex_function["deprioritized_evidence"]
            if hkex_function["classification"] == "DEPRIORITIZED"
            else hkex_function["target_evidence"]
        )
        if gate_excerpts:
            evidence.append(
                {
                    "excerpt": " ".join(str(gate_excerpts[0]).split())[:260],
                    "component": "hkex_primary_function_gate",
                    "concern": (
                        "deprioritized primary function"
                        if hkex_function["classification"] == "DEPRIORITIZED"
                        else "HKEX target-function evidence"
                    ),
                }
            )
    preliminary, fits, gaps = _preliminary_analysis(
        vacancy,
        signals,
        decisions,
        evidence,
        seniority_gap,
        seniority_penalty,
        max(0.0, -experience_adjustment),
        eligibility,
        config.candidate or {},
        capability_assessment,
        career_direction_fit_score,
    )
    preliminary["experience_feasibility"] = experience_feasibility
    if low_career_direction:
        gaps.append(
            "Career-direction fit is reduced because the role is dominated by "
            "operational, field-support, or routine processing duties."
        )
    if hkex_function:
        preliminary["hkex_primary_function_gate"] = hkex_function
        if hkex_function["classification"] == "DEPRIORITIZED":
            gaps.append(
                "The HKEX primary-function gate identifies the role as dominated "
                "by technical, routine operations, HR, UAT/QA, or administrative work."
            )
        elif hkex_function["classification"] == "NON_TARGET":
            gaps.append(
                "The HKEX primary-function gate found no evidenced target-function ownership."
            )
    return VacancyAssessment(
        vacancy_id=vacancy_id,
        signals=signals,
        eligibility_status=eligibility,
        hard_filters=decisions,
        component_scores=components,
        current_application_score=current_score,
        current_application_category=category,
        seniority_gap=seniority_gap,
        recommended_action=action,
        career_blueprint_score=blueprint_score,
        career_blueprint_label=blueprint_label,
        preliminary_analysis=preliminary,
        key_fit_reasons=fits,
        main_gaps_or_risks=gaps,
        supporting_evidence=evidence,
        analysis_version=ANALYSIS_VERSION,
        text_hash=vacancy_text_hash(vacancy),
        config_hash=analysis_config_hash(config, institution),
        analysed_at=timestamp,
    )


def assessment_as_json_values(
    assessment: VacancyAssessment,
) -> dict[str, str | float]:
    return {
        "requirement_signals_json": json.dumps(
            asdict(assessment.signals), ensure_ascii=False, sort_keys=True
        ),
        "hard_filters_json": json.dumps(
            [asdict(item) for item in assessment.hard_filters],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "component_scores_json": json.dumps(
            assessment.component_scores, sort_keys=True
        ),
        "preliminary_analysis_json": json.dumps(
            assessment.preliminary_analysis, ensure_ascii=False, sort_keys=True
        ),
        "key_fit_reasons_json": json.dumps(
            assessment.key_fit_reasons, ensure_ascii=False
        ),
        "main_gaps_or_risks_json": json.dumps(
            assessment.main_gaps_or_risks, ensure_ascii=False
        ),
        "supporting_evidence_json": json.dumps(
            assessment.supporting_evidence, ensure_ascii=False, sort_keys=True
        ),
    }
