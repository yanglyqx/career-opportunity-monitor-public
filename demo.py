from datetime import datetime, timezone

from job_monitor.analysis import assess_vacancy
from job_monitor.models import AppConfig, InstitutionConfig, Vacancy
from job_monitor.preference_filter import (
    candidate_preference_decision,
    filter_current_recommendations,
)


# ---------------------------------------------------------------------
# Demo candidate
# Fictional profile used only to demonstrate the public workflow.
# ---------------------------------------------------------------------

DEMO_CANDIDATE = {
    "target_functions": [
        "research",
        "policy analysis",
        "data analysis",
        "risk analysis",
        "financial regulation",
    ],
    "deprioritized_functions": [
        "sales",
        "administration",
        "routine operations",
    ],
    "education_level": "masters",
    "education_fields": [
        "economics",
        "finance",
        "accounting",
    ],
    "languages": [
        "English",
        "Mandarin",
    ],
    "experience_profile": {
        "years_full_time": 1.5,
        "supported_skills": [
            "Python",
            "data analysis",
            "econometric analysis",
            "financial research",
            "policy research",
            "data visualization",
        ],
    },
    "ordinary_opportunity_preferences": {
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
                    "human resource",
                    "HR analyst",
                    "HR operations",
                    "recruitment",
                    "payroll",
                    "employee relations",
                    "talent acquisition",
                    "talent operations",
                ],
                "responsibility_terms": [
                    "human resources",
                    "recruitment",
                    "payroll",
                    "employee relations",
                    "talent acquisition",
                    "talent operations",
                    "personnel administration",
                ],
                "keyword_terms": [
                    "human resources",
                    "recruitment",
                    "payroll",
                    "employee relations",
                    "talent operations",
                ],
                "minimum_non_title_matches": 2,
            }
        ],
        "deprioritized_role_families": [
            {
                "id": "administrative_programme_execution",
                "action": "DEPRIORITIZED",
                "title_terms": [
                    "general administration",
                    "administrative assistant",
                    "administrative officer",
                    "programme assistant",
                    "program assistant",
                    "programme coordinator",
                    "program coordinator",
                    "project support",
                    "operations coordinator",
                ],
                "responsibility_terms": [
                    "general administration",
                    "administrative support",
                    "logistics",
                    "procurement",
                    "scheduling",
                    "calendar management",
                    "budget administration",
                    "operational support",
                    "meeting coordination",
                    "maintain records",
                    "travel arrangements",
                    "event logistics",
                    "invoice processing",
                    "day-to-day implementation",
                    "day to day implementation",
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
                    "administrative support",
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
                    "project development",
                    "climate finance",
                    "policy",
                    "policy implementation",
                    "financial analysis",
                    "risk",
                    "regulation",
                    "regulatory",
                    "research",
                    "data analysis",
                    "technical programme design",
                    "technical program design",
                    "programme design",
                    "program design",
                ],
                "minimum_evidence_count": 2,
                "low_value_dominance_ratio": 1.0,
                "substantive_override_minimum": 2,
            }
        ],
    },
}


# ---------------------------------------------------------------------
# Minimal public configuration
# ---------------------------------------------------------------------

INSTITUTION = InstitutionConfig(
    name="Demo Financial Institution",
    short_name="DEMO",
    careers_url=None,
    adapter="demo",
    enabled=True,
    category="financial institution",
    priority="high",
)


CONFIG = AppConfig(
    config_path="demo",
    database_path=":memory:",
    reports_dir="sample_output",
    max_jobs_per_source=10,
    institutions={"DEMO": INSTITUTION},
    candidate=DEMO_CANDIDATE,
    hard_filters={},
    scoring={},
    career_blueprint={},
)


# ---------------------------------------------------------------------
# Synthetic vacancies
# ---------------------------------------------------------------------

NOW = datetime.now(timezone.utc)

