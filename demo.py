from datetime import datetime, timezone

from job_monitor.analysis import assess_vacancy
from job_monitor.models import AppConfig, InstitutionConfig, Vacancy


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

    for index, vacancy in enumerate(DEMO_JOBS, start=1):
        assessment = assess_vacancy(
            vacancy,
            CONFIG,
            INSTITUTION,
            vacancy_id=index,
            analysed_at=NOW,
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

    print("=" * 72)
    print("Demo complete.")
    print("=" * 72)


if __name__ == "__main__":
    main()