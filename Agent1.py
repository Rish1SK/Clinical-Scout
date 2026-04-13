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
        GenParams.MAX_NEW_TOKENS: 1024,
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
Conditions: string uses regex for matching (e.g., "(?i)Congenital Adrenal Hyperplasia")
Sex: string (MALE, FEMALE, or ALL)
Age: string ((CHILD), (ADULT), (OLDER_ADULT), (ADULT, OLDER_ADULT), (CHILD, ADULT), (CHILD, ADULT, OLDER_ADULT), )
Phases: string (EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4, PHASE1 | PHASE2, PHASE2 | PHASE3) use in if mentioned in the user prompt
Locations: string (e.g., Boston, Maryland) use regex for matching if mentioned in the user prompt
Interventions: string (e.g., specific drug names or procedures) use regex for matching if mentioned in the user prompt
PrimaryOutcomes: string (e.g., "Change in 17-hydroxyprogesterone levels") 
SecondaryOutcomes: string (e.g., "Incidence of adrenal crisis") 
OtherOutcomes: string (e.g., "Quality of life assessments") 
For all three outcome measure fields, use regex for matching if the user mentions specific outcomes they care about.
</schema>

Rules:
1. MEDICAL DEALBREAKERS (Conditions, Age, Sex, Study Type, StudyStatus) MUST go in the "mandatory" object using Mango Query syntax (e.g., {"$regex": "(?i)cancer"}).
2. LOGISTICAL PREFERENCES (Locations, Phases, Brief Summary, Interventions) MUST go in the "optional" object as raw Regex strings (e.g., "(?i)Boston").
3. Only output the JSON inside <JSON></JSON> tags. Nothing else.

Example Output:
User Prompt "I am looking for an actively recruiting trial for a female child with Congenital Adrenal Hyperplasia. I would prefer an early-stage trial, maybe Phase 1 or Phase 2, ideally located around Boston or New York. It would be great if the intervention involves Hydrocortisone, and I really want the outcome to track 'bone age' or 'growth'."
JSON Output:
{
    "mandatory": {
        "OverallStatus": "RECRUITING",
        "StudyType": "INTERVENTIONAL",
        "Conditions": {
            "$regex": "(?i)Congenital Adrenal Hyperplasia"
        },
        "Sex": {
            "$in": ["FEMALE", "ALL"]
        },
        "Age": {
            "$regex": "(?i)CHILD"
        }
    },
    "optional": {
        "Phases": "(?i)PHASE1|PHASE2",
        "Locations": "(?i)Boston|New York",
        "Interventions": "(?i)Hydrocortisone",
        "PrimaryOutcomes": "(?i)bone age|growth",
        "SecondaryOutcomes": "(?i)bone age|growth",
        "OtherOutcomes": "(?i)bone age|growth",
    }
}
</JSON>
"""

comprehension_prompt = """You are a clinical trial matching assistant. You will be provided with a patient's QUESTION and the resulting DATA from our database.
The data contains the top-ranked trials based on their preferences. 
Reply based ONLY on the data provided. Do not invent trials.

Format your response exactly like this:
Found [X] highly relevant trials for you. Here are the top matches:

