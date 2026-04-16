import os
import re
import json
from dotenv import load_dotenv
from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# 1. Load Environment Variables
load_dotenv()

# Cloudant Config
CLOUDANT_URL = os.getenv("CLOUDANT_URL")
CLOUDANT_API_KEY = os.getenv("CLOUDANT_API_KEY")
CLOUDANT_DB_NAME = os.getenv("CLOUDANT_DB_NAME")

# Watsonx Config
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_URL = os.getenv("WATSONX_URL") # Update if your region is different

# 2. Initialize Watsonx Model
def get_watsonx_model():
    credentials = {
        "url": WATSONX_URL,
        "apikey": WATSONX_API_KEY
    }
    
    # We use a low temperature for strict, reliable JSON generation
    parameters = {
        GenParams.DECODING_METHOD: "greedy",
        GenParams.MAX_NEW_TOKENS: 4096,
        GenParams.TEMPERATURE: 0.0, 
        GenParams.STOP_SEQUENCES: ["\n\nFound", "\n\nNote:", "[END OF RESPONSE]"]
    }
    
    # Llama 3 70B is excellent at strict JSON and logic routing
    return ModelInference(
        model_id="meta-llama/llama-3-3-70b-instruct", 
        params=parameters,
        credentials=credentials,
        project_id=WATSONX_PROJECT_ID
    )

client_llm = get_watsonx_model()

# 3. System Prompts
routing_prompt = """You are an expert medical data router. Convert the user's natural language request for clinical trials into a strict JSON routing object.
The database is IBM Cloudant (NoSQL). You must separate the user's requirements into "mandatory" (dealbreakers) and "optional" (preferences).

<schema>
table: clinical_trials
fields:
_id: string
OverallStatus: string set to in one of the following: UNKNOWN, RECRUITING, NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, ENROLLING_BY_INVITATION, AVAILABLE, APPROVED_FOR_MARKETING
StudyType: string (always set to "INTERVENTIONAL")
Conditions: string uses regex for matching (e.g., "(?i)Type 2 Diabetes|Hyperglycemia")
Sex: string (MALE, FEMALE, or ALL)
Age: string ((CHILD), (ADULT), (OLDER_ADULT), (ADULT, OLDER_ADULT), (CHILD, ADULT), (CHILD, ADULT, OLDER_ADULT), )
Phases: string (EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4, PHASE1 | PHASE2, PHASE2 | PHASE3)
Locations: string (e.g., Boston, Maryland) 
Interventions: string (e.g., Metformin, Insulin)
PrimaryOutcomes, SecondaryOutcomes, OtherOutcomes: string 
</schema>

Rules:
1. MEDICAL DEALBREAKERS (Conditions, Age, Sex, Study Type, StudyStatus) MUST go in the "mandatory" object using Mango Query syntax. Use pipe-separated keywords in regex to ensure we capture the maximum number of matches (e.g., "(?i)Diabetes|T2DM").
2. LOGISTICAL PREFERENCES (Locations, Phases, Brief Summary, Interventions) MUST go in the "optional" object as raw Regex strings.
3. Only output the JSON inside <JSON></JSON> tags. Nothing else.

Example Output:
User Prompt "I am looking for an actively recruiting trial for a male adult with Type 2 Diabetes. I would prefer a Phase 3 trial, ideally located in Maryland or Virginia. I'm interested in trials involving GLP-1 agonists and tracking A1C levels."
JSON Output:
{
    "mandatory": {
        "OverallStatus": "RECRUITING",
        "StudyType": "INTERVENTIONAL",
        "Conditions": {
            "$regex": "(?i)Type 2 Diabetes|Hyperglycemia|T2DM"
        },
        "Sex": {
            "$in": ["MALE", "ALL"]
        },
        "Age": {
            "$regex": "(?i)ADULT"
        }
    },
    "optional": {
        "Phases": "(?i)PHASE3",
        "Locations": "(?i)Maryland|Virginia",
        "Interventions": "(?i)GLP-1|Semaglutide",
        "PrimaryOutcomes": "(?i)A1C|HbA1c"
    }
}
</JSON>
"""

comprehension_prompt = """You are a clinical trial matching assistant. You will be provided with a patient's QUESTION and the resulting DATA from our database.
The data contains the top-ranked trials based on their preferences. 
Reply based ONLY on the data provided. Do not invent trials.

CRITICAL: You MUST list EVERY trial provided in the DATA, up to 20 results. If the data contains 20 trials, you must display all 20.

Format your response exactly like this:
Found [X] highly relevant trials for you. Here are the top matches:

1. [BriefTitle] 
   - Summary: [Brief Summary] Summarize the trial in 1-2 sentences.
   - Interventions: [Interventions]
   - Phase: [Phases]
   - Location: [Summarize the locations. Limit to top 2 specific cities/hospitals mentioned in the data.]
   - ID: [_id]
   - Link: [StudyURL]

CRITICAL RULES:
1. OUTPUT ONLY THE FINAL RESPONSE. 
2. DO NOT include meta-commentary or "Note" sections.
3. After you print the Link for the final trial, you MUST immediately print exactly "[END OF RESPONSE]" on a new line and stop.
"""

# 4. Chain Functions
def generate_query_json(question):
    """Passes the user prompt to Watsonx to generate the JSON routing object."""
    formatted_prompt = f"{routing_prompt}\n\nUser Request: {question}\n\nGenerate JSON:"
    response = client_llm.generate_text(prompt=formatted_prompt)
    return response

def run_cloudant_and_rank(routing_data):
    authenticator = IAMAuthenticator(os.getenv("CLOUDANT_API_KEY"))
    client = CloudantV1(authenticator=authenticator)
    client.set_service_url(os.getenv("CLOUDANT_URL"))

    mandatory_query = routing_data.get("mandatory", {})
    optional_prefs = routing_data.get("optional", {})
    target_location = optional_prefs.get("Locations", "").replace("(?i)", "")

    try:
        response = client.post_find(
            db=os.getenv("CLOUDANT_DB_NAME"),
            selector=mandatory_query,
            limit=500,
            fields=["_id", "BriefTitle", "Locations", "Phases", "Sex", "Age", "StudyURL", "Interventions", "Brief Summary"]
        ).get_result()

        docs = response.get('docs', [])
        scored_trials = []
        for doc in docs:
            score = 0
            raw_locs = str(doc.get("Locations", ""))
            if target_location and re.search(target_location, raw_locs, re.IGNORECASE):
                # Clean locations to only show relevant ones for Agent 2's context
                matches = re.findall(rf"[^|]*{target_location}[^|]*", raw_locs, re.IGNORECASE)
                doc["Locations"] = " | ".join(matches[:2])
                score += 10
            
            for field, pattern in optional_prefs.items():
                if field != "Locations" and re.search(str(pattern), str(doc.get(field, "")), re.IGNORECASE):
                    score += 1
            doc["RelevanceScore"] = score
            scored_trials.append(doc)

        scored_trials.sort(key=lambda x: x["RelevanceScore"], reverse=True)
        return scored_trials[:20]
    except Exception as e:
        print(f"Cloudant Error: {e}")
        return []

def agent_1_orchestrator_access(question, client_llm):
    """The entry point for Orchestrator.py"""
    formatted_prompt = f"{routing_prompt}\n\nUser Request: {question}\n\nGenerate JSON:"
    response = client_llm.generate_text(prompt=formatted_prompt)
    
    match = re.search(r"<JSON>(.*?)</JSON>", response, re.DOTALL)
    if not match: return []
    
    routing_data = json.loads(match.group(1).strip())
    return run_cloudant_and_rank(routing_data)