import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from Agent1 import agent_1_orchestrator_access, get_watsonx_model
from Agent2 import agent_2_analytical_processor

load_dotenv()

app = FastAPI(title="ClinicalScout API")

# Allow React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client_llm = get_watsonx_model()


# Request and Response models
class PatientQuery(BaseModel):
    question: str


class TrialMatch(BaseModel):
    nct_id: str
    title: str
    justification: str


class SearchResponse(BaseModel):
    total_found: int
    trials: list[TrialMatch]


@app.get("/")
def health_check():
    return {"status": "ClinicalScout API is running"}


@app.post("/search", response_model=SearchResponse)
async def search_trials(query: PatientQuery):
    """
    Full pipeline using Orchestrator logic.
    Agent 1 finds top 20 trials.
    Agent 2 analyzes each against the patient profile sequentially.
    """

    print("\n" + "=" * 50)
    print("PHASE 1: AGENT 1 (Wide-Net Search & Ranking)")
    print("=" * 50)

    # Agent 1 — filter and rank trials from Cloudant
    top_20_trials = agent_1_orchestrator_access(query.question, client_llm)

    if not top_20_trials:
        print("No trials found matching the mandatory criteria.")
        return SearchResponse(total_found=0, trials=[])

    print(f"Agent 1 found {len(top_20_trials)} potential matches.")
    print("\n" + "=" * 50)
    print("PHASE 2: AGENT 2 (Deep Extraction & Fit Justification)")
    print("=" * 50)

    results = []

    # Agent 2 — sequential loop matching Orchestrator.py logic exactly
    for idx, trial in enumerate(top_20_trials, 1):
        nct_id = trial["_id"]
        print(f"[{idx}/{len(top_20_trials)}] Analyzing {nct_id} against patient profile...")

        try:
            justification = await agent_2_analytical_processor(
                nct_id, query.question, client_llm
            )

            # Skip if nothing was returned
            if not justification or not isinstance(justification, str):
                print(f"No analysis returned for {nct_id} — skipping")
                continue

            results.append(TrialMatch(
                nct_id=nct_id,
                title=trial.get("BriefTitle", "Unknown Trial"),
                justification=justification
            ))

            print(f"Analysis complete for {nct_id}")

        except Exception as e:
            print(f"Error analyzing {nct_id}: {e}")
            continue

    print("\n" + "=" * 50)
    print(f"Pipeline complete. Returning {len(results)} analyses.")
    print("=" * 50)

    return SearchResponse(total_found=len(results), trials=results)


@app.post("/quick-search")
async def quick_search(query: PatientQuery):
    """
    Fast endpoint — Agent 1 only, no deep analysis.
    Returns ranked trial list immediately for fast initial display.
    """

    print("\n" + "=" * 50)
    print("QUICK SEARCH: AGENT 1 ONLY")
    print("=" * 50)

    top_trials = agent_1_orchestrator_access(query.question, client_llm)
    print(f"Quick search returned {len(top_trials)} trials")

    return {
        "total_found": len(top_trials),
        "trials": [
            {
                "nct_id": t["_id"],
                "title": t.get("BriefTitle", "Unknown"),
                "score": t.get("RelevanceScore", 0),
                "location": t.get("Locations", "See registry"),
                "phase": t.get("Phases", "Unknown"),
                "study_url": t.get(
                    "StudyURL",
                    f"https://clinicaltrials.gov/study/{t['_id']}"
                )
            }
            for t in top_trials
        ]
    }
