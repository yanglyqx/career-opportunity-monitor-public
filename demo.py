from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from job_monitor.analysis import assess_vacancy
from job_monitor.input_files import load_candidate, load_vacancies
from job_monitor.models import (
    AppConfig,
    InstitutionConfig,
    Vacancy,
    VacancyAssessment,
)
from job_monitor.preference_filter import (
    candidate_preference_decision,
    filter_current_recommendations,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_CANDIDATE_PATH = ROOT / "examples" / "candidate.example.yaml"
DEFAULT_JOBS_PATH = ROOT / "fixtures" / "demo_jobs.json"


INSTITUTION = InstitutionConfig(
    name="Demo Financial Institution",
    short_name="DEMO",
    careers_url=None,
    adapter="demo",
    enabled=True,
    category="financial institution",
    priority="high",
)


def build_config(candidate: dict, *, config_path: Path) -> AppConfig:
    return AppConfig(
        config_path=str(config_path),
        database_path=":memory:",
        reports_dir="sample_output",
        max_jobs_per_source=100,
        institutions={"DEMO": INSTITUTION},
        candidate=candidate,
        hard_filters={},
        scoring={},
        career_blueprint={},
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate vacancies against a configurable candidate profile."
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=DEFAULT_CANDIDATE_PATH,
        help="Candidate YAML file (default: examples/candidate.example.yaml)",
    )
    parser.add_argument(
        "--jobs",
        type=Path,
        default=DEFAULT_JOBS_PATH,
        help="Vacancy JSON file (default: fixtures/demo_jobs.json)",
    )
    return parser.parse_args(argv)


def run_demo(
    candidate_path: Path,
    jobs_path: Path,
    *,
    observed_at: datetime | None = None,
) -> None:
    now = observed_at or datetime.now(timezone.utc)
    candidate = load_candidate(candidate_path)
    vacancies = load_vacancies(jobs_path, observed_at=now)
    config = build_config(candidate, config_path=candidate_path)
    using_defaults = (
        candidate_path.resolve() == DEFAULT_CANDIDATE_PATH.resolve()
        and jobs_path.resolve() == DEFAULT_JOBS_PATH.resolve()
    )

    print("=" * 72)
    print("CAREER OPPORTUNITY MONITOR - PUBLIC DEMO")
    print("=" * 72)
    print()
    if using_defaults:
        print(
            "This demo evaluates fictional vacancies against a fictional "
            "early-career candidate profile."
        )
    else:
        print("Evaluating configured vacancies against the supplied candidate profile.")
    print()

    assessed_jobs: list[tuple[Vacancy, VacancyAssessment]] = []
    for index, vacancy in enumerate(vacancies, start=1):
        institution = config.institutions.get(vacancy.institution, INSTITUTION)
        assessment = assess_vacancy(
            vacancy,
            config,
            institution,
            vacancy_id=index,
            analysed_at=now,
        )
        assessed_jobs.append((vacancy, assessment))
        preference = candidate_preference_decision(
            vacancy, config, assessment=assessment
        )

        print("-" * 72)
        print(f"{index}. {vacancy.title}")
        print(f"   Location:       {vacancy.location}")
        print(
            f"   Current Fit:    "
            f"{assessment.current_application_score:.1f}/100"
        )
        print(f"   Current Status: {assessment.current_application_category}")
        print(f"   Recommended:    {assessment.recommended_action}")
        print(f"   Preference:     {preference.status}")
        print(
            f"   Long-Term Fit:  "
            f"{assessment.career_blueprint_score:.1f}/100"
        )
        print(f"   Long-Term Label: {assessment.career_blueprint_label}")

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
        (vacancy for vacancy, _ in assessed_jobs), config
    )
    print("CURRENT RECOMMENDATIONS AFTER PREFERENCE FILTER")
    for vacancy in current_recommendations:
        print(f"   - {vacancy.title}")
    print()

    print("=" * 72)
    print("Demo complete.")
    print("=" * 72)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run_demo(args.candidate, args.jobs)


if __name__ == "__main__":
    main()
