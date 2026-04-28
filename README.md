# ClinicalScout
### Autonomous Clinical Trial Matching Agent
**IBM SkillsBuild — AI Driven Industry Innovation | Spring 2026**

---

## Overview

ClinicalScout is an agentic AI solution that autonomously matches critically ill patients to actively recruiting clinical trials based on their full medical profile and real-world life constraints. Patients describe their situation once in plain language and the system handles everything — finding verified matches, reasoning through eligibility criteria, and generating a physician-ready summary — eliminating the navigational exhaustion and logistical barriers that prevent patients from accessing life-saving treatment opportunities.

The core innovation is not the model. It is the reasoning design. Existing tools retrieve trials for patients to evaluate. ClinicalScout evaluates trials for patients to decide.

---

## The Problem

Critically ill patients searching for clinical trials face three compounding failures that no existing tool addresses simultaneously:

- **Navigational Exhaustion** — Public databases return thousands of results with no plain-language guidance, no guided search, and no way to determine which results are worth a critically ill person's limited time and energy
- **Missed Life-Saving Opportunities** — Active and closed trials look identical. Patients invest time and hope in opportunities that stopped recruiting months ago with no way of knowing before they try
- **Logistical Incompatibility** — Patients confirm medical eligibility only to discover travel distance, weekday-only scheduling, or visit frequency makes participation impossible. The system never asked about their life

---

## Solution Architecture

ClinicalScout uses a two-agent decoupled architecture where each agent handles a fundamentally different type of problem.

```
Patient Narrative (Plain Language)
            |
            v
    +----------------+
    |    AGENT 1     |  IBM watsonx.ai Mistral Small
    |  Structured    |  Extracts structured data from narrative
    |  Extraction    |  Executes Mango Query against IBM Cloudant
    |  & Filtering   |  Ranks results by location + preference score
    +----------------+
            |
     Top 20 Trial IDs
            |
            v
    +----------------+
    |    AGENT 2     |  IBM watsonx.ai Llama 3 70B
    |   Semantic     |  Fetches full criteria from ClinicalTrials.gov API
    |   Reasoning    |  Reasons through eligibility against patient profile
    |  & Analysis    |  Generates plain-language eligibility assessment
    +----------------+
            |
            v
    Consultant Report (Patient + Physician Summary)
```

### Why Two Agents

**Agent 1** solves a filtering problem — binary, deterministic, rule-based. Is this trial recruiting? Is it within range? Does it allow the patient's age and sex? These questions have yes or no answers that require fast structured query execution, not semantic reasoning. Using a lightweight model with a NoSQL database is the right tool for a deterministic problem.

**Agent 2** solves a reasoning problem — probabilistic, contextual, and semantically complex. Does this patient's specific biomarker profile meet this trial's inclusion criteria as written in regulatory language? That cannot be answered with a database query. It requires retrieving the full clinical context and reasoning across it against the patient's specific medical history.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent 1 LLM | IBM watsonx.ai — Mistral Small 3.1 24B |
| Agent 2 LLM | IBM watsonx.ai — Llama 3.3 70B Instruct |
| Database | IBM Cloudant (NoSQL) — clinical trials dataset |
| Live Trial Data | ClinicalTrials.gov API v2 |
| Backend Framework | FastAPI (Python) |
| Frontend Framework | React.js |
| Markdown Rendering | react-markdown |
| HTTP Client | Axios |
| Async HTTP | curl-cffi |
| Environment Config | python-dotenv |
| Cloud Platform | IBM Cloud |

---

## Project Structure

```
Clinical-Scout/
│
├── .env                          # API credentials (never commit)
├── requirements.txt              # Python dependencies
│
├── Agent1.py                     # Wide-net search and ranking
├── Agent2.py                     # Deep eligibility analysis
├── Orchestrator.py               # Standalone pipeline runner
├── api.py                        # FastAPI backend server
├── db_connect.py                 # Cloudant query testing utility
│
└── clinicalscout-frontend/       # React frontend
    └── src/
        ├── App.js                # Root component and state
        ├── App.css               # Global styles
        └── components/
            ├── SearchForm.js     # Patient input form
            ├── TrialCard.js      # Trial result card with markdown
            └── LoadingSpinner.js # Loading state UI
```

---

## Setup and Installation

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- IBM Cloud account with watsonx.ai access
- IBM Cloudant instance with clinical trials database

### Backend Setup

**1. Clone the repository**
```bash
git clone https://github.com/your-username/Clinical-Scout.git
cd Clinical-Scout
```

**2. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**3. Create your .env file**
```
CLOUDANT_URL=your-cloudant-url
CLOUDANT_API_KEY=your-cloudant-api-key
CLOUDANT_DB_NAME=your-database-name
WATSONX_API_KEY=your-watsonx-api-key
WATSONX_PROJECT_ID=your-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

**4. Start the FastAPI server**
```bash
uvicorn api:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
API documentation available at `http://localhost:8000/docs`

### Frontend Setup

**1. Navigate to the frontend folder**
```bash
cd clinicalscout-frontend
```

**2. Install dependencies**
```bash
npm install
```

**3. Start the React development server**
```bash
npm start
```

The app will open at `http://localhost:3000`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check — confirms API is running |
| POST | `/search` | Full pipeline — Agent 1 + Agent 2 analysis |
| POST | `/quick-search` | Agent 1 only — fast ranked results |

### Example Request

```json
POST /search
{
  "question": "I am a 54-year-old female with stage III non-small cell lung cancer with an EGFR mutation. I have completed two rounds of chemotherapy with no response. ECOG status 1. I live in Chicago, Illinois and can travel up to 50 miles. Available weekday evenings and weekends. Looking for Phase II or III trials involving EGFR-targeted therapy."
}
```

