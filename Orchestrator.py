import asyncio
import os
import json
from dotenv import load_dotenv
from Agent1 import agent_1_orchestrator_access, get_watsonx_model
from Agent2 import agent_2_analytical_processor

# 1. Initialization
load_dotenv()

async def main_clinical_scout_orchestrator():
    """
    Main pipeline: 
    1. Agent 1 finds the best 20 trials.
    2. Agent 2 analyzes them against the patient's specific bio-data.
    """
    client_llm = get_watsonx_model()
    
    # --- USER QUESTION (The Golden Thread) ---
    # This detailed question gives Agent 2 the data it needs to 'check the boxes'
    question = (
        "I am a 64-year-old female with Relapsing-Remitting Multiple Sclerosis (RRMS) "
        "living in San Francisco. I have been on Ocrevus for 18 months, but my last "
        "MRI showed active lesions. My EDSS score is 3.5. I have no history of "
        "chronic infections. Looking for trials in Northern California."
    )

    print("\n" + "="*50)
    print("PHASE 1: AGENT 1 (Wide-Net Search & Ranking)")
    print("="*50)
    
    # 1. Agent 1: Filter 500+ trials down to the top 20 ranked by proximity
    top_20_trials = agent_1_orchestrator_access(question, client_llm)

    if not top_20_trials:
        print("❌ No trials found matching the mandatory criteria.")
        return

    print(f"✅ Agent 1 found {len(top_20_trials)} potential matches.")
    print("\n" + "="*50)
    print("PHASE 2: AGENT 2 (Deep Extraction & Fit Justification)")
    print("="*50)

    # 2. Agent 2 Loop: Deep Dive via Live API
    final_report_path = "ClinicalScout_Consultant_Report.txt"
    
    with open(final_report_path, "w", encoding="utf-8") as f:
        f.write(f"CLINICAL SCOUT CONSULTANT REPORT\n")
        f.write(f"PATIENT PROFILE: {question}\n")
        f.write("="*80 + "\n\n")

        for idx, trial in enumerate(top_20_trials, 1):
            nct_id = trial['_id']
            print(f"[{idx}/20] Analyzing {nct_id} against patient profile...")
            
            # Agent 2 hits the Live API and justifies the fit
            try:
                justification = await agent_2_analytical_processor(nct_id, question, client_llm)
                
                # Write to file immediately to preserve progress
                f.write(justification + "\n\n")
                f.write("*"*80 + "\n\n")
            except Exception as e:
                print(f"⚠️ Error analyzing {nct_id}: {e}")
                continue

    print("\n" + "="*50)
    print(f"SUCCESS: Comprehensive report saved to '{final_report_path}'")
    print("="*50)

if __name__ == "__main__":
    # Ensure all async components (curl_cffi) run correctly
    asyncio.run(main_clinical_scout_orchestrator())