1. [BriefTitle] 
   - Summary: [Brief Summary] Summarize the trial in 1-2 sentences, focusing on the intervention and outcomes.
   - Interventions: [Interventions]
   - Phase: [Phases]
   - Location: [Summarize the locations. If the user asked for a specific place, ONLY list that specific hospital/city. If they didn't ask for a location, just say "Multiple global sites" or list the top 2 cities and add "and others". NEVER list more than 2 locations.]
   - ID: [_id]
   - Link: [StudyURL]

CRITICAL RULES:
1. OUTPUT ONLY THE FINAL RESPONSE. 
2. DO NOT include any internal thoughts, self-corrections, or meta-commentary.
3. DO NOT use phrases like "Note:", "Here is the revised response", or discuss your formatting. 
4. After you print the Link for the final trial, you MUST immediately print exactly "[END OF RESPONSE]" on a new line and stop.

CRITICAL INSTRUCTION: Stop generating text immediately after printing the final trial ID. Do not write any closing remarks or repeat the list.
"""

# 4. Chain Functions
def generate_query_json(question):
    """Passes the user prompt to Watsonx to generate the JSON routing object."""
    formatted_prompt = f"{routing_prompt}\n\nUser Request: {question}\n\nGenerate JSON:"
    response = client_llm.generate_text(prompt=formatted_prompt)
    return response

def run_cloudant_and_rank(routing_data):
    """Executes the Fetch & Rank logic against Cloudant."""
    authenticator = IAMAuthenticator(CLOUDANT_API_KEY)
    client = CloudantV1(authenticator=authenticator)
    client.set_service_url(CLOUDANT_URL)

    mandatory_query = routing_data.get("mandatory", {})
    optional_prefs = routing_data.get("optional", {})

    print(f"Executing Cloudant Fetch with: {mandatory_query}")
    
    try:
        # Step 1: Fetch
        response = client.post_find(
            db=CLOUDANT_DB_NAME,
            selector=mandatory_query,
            limit=500,
            fields=["_id", "BriefTitle", "Locations", "Phases", "Sex", "Age", "StudyURL", "Interventions", "Brief Summary"]
        ).get_result()

        docs = response.get('docs', [])
        total_matches = len(docs)
        
        if total_matches == 0:
            return 0, []

        # Step 2: Rank
        scored_trials = []
        for doc in docs:
            score = 0
            # Check each optional preference against the document fields
            for field, regex_pattern in optional_prefs.items():
                doc_value = str(doc.get(field, ""))
                if re.search(regex_pattern, doc_value):
                    score += 1
            
            doc["RelevanceScore"] = score
            scored_trials.append(doc)

        # Sort by highest score
        scored_trials.sort(key=lambda x: x["RelevanceScore"], reverse=True)
        
        # Return the total count, and just the top 5 matches to keep the LLM context clean
        return total_matches, scored_trials[:5]

    except Exception as e:
        print(f"Cloudant Error: {str(e)}")
        return 0, None

def data_comprehension(question, total_matches, top_docs):
    """Passes the ranked results back to Watsonx for natural language formatting."""
    context_string = json.dumps(top_docs, indent=2)
    formatted_prompt = f"{comprehension_prompt}\n\nQUESTION: {question}\nTOTAL MATCHES: {total_matches}\nDATA: {context_string}\n\nResponse:"
    
    response = client_llm.generate_text(prompt=formatted_prompt)
    return response

def trial_matching_chain(question):
    """The main orchestration function."""
    print("1. Generating Database Routing Logic...")
    llm_output = generate_query_json(question)
    
    # Extract JSON using Regex
    pattern = r"<JSON>(.*?)</JSON>"
    matches = re.findall(pattern, llm_output, re.DOTALL)

    if not matches:
        return "Sorry, the AI could not parse the search parameters. Please try rephrasing your medical request."

    routing_json = matches[0].strip()
    
    try:
        routing_data = json.loads(routing_json)
    except json.JSONDecodeError:
        return "Sorry, there was an error decoding the database parameters."

    print("2. Fetching and Ranking from Cloudant...")
    total_count, top_docs = run_cloudant_and_rank(routing_data)
    
    if top_docs is None:
        return "Sorry, there was a problem executing the database query."
    
    if total_count == 0:
        return "No clinical trials found matching those strict medical requirements."

    print(f"Found {total_count} viable trials. Formatting output...")
    
    print("3. Generating Final Summary...")
    answer = data_comprehension(question, total_count, top_docs)
    return answer

if __name__ == "__main__":
    # Test the Agent Chain
    question = "I am a male adult with Congenital Adrenal Hyperplasia. I would prefer a Phase 2 trial, ideally somewhere in Maryland."
    
    final_answer = trial_matching_chain(question)
    
    print("\n================ FINAL RESPONSE ================\n")
    print(final_answer)