### Example Response

```json
{
  "total_found": 5,
  "trials": [
    {
      "nct_id": "NCT06031688",
      "title": "Targeted Treatment for Advanced Non-Small Cell Lung Cancer",
      "justification": "### [NCT06031688] ...\n\n**1. Strategic Match Justification**\n..."
    }
  ]
}
```

---

## How It Works

**Step 1 — Patient describes their situation once**

The patient types a plain-language narrative describing their diagnosis, prior treatments, location, schedule, and preferences. No forms, no dropdown menus, no medical coding required.

**Step 2 — Agent 1 builds and executes a structured query**

Agent 1 uses IBM watsonx.ai Mistral Small to extract structured data from the narrative and convert it into a Mango Query for IBM Cloudant. It separates mandatory dealbreakers (condition, age, sex, recruiting status) from optional preferences (location, phase, intervention type) and returns up to 500 trials filtered by hard constraints, then ranks them by relevance score.

**Step 3 — Agent 2 performs deep eligibility analysis**

For each top-ranked trial, Agent 2 fetches the full inclusion and exclusion criteria from the ClinicalTrials.gov live API, then uses IBM watsonx.ai Llama 3 70B to reason through whether the patient meets each requirement. It produces a structured analysis covering strategic match justification, eligibility mapping with evidence, predictive risk assessment, and a proactive clinical action plan.

**Step 4 — Results render in the frontend**

The React frontend displays each trial as a collapsed card showing a plain-text preview. The full analysis expands on click, rendered as clean formatted text with no special characters. Each card links directly to the trial on ClinicalTrials.gov.

---

## Sample Test Prompts

**Lung Cancer — Chicago**
```
I am a 54-year-old female with stage III non-small cell lung cancer with an EGFR mutation. I have completed two rounds of chemotherapy with no response. ECOG status 1. I live in Chicago, Illinois and can travel up to 50 miles. Available weekday evenings and weekends. Looking for Phase II or III trials involving EGFR-targeted therapy.
```

**Multiple Sclerosis — San Francisco**
```
I am a 64-year-old female with Relapsing-Remitting Multiple Sclerosis living in San Francisco. I have been on Ocrevus for 18 months but my last MRI showed active lesions. My EDSS score is 3.5. I have no history of chronic infections. Looking for trials in Northern California.
```

**Colorectal Cancer — Houston**
```
I am a 47-year-old male with stage IV colorectal cancer. I have completed 6 months of FOLFOX chemotherapy but my CEA markers are rising. I live in Houston, Texas and can travel up to 40 miles. Available any day of the week. Looking for Phase II or III trials involving immunotherapy or targeted therapy.
```

---

## Design Methodology

ClinicalScout was designed using IBM Enterprise Design Thinking across a 10-week development cycle. Key activities included:

- **Empathy Mapping** — Identified the target user Natalie Beck, a 54-year-old Senior Project Manager and Stage III cancer patient, and mapped her says, thinks, does, and feels across the trial search journey
- **As-Is Scenario Mapping** — Mapped the five-stage broken journey from database login through emotional defeat, identifying three core friction points: Navigational Exhaustion, Missed Life-Saving Opportunities, and Logistical Incompatibility
- **How Might We Ideation** — Generated 7 HMW statements from the friction points and pain points identified in research
- **Big Idea Vignettes** — Created experience-level solution concepts for each HMW
- **Clustering and Prioritization** — Grouped ideas into four clusters and ranked by Value Proposition and AI Justification
- **To-Be Scenario Mapping** — Mapped the transformed five-stage future experience showing the emotional arc from relief to confidence

---

## Key Design Decisions

**Why sequential Agent 2 processing instead of concurrent**
Agent 2 makes a live API call to ClinicalTrials.gov and runs an LLM generation for each trial. Running 20 concurrent calls risks hitting watsonx.ai rate limits and silently dropping results. Sequential processing ensures every trial completes before the next begins, matching the proven Orchestrator pipeline logic.

**Why IBM Cloudant instead of PostgreSQL**
The clinical trials dataset is document-oriented with variable fields across studies. Cloudant's Mango Query syntax supports regex matching on document fields directly, making it ideal for flexible condition and location matching without requiring a fixed schema.

**Why separate models for each agent**
Agent 1 needs fast, reliable JSON generation from a structured prompt. Agent 2 needs deep multi-step clinical reasoning over long eligibility criteria documents. Using a smaller faster model for Agent 1 reduces latency and avoids context deadline timeouts on the routing task, while preserving the larger model's capacity for the genuinely complex reasoning in Agent 2.

---

## Limitations and Future Work

**Current MVP limitations:**
- Agent 2 analysis is sequential — processing 20 trials takes 5 to 10 minutes
- No persistent patient profile — users must re-enter their narrative each session
- No proactive monitoring — the agent matches on demand rather than alerting when new trials open
- No EHR integration — patients describe their history manually rather than importing from hospital records
- No HIPAA-compliant production deployment — operates on public data only

**Planned post-MVP features:**
- Background autonomous monitoring with proactive alerts when new matching trials open
- Direct integration with hospital patient portal APIs for automatic medical record import
- Physician-facing interface delivering summaries directly into clinical workflow
- HIPAA-compliant production deployment on IBM Cloud with zero-retention LLM environments
- Multi-language support for non-English speaking patients

---

## Team

**Wolfpack AI — IBM SkillsBuild Spring 2026**
- Jagadeshwar Muthukumaran
- Rishi Senthil Kumar

---

## Acknowledgements

Built on IBM watsonx.ai, IBM Cloudant, and IBM Cloud as part of the IBM SkillsBuild AI Driven Industry Innovation program. Clinical trial data sourced from ClinicalTrials.gov, a resource provided by the U.S. National Library of Medicine.
