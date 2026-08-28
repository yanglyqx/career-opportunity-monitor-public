const REPOSITORY_RAW =
  "https://raw.githubusercontent.com/yanglyqx/career-opportunity-monitor-public/main/src/job_monitor";
const DEMO_JOBS_URL =
  "https://raw.githubusercontent.com/yanglyqx/career-opportunity-monitor-public/main/fixtures/browser_demo_jobs.json";

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
from datetime import date, datetime, timezone

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
    institution_name = vacancy_data.get("institution", "Interactive Demo Institution")
    institution = InstitutionConfig(
        name=institution_name,
        short_name=institution_name,
        careers_url=None,
        adapter="demo",
        enabled=True,
        category="demo institution",
        priority="normal",
    )
    closing_date = (
        date.fromisoformat(vacancy_data["closing_date"])
        if vacancy_data.get("closing_date")
        else None
    )
    vacancy = Vacancy(
        institution=institution_name,
        title=vacancy_data["title"],
        official_url="https://example.com/interactive-demo",
        vacancy_identifier="BROWSER-001",
        closing_date=closing_date,
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
        institutions={institution_name: institution},
        candidate=candidate,
        hard_filters={},
        scoring={},
        career_blueprint={},
    )
    assessment = assess_vacancy(
        vacancy,
        config,
        institution,
        vacancy_id=1,
        analysed_at=now,
    )
    preference = candidate_preference_decision(
        vacancy, config, assessment=assessment
    )
    return json.dumps({
        "title": vacancy.title,
        "institution": vacancy.institution,
        "location": vacancy.location,
        "employment_type": vacancy.employment_type,
        "closing_date": vacancy.closing_date.isoformat() if vacancy.closing_date else None,
        "vacancy_text": vacancy.cleaned_text,
        "current_score": assessment.current_application_score,
        "current_category": assessment.current_application_category,
        "recommended_action": assessment.recommended_action,
        "preference_status": preference.status,
        "long_term_score": assessment.career_blueprint_score,
        "long_term_label": assessment.career_blueprint_label,
        "key_fit_reasons": assessment.key_fit_reasons,
        "main_gaps_or_risks": assessment.main_gaps_or_risks,
        "required_experience_years": assessment.signals.minimum_required_experience_years,
        "preferred_experience_years": assessment.signals.preferred_experience_years,
        "education_level": assessment.signals.education_level,
        "required_degree_fields": assessment.signals.required_degree_fields,
        "mandatory_qualifications": assessment.signals.mandatory_professional_qualifications,
        "preferred_qualifications": assessment.signals.preferred_professional_qualifications,
        "language_requirements": assessment.signals.language_requirements,
        "functional_keywords": assessment.signals.functional_keywords,
        "subject_matter_keywords": assessment.signals.subject_matter_keywords,
        "seniority_gap": assessment.seniority_gap,
        "eligibility_status": assessment.eligibility_status,
    })

def assess_browser_batch(candidate_json, vacancies_json):
    return json.dumps([
        json.loads(assess_browser_input(candidate_json, json.dumps(vacancy)))
        for vacancy in json.loads(vacancies_json)
    ])
