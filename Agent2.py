import os
import asyncio
from curl_cffi import requests

async def fetch_trial_details(nct_id: str):
    url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id.strip().upper()}"
    try:
        async with requests.AsyncSession(impersonate="chrome") as client:
            response = await client.get(url)
            if response.status_code != 200: return None
            data = response.json()
            protocol = data.get('protocolSection', {})
            elig_module = protocol.get('eligibilityModule', {})
            
            criteria = elig_module.get('eligibilityCriteria')
            if isinstance(criteria, dict):
                eligibility_text = criteria.get('textString', 'N/A')
            else:
                eligibility_text = str(criteria) if criteria else 'N/A'

            return {
                "id": nct_id,
                "title": protocol.get('identificationModule', {}).get('briefTitle', 'N/A'),
                "criteria": eligibility_text,
                "summary": protocol.get('descriptionModule', {}).get('briefSummary', 'N/A')
            }
    except Exception: return None

async def agent_2_analytical_processor(nct_id, user_question, client_llm):
    trial_data = await fetch_trial_details(nct_id)
    if not trial_data: return f"### [{nct_id}] Error: Data Fetch Failed."

    prompt = f"""You are a Lead Clinical Trial Strategist. Your goal is to provide a predictive, deep-dive match analysis.
Compare the PATIENT PROFILE against the TECHNICAL CRITERIA and justify the fit.

PATIENT PROFILE: 
{user_question}

TRIAL TECHNICAL DATA:
ID: {nct_id} | Title: {trial_data['title']}
Criteria: {trial_data['criteria']}

RESPONSE ARCHITECTURE:

### [{nct_id}] {trial_data['title']}

**1. Strategic Match Justification**
- [Explain the rank based on location and condition relevance. Why did this beat other trials?]

**2. Eligibility Mapping (Evidence vs. Requirement)**
List 4-5 critical requirements from the criteria. For each, apply this:
- **Requirement:** [Quote the exact technical text]
- **Status:** [Fulfilled / Unfulfilled / Unknown]
- **Evidence:** [Reference the patient's data. Explain the 'Why' behind the status.]

**3. Predictive Risk Assessment (The Dealbreakers)**
- [Identify hidden risks like medication interactions or lab thresholds that could disqualify this specific patient.]

**4. Proactive Clinical Action Plan (10 Steps Ahead)**
- **Immediate Step:** [The #1 lab or scan to get now.]
- **Doctor's Script:** [2 precise questions for their specialist.]
- **Document Dossier:** [Exact records needed for screening.]

---
[END OF EVALUATION]
"""
    return client_llm.generate_text(prompt=prompt)