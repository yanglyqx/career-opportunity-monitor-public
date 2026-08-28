const REPOSITORY_RAW =
  "https://raw.githubusercontent.com/yanglyqx/career-opportunity-monitor-public/main/src/job_monitor";

const PYTHON_FILES = ["__init__.py", "models.py", "analysis.py", "preference_filter.py"];

const defaultPreferences = {
  enabled: true,
  internship: {
    id: "internship",
    action: "EXCLUDED",
    title_terms: ["intern", "internship"],
    employment_terms: ["intern", "internship"],
  },
  excluded_role_families: [
    {
      id: "human_resources",
      action: "EXCLUDED",
      title_terms: [
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
      responsibility_terms: [
        "human resources",
        "recruitment",
        "payroll",
        "employee relations",
        "talent acquisition",
        "talent operations",
        "personnel administration",
      ],
      keyword_terms: [
        "human resources",
        "recruitment",
        "payroll",
        "employee relations",
        "talent operations",
      ],
      minimum_non_title_matches: 2,
    },
  ],
  deprioritized_role_families: [
    {
      id: "administrative_programme_execution",
      action: "DEPRIORITIZED",
      title_terms: [
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
      responsibility_terms: [
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
      keyword_terms: [
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
      preserve_terms: [
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
      minimum_evidence_count: 2,
      low_value_dominance_ratio: 1.0,
      substantive_override_minimum: 2,
    },
  ],
};

const pythonBridge = `
import json
from datetime import datetime, timezone

from job_monitor.analysis import assess_vacancy
from job_monitor.models import AppConfig, InstitutionConfig, Vacancy
from job_monitor.preference_filter import candidate_preference_decision

INSTITUTION = InstitutionConfig(
    name="Interactive Demo Institution",
    short_name="DEMO",
    careers_url=None,
    adapter="demo",
    enabled=True,
    category="financial institution",
    priority="high",
)

def assess_browser_input(candidate_json, vacancy_json):
    candidate = json.loads(candidate_json)
    vacancy_data = json.loads(vacancy_json)
    now = datetime.now(timezone.utc)
    vacancy = Vacancy(
        institution="DEMO",
        title=vacancy_data["title"],
        official_url="https://example.com/interactive-demo",
        vacancy_identifier="BROWSER-001",
        closing_date=None,
        cleaned_text=vacancy_data["cleaned_text"],
        first_seen=now,
        last_seen=now,
        location=vacancy_data.get("location"),
        employment_type=vacancy_data.get("employment_type"),
    )
    config = AppConfig(
        config_path="browser",
        database_path=":memory:",
        reports_dir="",
        max_jobs_per_source=1,
        institutions={"DEMO": INSTITUTION},
        candidate=candidate,
        hard_filters={},
        scoring={},
        career_blueprint={},
    )
    assessment = assess_vacancy(
        vacancy,
        config,
        INSTITUTION,
        vacancy_id=1,
        analysed_at=now,
    )
    preference = candidate_preference_decision(
        vacancy, config, assessment=assessment
    )
    return json.dumps({
        "title": vacancy.title,
        "location": vacancy.location,
        "employment_type": vacancy.employment_type,
        "current_score": assessment.current_application_score,
        "current_category": assessment.current_application_category,
        "recommended_action": assessment.recommended_action,
        "preference_status": preference.status,
        "long_term_score": assessment.career_blueprint_score,
        "long_term_label": assessment.career_blueprint_label,
        "key_fit_reasons": assessment.key_fit_reasons,
        "main_gaps_or_risks": assessment.main_gaps_or_risks,
    })
`;

let pyodideRuntime;

function terms(id) {
  return document
    .getElementById(id)
    .value.split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function candidateInput() {
  return {
    target_functions: terms("target-functions"),
    deprioritized_functions: ["sales", "administration", "routine operations"],
    education_level: document.getElementById("education-level").value,
    education_fields: terms("education-fields"),
    languages: terms("languages"),
    experience_profile: {
      years_full_time: Number(document.getElementById("experience-years").value || 0),
      supported_skills: terms("supported-skills"),
    },
    ordinary_opportunity_preferences: defaultPreferences,
  };
}

function vacancyInput() {
  return {
    title: document.getElementById("job-title").value.trim(),
    location: document.getElementById("job-location").value.trim(),
    employment_type: document.getElementById("employment-type").value,
    cleaned_text: document.getElementById("job-description").value.trim(),
  };
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function fillList(id, items, emptyMessage) {
  const list = document.getElementById(id);
  list.replaceChildren();
  const values = items.length ? items : [emptyMessage];
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = value;
    list.appendChild(item);
  }
}

function showResult(result) {
  document.getElementById("empty-state").hidden = true;
  document.getElementById("error-state").hidden = true;
  document.getElementById("results").hidden = false;
  setText("result-job-title", result.title);
  setText(
    "result-meta",
    [result.location, result.employment_type].filter(Boolean).join(" · "),
  );
  setText("current-score", `${result.current_score.toFixed(1)}/100`);
  setText("current-category", result.current_category);
  setText("recommended-action", result.recommended_action);
  setText("preference-status", result.preference_status);
  setText("long-term-score", `${result.long_term_score.toFixed(1)}/100`);
  setText("long-term-label", result.long_term_label);
  fillList("fit-reasons", result.key_fit_reasons, "No strong fit reason was extracted.");
  fillList("gaps", result.main_gaps_or_risks, "No major gap was extracted.");
  document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function showError(error) {
  document.getElementById("empty-state").hidden = true;
  document.getElementById("results").hidden = true;
  document.getElementById("error-state").hidden = false;
  setText("error-message", error instanceof Error ? error.message : String(error));
}

async function initializePython() {
  const status = document.getElementById("engine-status");
  const button = document.getElementById("analyze-button");
  const buttonLabel = document.getElementById("button-label");
  try {
    pyodideRuntime = await loadPyodide();
    pyodideRuntime.FS.mkdirTree("/home/pyodide/job_monitor");
    await Promise.all(
      PYTHON_FILES.map(async (filename) => {
        const response = await fetch(`${REPOSITORY_RAW}/${filename}`);
        if (!response.ok) {
          throw new Error(`Could not load ${filename} from the public repository.`);
        }
        pyodideRuntime.FS.writeFile(
          `/home/pyodide/job_monitor/${filename}`,
          await response.text(),
          { encoding: "utf8" },
        );
      }),
    );
    await pyodideRuntime.runPythonAsync(
      `import sys\nsys.path.insert(0, "/home/pyodide")\n${pythonBridge}`,
    );
    button.disabled = false;
    buttonLabel.textContent = "Analyze opportunity";
    status.textContent = "Scoring engine ready. Analysis runs locally in this browser.";
  } catch (error) {
    buttonLabel.textContent = "Scoring engine unavailable";
    status.textContent = "The local runtime could not be loaded. Please refresh and try again.";
    showError(error);
  }
}

document.getElementById("assessment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = document.getElementById("analyze-button");
  const buttonLabel = document.getElementById("button-label");
  const vacancy = vacancyInput();
  if (!vacancy.title || !vacancy.cleaned_text) {
    showError(new Error("Add both a job title and a job description."));
    return;
  }

  button.disabled = true;
  buttonLabel.textContent = "Analyzing…";
  try {
    pyodideRuntime.globals.set("candidate_json", JSON.stringify(candidateInput()));
    pyodideRuntime.globals.set("vacancy_json", JSON.stringify(vacancy));
    const output = await pyodideRuntime.runPythonAsync(
      "assess_browser_input(candidate_json, vacancy_json)",
    );
    showResult(JSON.parse(output));
  } catch (error) {
    showError(error);
  } finally {
    button.disabled = false;
    buttonLabel.textContent = "Analyze opportunity";
  }
});

initializePython();
