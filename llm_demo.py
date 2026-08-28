from __future__ import annotations

import json

from demo import DEMO_JOBS
from job_monitor.llm_analysis import extract_job_description_with_llm


def main() -> None:
    vacancy = DEMO_JOBS[1]
    analysis = extract_job_description_with_llm(vacancy.cleaned_text or "")

    print("=" * 72)
    print("LLM-ASSISTED JOB ANALYSIS - OPTIONAL DEMO")
    print("=" * 72)
    print(f"Vacancy: {vacancy.title}")
    print(json.dumps(analysis.as_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