DEMO_JOBS = [
    Vacancy(
        institution="DEMO",
        title="Junior Research Analyst",
        official_url="https://example.com/jobs/research-analyst",
        vacancy_identifier="DEMO-001",
        closing_date=None,
        cleaned_text="""
        The Research Analyst will conduct economic and financial research, analyse market and policy developments, work with large datasets, and prepare analytical reports for senior decision makers.

        Candidates should have a master's degree in economics, finance,
        accounting, public policy or a related field.

        Strong quantitative and data-analysis skills are required.
        Experience with Python, R or Stata is preferred.

        Candidates with up to two years of professional experience,
        including recent graduates, are encouraged to apply.
        """,
        first_seen=NOW,
        last_seen=NOW,
        location="Hong Kong",
        employment_type="Full-time",
    ),

    Vacancy(
        institution="DEMO",
        title="Policy and Data Analyst",
        official_url="https://example.com/jobs/policy-data-analyst",
        vacancy_identifier="DEMO-002",
        closing_date=None,
        cleaned_text="""
        The analyst will support financial-sector policy research,
        regulatory analysis and quantitative assessment.

        Responsibilities include collecting and cleaning datasets,
        analysing market developments, producing data visualisations,
        and drafting research notes.

        A postgraduate degree in economics, finance or another
        quantitative discipline is required.

        At least two years of relevant research or analytical experience
        is preferred. Knowledge of Python and financial markets is an advantage.
        """,
        first_seen=NOW,
        last_seen=NOW,
        location="Singapore",
        employment_type="Full-time",
    ),

    Vacancy(
        institution="DEMO",
        title="Senior Financial Regulation Specialist",
        official_url="https://example.com/jobs/senior-regulation-specialist",
        vacancy_identifier="DEMO-003",
        closing_date=None,
        cleaned_text="""
        The Senior Financial Regulation Specialist will lead financial-sector policy research, analyse regulatory and market developments, and advise senior management on financial stability and market policy.

        Responsibilities include designing analytical frameworks, conducting
        quantitative and qualitative research, analysing large financial datasets,
        and coordinating with domestic and international regulatory institutions.

        Applicants must have at least eight years of relevant professional
        experience in financial regulation, economic policy, market analysis
        or financial-sector research.

        Significant experience leading complex analytical projects is required.

        An advanced degree in economics, finance, public policy or a related
        quantitative discipline is desirable.
        """,    
        first_seen=NOW,
        last_seen=NOW,
        location="Hong Kong",
        employment_type="Full-time",
    ),

    Vacancy(
        institution="DEMO",
        title="Operations Coordinator",
        official_url="https://example.com/jobs/operations-coordinator",
        vacancy_identifier="DEMO-004",
        closing_date=None,
        cleaned_text="""
        The Operations Coordinator will manage administrative workflows,
        arrange meetings, process routine documentation, maintain records,
        and provide general operational support.

        One year of administrative experience is preferred.
        Strong organisational and communication skills are required.
        """,
        first_seen=NOW,
        last_seen=NOW,
        location="Hong Kong",
        employment_type="Full-time",
    ),
]


def main():
    print("=" * 72)
    print("CAREER OPPORTUNITY MONITOR - PUBLIC DEMO")
    print("=" * 72)
    print()
    print(
        "This demo evaluates fictional vacancies against a fictional "
        "early-career candidate profile."
    )
    print()

    assessed_jobs = []
    for index, vacancy in enumerate(DEMO_JOBS, start=1):
        assessment = assess_vacancy(
            vacancy,
            CONFIG,
            INSTITUTION,
            vacancy_id=index,
            analysed_at=NOW,
        )
        assessed_jobs.append((vacancy, assessment))
        preference = candidate_preference_decision(
            vacancy, CONFIG, assessment=assessment
        )

        print("-" * 72)
        print(f"{index}. {vacancy.title}")
        print(f"   Location:       {vacancy.location}")
        print(
            f"   Current Fit:    "
            f"{assessment.current_application_score:.1f}/100"
        )
        print(
            f"   Current Status: "
            f"{assessment.current_application_category}"
        )
        print(
            f"   Recommended:    "
            f"{assessment.recommended_action}"
        )
        print(f"   Preference:     {preference.status}")
        print(
            f"   Long-Term Fit:  "
            f"{assessment.career_blueprint_score:.1f}/100"
        )
        print(
            f"   Long-Term Label:"
            f" {assessment.career_blueprint_label}"
        )

        if assessment.key_fit_reasons:
            print("   Key signals:")
            for reason in assessment.key_fit_reasons[:2]:
                signal = reason.split(":", 1)[0].strip()
                print(f"      + {signal}")

        if assessment.main_gaps_or_risks:
            print("   Main gaps:")
            for gap in assessment.main_gaps_or_risks[:2]:
                clean_gap = " ".join(gap.split())
                print(f"      - {clean_gap}")

        print()

    current_recommendations = filter_current_recommendations(
        (vacancy for vacancy, _ in assessed_jobs), CONFIG
    )
    print("CURRENT RECOMMENDATIONS AFTER PREFERENCE FILTER")
    for vacancy in current_recommendations:
        print(f"   - {vacancy.title}")
    print()

    print("=" * 72)
    print("Demo complete.")
    print("=" * 72)


if __name__ == "__main__":
    main()
