import os
import re
import json
from dotenv import load_dotenv
from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

load_dotenv()
URL = os.getenv("CLOUDANT_URL")
API_KEY = os.getenv("CLOUDANT_API_KEY")
DB_NAME = os.getenv("CLOUDANT_DB_NAME")

authenticator = IAMAuthenticator(API_KEY)
client = CloudantV1(authenticator=authenticator)
client.set_service_url(URL)

# ==========================================
# STEP 1: The Absolute Dealbreakers (Cloudant)
# ==========================================
# Only put things here that the patient MUST have. 
# Keep it lightweight to pull a broader net of trials.
query_selector = {
    "OverallStatus": "RECRUITING",
    "StudyType": "INTERVENTIONAL",
    "Conditions": {"$regex": "(?i)Congenital Adrenal Hyperplasia"},
    
    # NEW DEALBREAKERS: The trial MUST allow Males (MALE or ALL)
    "Sex": {"$in": ["MALE", "ALL"]},
    
    # The trial MUST allow Adults 
    # (Regex catches "ADULT", "OLDER_ADULT", and "CHILD, ADULT")
    "Age": {"$regex": "(?i)ADULT"} 
}

print(f"Fetching mandatory matches from '{DB_NAME}'...")

try:
    response = client.post_find(
        db=DB_NAME,
        selector=query_selector,
        limit=1000, 
        fields=["_id", "BriefTitle", "Summary", "Locations", "Phases", "Sex", "Age"] 
    ).get_result()

    docs = response.get('docs', [])
    print(f"✅ Retrieved {len(docs)} trials that passed the dealbreakers.")

    # ==========================================
    # STEP 2: The "Nice-to-Have" Python Scorer
    # ==========================================
    # We define our optional preferences here
    optional_prefs = {
        "preferred_location": r"(?i)Maryland|Bethesda",
        "preferred_phase": r"(?i)PHASE2",
        "preferred_age": r"(?i)ADULT",
        "preferred_sex": r"(?i)FEMALE|ALL"
    }

    scored_trials = []

    for doc in docs:
        score = 0
        match_reasons = []

        # Safely extract fields
        loc = doc.get("Locations", "")
        phase = doc.get("Phases", "")
        age = doc.get("Age", "")
        sex = doc.get("Sex", "")

        # Give +1 point for every optional preference they hit
        if re.search(optional_prefs["preferred_location"], loc):
            score += 1
            match_reasons.append("Location Match")
            
        if re.search(optional_prefs["preferred_phase"], phase):
            score += 1
            match_reasons.append("Phase Match")
            
        if re.search(optional_prefs["preferred_age"], age):
            score += 1
            match_reasons.append("Age Match")
            
        if re.search(optional_prefs["preferred_sex"], sex):
            score += 1
            match_reasons.append("Sex Match")

        # Attach the score to the document
        doc["RelevanceScore"] = score
        doc["MatchedOptionals"] = match_reasons
        scored_trials.append(doc)

    # ==========================================
    # STEP 3: Sort by the Highest Score
    # ==========================================
    # Sorts the list so trials with the highest score are at index 0
    scored_trials.sort(key=lambda x: x["RelevanceScore"], reverse=True)

    print("\n🏆 Top 3 Best Fitting Trials:")
    for i, doc in enumerate(scored_trials[:3]):
        print(f"\n--- Rank {i+1} (Score: {doc['RelevanceScore']}/4) ---")
        print(f"Matched On: {', '.join(doc['MatchedOptionals']) if doc['MatchedOptionals'] else 'None of the optionals'}")
        print(f"ID: {doc['_id']}")
        print(f"Title: {doc.get('BriefTitle', 'No Title')}")

except Exception as e:
    print(f"❌ Query failed: {str(e)}")