from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from job_monitor.models import Vacancy


def _report_values(item: Vacancy | Mapping[str, Any]) -> tuple[str, str, str, str | None]:
    if isinstance(item, Vacancy):
        closing = item.closing_date.isoformat() if item.closing_date else "Not provided"
        return item.title, item.official_url, closing, item.detail_fetch_error
    return (
        str(item["title"]),
        str(item["official_url"]),
        str(item["closing_date"] or "Not provided"),
        item["detail_fetch_error"],
    )


def render_markdown_report(
    institution_name: str,
    vacancies: Iterable[Vacancy | Mapping[str, Any]],
    checked_at: datetime,
    *,
    source_status: str | None = None,
    detail_pages_succeeded: int | None = None,
    detail_page_failures: int | None = None,
    manual_review_url: str | None = None,
) -> str:
    items = list(vacancies)
    lines = [
        f"# Current vacancies — {institution_name}",
        "",
        f"Checked at: {checked_at.isoformat()}",
        "",
        f"Vacancies detected: {len(items)}",
        "",
    ]
    if source_status:
        lines.extend(
            [
                f"Source status: {source_status}",
                "",
                f"Detail pages successfully fetched: {detail_pages_succeeded or 0}",
                "",
                f"Detail-page failures: {detail_page_failures or 0}",
                "",
            ]
        )
        if manual_review_url:
            lines.extend(
                [f"Official manual-review link: {manual_review_url}", ""]
            )
    if not items:
        lines.append("_No current vacancies detected._")
    for item in items:
        title, url, closing, error = _report_values(item)
        lines.extend(
            [
                f"## [{title}]({url})",
                "",
                f"- Closing date: {closing}",
            ]
        )
        if error:
            lines.append(f"- Detail status: unavailable ({error})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(directory: str | Path, filename: str, content: str) -> Path:
    report_dir = Path(directory)
    report_dir.mkdir(parents=True, exist_ok=True)
    destination = report_dir / filename
    destination.write_text(content, encoding="utf-8")
    return destination


def _json_value(row: Mapping[str, Any], key: str, fallback: Any) -> Any:
    value = row[key]
    if not value:
        return fallback
    try:
        return json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return fallback


def _assessment_section(row: Mapping[str, Any]) -> str:
    category = str(row["current_application_category"])
    if category == "ELIGIBILITY UNCLEAR":
        return "Requires eligibility review"
    if category in {"STRONG MATCH", "STRETCH BUT WORTHWHILE"}:
        return "Immediate attention"
    if category == "MONITOR ONLY":
        return "Monitor only"
    return "Not suitable"


def render_assessment_report(
    institution_name: str,
    rows: Iterable[Mapping[str, Any]],
    generated_at: datetime,
) -> str:
    assessed = [row for row in rows if row["assessment_id"] is not None]
    sections = (
        "Immediate attention",
        "Requires eligibility review",
        "Career blueprint",
        "Monitor only",
        "Not suitable",
    )
    grouped = {}
    for section in sections:
        if section == "Career blueprint":
            grouped[section] = [
                row
                for row in assessed
                if row["career_blueprint_label"] != "NOT RETAINED"
            ]
        else:
            grouped[section] = [
                row for row in assessed if _assessment_section(row) == section
            ]
    lines = [
        f"# Vacancy assessment — {institution_name}",
        "",
        f"Generated at: {generated_at.isoformat()}",
        "",
        (
            "_Preliminary rule-based assessment. It uses only explicit vacancy text "
            "and the configured candidate profile; verify important requirements manually._"
        ),
        "",
        f"Assessed current vacancies: {len(assessed)}",
        "",
    ]
    for section in sections:
        lines.extend([f"## {section}", ""])
        section_rows = grouped[section]
        if not section_rows:
            lines.extend(["_None._", ""])
            continue
        for row in section_rows:
            hard_filters = _json_value(row, "hard_filters_json", [])
            evidence = _json_value(row, "supporting_evidence_json", [])
            analysis = _json_value(row, "preliminary_analysis_json", {})
            signals = _json_value(row, "requirement_signals_json", {})
            fits = _json_value(row, "key_fit_reasons_json", [])
            gaps = _json_value(row, "main_gaps_or_risks_json", [])
            required_years = signals.get("minimum_required_experience_years")
            required_experience = (
                f"{required_years:g} years minimum"
                if isinstance(required_years, (int, float))
                else "Not clearly stated"
            )

            if section == "Career blueprint":
                attractive = analysis.get("why_the_work_is_attractive", [])
                direction = analysis.get("possible_long_term_career_path", [])
                skills = analysis.get("skills_to_build", [])
                next_role = analysis.get("experience_to_seek_in_next_role", [])
                keywords = analysis.get("useful_keywords_for_future_searches", [])
                lines.extend(
                    [
                        f"### [{row['title']}]({row['official_url']})",
                        "",
                        (
                            "- Long-term career blueprint score: "
                            f"{row['career_blueprint_score']:.1f}/100"
                        ),
                        f"- Career-blueprint label: {row['career_blueprint_label']}",
                        (
                            "- Why the actual work may be attractive: "
                            + (
                                "; ".join(str(value) for value in attractive)
                                if attractive
                                else "No specific duty extracted."
                            )
                        ),
                        (
                            "- Possible long-term direction: "
                            + (
                                "; ".join(str(value) for value in direction)
                                if direction
                                else "Not established."
                            )
                        ),
                        (
                            "- Skills and experience to build: "
                            + (
                                ", ".join(str(value) for value in skills)
                                if skills
                                else "Manual review required."
                            )
                        ),
                        (
                            "- Helpful next job: "
                            + (
                                "; ".join(str(value) for value in next_role)
                                if next_role
                                else "Not established."
                            )
                        ),
                        (
                            "- Future search keywords: "
                            + (
                                ", ".join(str(value) for value in keywords)
                                if keywords
                                else "None extracted."
                            )
                        ),
                        (
                            "- Current viability: "
                            + str(
                                analysis.get(
                                    "current_viability",
                                    "Requires manual verification.",
                                )
                            )
                        ),
                        "",
                    ]
                )
                continue

            if section == "Not suitable":
                reasons = [
                    str(item.get("reason", ""))
                    for item in hard_filters
                    if item.get("reason")
                ]
                brief = (
                    reasons[0]
                    if reasons
                    else gaps[0]
                    if gaps
                    else "Below the configured current-viability threshold."
                )
                lines.extend(
                    [
                        f"- [{row['title']}]({row['official_url']}) — {brief}",
                    ]
                )
                if evidence:
                    lines.append("  - Supporting vacancy-text evidence:")
                    for item in evidence[:2]:
                        lines.append(
                            "    - "
                            f"{item.get('concern', 'fit')} "
                            f"({item.get('component', 'unknown')}): "
                            f"“{item.get('excerpt', '')}”"
                        )
                lines.append("")
                continue

            notes = analysis.get("possible_long_term_career_path", [])
            lines.extend(
                [
                    f"### [{row['title']}]({row['official_url']})",
                    "",
                    f"- Institution: {row['institution']}",
                    f"- Deadline: {row['closing_date'] or 'Not provided'}",
                    (
                        "- Current application score: "
                        f"{row['current_application_score']:.1f}/100"
                    ),
                    f"- Current application category: {row['current_application_category']}",
                    (
                        "- Long-term career blueprint score: "
                        f"{row['career_blueprint_score']:.1f}/100"
                    ),
                    f"- Career-blueprint label: {row['career_blueprint_label']}",
                    f"- Eligibility status: {row['eligibility_status']}",
                    f"- Seniority gap: {row['seniority_gap']}",
                    f"- Recommended action: {row['recommended_action']}",
                    (
                        "- Evidence-based fit reasons: "
                        + ("; ".join(fits) if fits else "No strong signal extracted.")
                    ),
                    (
                        "- Main gaps or risks: "
                        + ("; ".join(gaps) if gaps else "None extracted.")
                    ),
                    f"- Extracted required experience: {required_experience}",
                    (
                        "- Preliminary career-development notes: "
                        + (
                            "; ".join(str(value) for value in notes)
                            if notes
                            else "No supported direction generated."
                        )
                    ),
                ]
            )
            if evidence:
                lines.append("- Supporting vacancy-text evidence:")
                for item in evidence:
                    lines.append(
                        "  - "
                        f"{item.get('concern', 'fit')} "
                        f"({item.get('component', 'unknown')}): "
                        f"“{item.get('excerpt', '')}”"
                    )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_assessment_csv(rows: Iterable[Mapping[str, Any]]) -> str:
    output = io.StringIO(newline="")
    fieldnames = [
        "institution",
        "title",
        "official_url",
        "deadline",
        "current_application_score",
        "current_application_category",
        "career_blueprint_score",
        "career_blueprint_label",
        "eligibility_status",
        "seniority_gap",
        "recommended_action",
        "minimum_required_experience_years",
        "key_fit_reasons",
        "main_gaps_or_risks",
        "supporting_evidence",
        "analysis_version",
        "analysed_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        if row["assessment_id"] is None:
            continue
        signals = _json_value(row, "requirement_signals_json", {})
        writer.writerow(
            {
                "institution": row["institution"],
                "title": row["title"],
                "official_url": row["official_url"],
                "deadline": row["closing_date"] or "",
                "current_application_score": row["current_application_score"],
                "current_application_category": row[
                    "current_application_category"
                ],
                "career_blueprint_score": row["career_blueprint_score"],
                "career_blueprint_label": row["career_blueprint_label"],
                "eligibility_status": row["eligibility_status"],
                "seniority_gap": row["seniority_gap"],
                "recommended_action": row["recommended_action"],
                "minimum_required_experience_years": signals.get(
                    "minimum_required_experience_years", ""
                ),
                "key_fit_reasons": " | ".join(
                    _json_value(row, "key_fit_reasons_json", [])
                ),
                "main_gaps_or_risks": " | ".join(
                    _json_value(row, "main_gaps_or_risks_json", [])
                ),
                "supporting_evidence": " | ".join(
                    (
                        f"{item.get('concern', '')}: {item.get('excerpt', '')}"
                        for item in _json_value(
                            row, "supporting_evidence_json", []
                        )
                    )
                ),
                "analysis_version": row["analysis_version"],
                "analysed_at": row["analysed_at"],
            }
        )
    return output.getvalue()


def _combined_section(row: Mapping[str, Any], generated_at: datetime) -> str:
    if str(row["eligibility_status"]) == "UNCLEAR":
        return "Requires eligibility review"
    if str(row["eligibility_status"]) == "INELIGIBLE":
        return "Not suitable"
    deadline = row["closing_date"]
    approaching = False
    if deadline:
        try:
            days = (
                datetime.fromisoformat(str(deadline)).date() - generated_at.date()
            ).days
            approaching = 0 <= days <= 7
        except ValueError:
            pass
    if str(row["current_application_category"]) in {
        "STRONG MATCH",
        "STRETCH BUT WORTHWHILE",
    } or approaching:
        return "Immediate attention"
    if str(row["current_application_category"]) == "MONITOR ONLY":
        return "Monitor only"
    return "Not suitable"


def render_combined_assessment_report(
    rows: Iterable[Mapping[str, Any]],
    source_checks: Iterable[Mapping[str, Any]],
    generated_at: datetime,
) -> str:
    assessed = [row for row in rows if row["assessment_id"] is not None]
    sections = (
        "Immediate attention",
        "Requires eligibility review",
        "Monitor only",
        "Career blueprint",
        "Not suitable",
    )
    lines = [
        "# Combined vacancy assessment",
        "",
        f"Generated at: {generated_at.isoformat()}",
        "",
        "_Current application viability and long-term career value are independent. "
        "A high blueprint score never overrides current eligibility._",
        "",
        "## Source problems",
        "",
    ]
    problems = [
        row
        for row in source_checks
        if str(row["status"])
        not in {"SUCCESS", "VALID_ZERO_VACANCIES"}
    ]
    if problems:
        for row in problems:
            lines.extend(
                [
                    f"- **{row['institution']} — {row['status']}**: "
                    f"{row['message'] or 'No additional detail.'} "
                    f"([official manual review]({row['manual_review_url']}))",
                ]
            )
    else:
        lines.append("_No recorded source problems._")
    lines.append("")

    for section in sections:
        lines.extend([f"## {section}", ""])
        if section == "Career blueprint":
            section_rows = [
                row
                for row in assessed
                if str(row["career_blueprint_label"]) != "NOT RETAINED"
                or (
                    "archive_status" in row.keys()
                    and str(row["archive_status"]) == "ARCHIVED"
                )
            ]
        else:
            section_rows = [
                row
                for row in assessed
                if int(row["is_current"])
                and _combined_section(row, generated_at) == section
            ]
        if not section_rows:
            lines.extend(["_None._", ""])
            continue
        for row in section_rows:
            signals = _json_value(row, "requirement_signals_json", {})
            evidence = _json_value(row, "supporting_evidence_json", [])
            fits = _json_value(row, "key_fit_reasons_json", [])
            gaps = _json_value(row, "main_gaps_or_risks_json", [])
            analysis = _json_value(row, "preliminary_analysis_json", {})
            identifier = row["vacancy_identifier"] or row["source_fingerprint"]
            years = signals.get("minimum_required_experience_years")
            experience = (
                f"{years:g} years minimum"
                if isinstance(years, (int, float))
                else "Not clearly stated"
            )
            qualifications = (
                signals.get("mandatory_professional_qualifications", [])
                + signals.get("preferred_professional_qualifications", [])
            )
            lines.extend(
                [
                    f"### [{row['institution']} — {row['title']}]({row['official_url']})",
                    "",
                    f"- Vacancy ID: {identifier}",
                    f"- Deadline: {row['closing_date'] or 'Not provided'}",
                    f"- Current application score: {float(row['current_application_score']):.1f}/100",
                    f"- Current application category: {row['current_application_category']}",
                    f"- Long-term career-blueprint score: {float(row['career_blueprint_score']):.1f}/100",
                    f"- Career-blueprint label: {row['career_blueprint_label']}",
                    f"- Eligibility status: {row['eligibility_status']}",
                    f"- Seniority gap: {row['seniority_gap']}",
                    f"- Recommended action: {row['recommended_action']}",
                    "- Key fit reasons: "
                    + ("; ".join(fits) if fits else "No strong signal extracted"),
                    "- Main gaps or risks: "
                    + ("; ".join(gaps) if gaps else "None extracted"),
                    f"- Extracted required experience: {experience}",
                    "- Relevant qualification requirements: "
                    + (
                        ", ".join(dict.fromkeys(qualifications))
                        if qualifications
                        else "None clearly extracted"
                    ),
                    "- Preliminary career-development notes: "
                    + "; ".join(
                        analysis.get("possible_long_term_career_path", [])
                    )
                    if analysis.get("possible_long_term_career_path")
                    else "- Preliminary career-development notes: Not established",
                ]
            )
            if evidence:
                lines.append("- Supporting vacancy-text evidence:")
                for item in evidence:
                    lines.append(
                        f"  - {item.get('concern', 'fit')} "
                        f"({item.get('component', 'unknown')}): "
                        f"“{item.get('excerpt', '')}”"
                    )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_combined_assessment_csv(
    rows: Iterable[Mapping[str, Any]],
    generated_at: datetime,
) -> str:
    output = io.StringIO(newline="")
    fields = [
        "section",
        "institution",
        "title",
        "vacancy_id",
        "official_url",
        "deadline",
        "current_application_score",
        "current_application_category",
        "career_blueprint_score",
        "career_blueprint_label",
        "eligibility_status",
        "seniority_gap",
        "recommended_action",
        "required_experience",
        "qualifications",
        "key_fit_reasons",
        "main_gaps_or_risks",
        "supporting_evidence",
        "preliminary_career_development_notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        if row["assessment_id"] is None:
            continue
        section = (
            "Career blueprint"
            if not int(row["is_current"])
            and "archive_status" in row.keys()
            and str(row["archive_status"]) == "ARCHIVED"
            else _combined_section(row, generated_at)
        )
        if not int(row["is_current"]) and section != "Career blueprint":
            continue
        signals = _json_value(row, "requirement_signals_json", {})
        analysis = _json_value(row, "preliminary_analysis_json", {})
        writer.writerow(
            {
                "section": section,
                "institution": row["institution"],
                "title": row["title"],
                "vacancy_id": row["vacancy_identifier"]
                or row["source_fingerprint"],
                "official_url": row["official_url"],
                "deadline": row["closing_date"] or "",
                "current_application_score": row["current_application_score"],
                "current_application_category": row[
                    "current_application_category"
                ],
                "career_blueprint_score": row["career_blueprint_score"],
                "career_blueprint_label": row["career_blueprint_label"],
                "eligibility_status": row["eligibility_status"],
                "seniority_gap": row["seniority_gap"],
                "recommended_action": row["recommended_action"],
                "required_experience": signals.get(
                    "minimum_required_experience_years", ""
                ),
                "qualifications": " | ".join(
                    signals.get("mandatory_professional_qualifications", [])
                    + signals.get("preferred_professional_qualifications", [])
                ),
                "key_fit_reasons": " | ".join(
                    _json_value(row, "key_fit_reasons_json", [])
                ),
                "main_gaps_or_risks": " | ".join(
                    _json_value(row, "main_gaps_or_risks_json", [])
                ),
                "supporting_evidence": " | ".join(
                    f"{item.get('concern', '')}: {item.get('excerpt', '')}"
                    for item in _json_value(
                        row, "supporting_evidence_json", []
                    )
                ),
                "preliminary_career_development_notes": " | ".join(
                    analysis.get("possible_long_term_career_path", [])
                ),
            }
        )
    return output.getvalue()