`;

let pyodideRuntime;
let demoJobs = [];
let monitorAssessments = [];

async function extractCvText(file) {
  const buffer = await file.arrayBuffer();
  if (file.name.toLowerCase().endsWith(".pdf")) {
    const pdfjs = await import(
      "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.min.mjs"
    );
    pdfjs.GlobalWorkerOptions.workerSrc =
      "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs";
    const document = await pdfjs.getDocument({ data: buffer }).promise;
    const pages = [];
    for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
      const page = await document.getPage(pageNumber);
      const content = await page.getTextContent();
      pages.push(content.items.map((item) => item.str).join(" "));
    }
    return pages.join("\n");
  }
  if (file.name.toLowerCase().endsWith(".docx")) {
    if (!window.mammoth) throw new Error("The Word parser did not load.");
    return (await window.mammoth.extractRawText({ arrayBuffer: buffer })).value;
  }
  throw new Error("Choose a PDF or .docx Word file.");
}

function detectedTerms(text, vocabulary) {
  const lower = text.toLowerCase();
  return vocabulary.filter((term) => lower.includes(term.toLowerCase()));
}

function applyCvDraft(text) {
  const lower = text.toLowerCase();
  const fields = detectedTerms(text, [
    "economics", "finance", "accounting", "statistics", "data science",
    "public policy", "computer science", "engineering", "environmental studies",
    "international development", "public health",
  ]);
  const skills = detectedTerms(text, [
    "Python", "SQL", "R", "Stata", "Power BI", "Tableau", "Excel", "Bloomberg",
    "Refinitiv", "econometric analysis", "financial modelling", "data analysis",
    "data visualization", "machine learning", "policy research", "risk analysis",
  ]);
  const languages = detectedTerms(text, [
    "English", "Mandarin", "Cantonese", "French", "Spanish", "German",
    "Arabic", "Japanese", "Korean", "Portuguese",
  ]);
  const functions = detectedTerms(text, [
    "financial research", "policy analysis", "data analysis", "risk analysis",
    "financial regulation", "investment analysis", "climate finance",
    "economic research", "monitoring and evaluation", "data science",
  ]);
  let education = "";
  if (/\b(ph\.?d|doctorate|doctoral)\b/i.test(text)) education = "doctorate";
  else if (/\b(master|m\.?sc|m\.?phil|mba)\b/i.test(text)) education = "masters";
  else if (/\b(bachelor|b\.?sc|b\.?a\.)\b/i.test(text)) education = "bachelors";

  const yearMatches = [...lower.matchAll(/(\d+(?:\.\d+)?)\+?\s+years?\s+(?:of\s+)?(?:professional|full[- ]time|work|relevant)?\s*experience/g)]
    .map((match) => Number(match[1]))
    .filter((years) => years <= 20);

  if (education) document.getElementById("education-level").value = education;
  if (fields.length) document.getElementById("education-fields").value = fields.join(", ");
  if (skills.length) document.getElementById("supported-skills").value = skills.join(", ");
  if (languages.length) document.getElementById("languages").value = languages.join(", ");
  if (functions.length) document.getElementById("target-functions").value = functions.join(", ");
  if (yearMatches.length) {
    document.getElementById("experience-years").value = Math.max(...yearMatches);
  }
  return [
    education && "education",
    fields.length && "fields",
    skills.length && "skills",
    languages.length && "languages",
    functions.length && "functions",
    yearMatches.length && "experience",
  ].filter(Boolean);
}

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

function notificationDecision(result) {
  const currentThreshold = Number(document.getElementById("current-threshold").value);
  const longTermThreshold = Number(document.getElementById("long-term-threshold").value);
  const excluded = result.preference_status === "EXCLUDED";
  return !excluded &&
    (result.current_score >= currentThreshold || result.long_term_score >= longTermThreshold);
}

function textList(values, fallback = "Not explicitly stated") {
  if (!values || !values.length) return fallback;
  return values.map((value) => {
    if (typeof value === "string") return value;
    return Object.values(value).filter(Boolean).join(" — ");
  }).join(", ");
}

function detailSection(titleText, values, fallback) {
  const section = document.createElement("section");
  section.className = "assessment-detail-section";
  const title = document.createElement("h5");
  title.textContent = titleText;
  const list = document.createElement("ul");
  const items = values && values.length ? values : [fallback];
  for (const value of items) {
    const item = document.createElement("li");
    item.textContent = typeof value === "string"
      ? value
      : Object.values(value).filter(Boolean).join(" — ");
    list.appendChild(item);
  }
  section.append(title, list);
  return section;
}

function buildAssessmentDetails(result) {
  const wrapper = document.createElement("div");
  wrapper.className = "assessment-details";
  const facts = document.createElement("div");
  facts.className = "requirement-facts";
  const factValues = [
    ["Eligibility", result.eligibility_status],
    ["Seniority gap", result.seniority_gap],
    ["Required experience", result.required_experience_years == null ? "Not explicitly stated" : `${result.required_experience_years} years`],
    ["Preferred experience", result.preferred_experience_years == null ? "Not explicitly stated" : `${result.preferred_experience_years} years`],
    ["Education", [result.education_level, textList(result.required_degree_fields, "")].filter(Boolean).join(" · ") || "Not explicitly stated"],
    ["Professional qualifications", textList([...(result.mandatory_qualifications || []), ...(result.preferred_qualifications || [])])],
    ["Languages", textList(result.language_requirements)],
    ["Keywords", textList([...(result.functional_keywords || []), ...(result.subject_matter_keywords || [])])],
  ];
  for (const [label, value] of factValues) {
    const row = document.createElement("p");
    const strong = document.createElement("strong");
    strong.textContent = `${label}: `;
    row.append(strong, document.createTextNode(value || "Not explicitly stated"));
    facts.appendChild(row);
  }
  wrapper.append(
    facts,
    detailSection("Why it may fit", result.key_fit_reasons, "No strong fit reason was extracted."),
    detailSection("Main gaps", result.main_gaps_or_risks, "No specific gap was extracted; verify the official requirements."),
  );
  const jd = document.createElement("details");
  jd.className = "vacancy-text";
  const summary = document.createElement("summary");
  summary.textContent = "View full demo vacancy description";
  const text = document.createElement("p");
  text.textContent = result.vacancy_text;
  jd.append(summary, text);
  wrapper.appendChild(jd);
  return wrapper;
}

function renderMonitorResults() {
  const retained = monitorAssessments.filter(notificationDecision);
  document.getElementById("monitor-empty").hidden = true;
  document.getElementById("monitor-error").hidden = true;
  document.getElementById("monitor-results").hidden = false;
  document.getElementById("digest-preview").hidden = false;
  setText("institutions-count", new Set(monitorAssessments.map((item) => item.institution)).size);
  setText("vacancies-count", monitorAssessments.length);
  setText("retained-count", retained.length);
  setText("digest-count", `${retained.length} of ${monitorAssessments.length} vacancies retained`);

  const list = document.getElementById("opportunity-list");
  list.replaceChildren();
  for (const result of monitorAssessments) {
    const retainedForDigest = notificationDecision(result);
    const card = document.createElement("details");
    card.className = `opportunity-card ${retainedForDigest ? "is-retained" : "is-filtered"}`;
    const summary = document.createElement("summary");
    summary.className = "opportunity-row";
    const identity = document.createElement("div");
    const institution = document.createElement("span");
    institution.className = "institution-name";
    institution.textContent = result.institution;
    const title = document.createElement("h4");
    title.textContent = result.title;
    const meta = document.createElement("p");
    meta.textContent = [result.location, result.employment_type, result.closing_date && `Deadline ${result.closing_date}`].filter(Boolean).join(" · ");
    identity.append(institution, title, meta);

    const scores = document.createElement("div");
    scores.className = "row-scores";
    scores.textContent = `Current ${result.current_score.toFixed(1)} · Long-Term ${result.long_term_score.toFixed(1)}`;
    const decision = document.createElement("span");
    decision.className = "decision-pill";
    decision.textContent = retainedForDigest ? "RETAINED" : "FILTERED OUT";
    summary.append(identity, scores, decision);
    card.append(summary, buildAssessmentDetails(result));
    list.appendChild(card);
  }

  const digest = document.getElementById("digest-jobs");
  const digestEmpty = document.getElementById("digest-empty");
  digest.replaceChildren();
  digestEmpty.hidden = retained.length !== 0;
  retained.forEach((result, index) => {
    const item = document.createElement("details");
    item.className = "digest-job";
    item.open = index === 0;
    const heading = document.createElement("summary");
    const identity = document.createElement("div");
    const institution = document.createElement("span");
    institution.className = "digest-institution";
    institution.textContent = result.institution;
    const title = document.createElement("h3");
    title.textContent = result.title;
    identity.append(institution, title);
    const action = document.createElement("span");
    action.textContent = result.recommended_action;
    heading.append(identity, action);
    const body = document.createElement("div");
    body.className = "digest-body";
    const headline = document.createElement("div");
    headline.className = "digest-scoreboard";
    const deadline = result.closing_date ? `Deadline: ${result.closing_date}` : "Deadline: not stated";
    headline.textContent = `${deadline}  |  Current score: ${result.current_score.toFixed(1)}/100 (${result.current_category})  |  Long-term score: ${result.long_term_score.toFixed(1)}/100 (${result.long_term_label})  |  Eligibility: ${result.eligibility_status}`;
    const actionLine = document.createElement("p");
    actionLine.className = "digest-action";
    actionLine.textContent = `Recommended action: ${result.recommended_action}`;
    const viability = document.createElement("section");
    viability.className = "digest-panel viability-panel";
    const viabilityTitle = document.createElement("h4");
    viabilityTitle.textContent = "Current application viability";
    const viabilityText = document.createElement("p");
    viabilityText.textContent = `${result.current_category}. Seniority gap: ${result.seniority_gap}. Core skill gaps: ${textList(result.main_gaps_or_risks)}.`;
    viability.append(viabilityTitle, viabilityText);
    const longTerm = document.createElement("section");
    longTerm.className = "digest-panel career-panel";
    const longTitle = document.createElement("h4");
    longTitle.textContent = "Long-term career value";
    const longText = document.createElement("p");
    longText.textContent = `${result.long_term_score.toFixed(1)}/100 (${result.long_term_label})`;
    longTerm.append(longTitle, longText);
    const brief = document.createElement("section");
    brief.className = "digest-copy";
    const briefTitle = document.createElement("h4");
    briefTitle.textContent = "Vacancy brief";
    const briefText = document.createElement("p");
    briefText.textContent = result.vacancy_text.split("\n").filter(Boolean).slice(0, 2).join(" ");
    brief.append(briefTitle, briefText);
    body.append(
      headline,
      actionLine,
      viability,
      longTerm,
      brief,
      buildAssessmentDetails(result),
    );
    const why = document.createElement("p");
    why.className = "why-notified";
    why.textContent = `Why notified: ${result.current_score >= Number(document.getElementById("current-threshold").value) ? "qualifying current application match" : "qualifying long-term career match"}.`;
    body.appendChild(why);
    item.append(heading, body);
    digest.appendChild(item);
  });
}

function updateThresholdLabels() {
  setText("current-threshold-value", document.getElementById("current-threshold").value);
  setText("long-term-threshold-value", document.getElementById("long-term-threshold").value);
  if (monitorAssessments.length) renderMonitorResults();
}

async function runMonitorBatch(vacancies) {
  pyodideRuntime.globals.set("candidate_json", JSON.stringify(candidateInput()));
  pyodideRuntime.globals.set("vacancies_json", JSON.stringify(vacancies));
  const output = await pyodideRuntime.runPythonAsync(
    "assess_browser_batch(candidate_json, vacancies_json)",
  );
  monitorAssessments = JSON.parse(output);
  renderMonitorResults();
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
    const jobsResponse = await fetch(DEMO_JOBS_URL);
    if (!jobsResponse.ok) throw new Error("Could not load the demo vacancies.");
    demoJobs = await jobsResponse.json();
    await pyodideRuntime.runPythonAsync(
      `import sys\nsys.path.insert(0, "/home/pyodide")\n${pythonBridge}`,
    );
    button.disabled = false;
    document.getElementById("monitor-button").disabled = false;
    buttonLabel.textContent = "Analyze opportunity";
    setText("monitor-button-label", "Run daily monitor simulation");
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

document.getElementById("monitor-button").addEventListener("click", async () => {
  const button = document.getElementById("monitor-button");
  button.disabled = true;
  setText("monitor-button-label", "Checking institutions and scoring vacancies…");
  try {
    await runMonitorBatch(demoJobs);
    document.getElementById("monitor-results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    document.getElementById("monitor-empty").hidden = true;
    document.getElementById("monitor-results").hidden = true;
    document.getElementById("monitor-error").hidden = false;
    setText("monitor-error-message", error instanceof Error ? error.message : String(error));
  } finally {
    button.disabled = false;
    setText("monitor-button-label", "Run daily monitor simulation");
  }
});

document.getElementById("current-threshold").addEventListener("input", updateThresholdLabels);
document.getElementById("long-term-threshold").addEventListener("input", updateThresholdLabels);

document.getElementById("cv-upload").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const status = document.getElementById("cv-status");
  status.textContent = "Reading the CV locally…";
  try {
    const text = await extractCvText(file);
    if (!text.trim()) throw new Error("No readable text was found in this file.");
    const detected = applyCvDraft(text);
    status.textContent = detected.length
      ? `Drafted ${detected.join(", ")} from ${file.name}. Review the fields before analysis.`
      : `Read ${file.name}, but no profile fields were confidently detected. Enter them manually.`;
  } catch (error) {
    status.textContent = error instanceof Error ? error.message : String(error);
  } finally {
    event.target.value = "";
  }
});

initializePython();
