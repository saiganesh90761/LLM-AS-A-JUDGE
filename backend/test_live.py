import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env variables explicitly for script running
load_dotenv()

# Fix Windows terminal printing emoji/unicode encoding crashes
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app.database.db import SessionLocal, Base, engine

from app.services.pipeline import EvaluationPipeline

async def run_live_test():
    # Make sure SQLite tables are initialized
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    pipeline = EvaluationPipeline()
    
    prompt = "Hello! Write a 1-sentence poem about the ocean."
    print(f"Submitting prompt: '{prompt}'")
    print("Calling OpenRouter with candidate model (Gemini 2.5 Flash) and judge model (Gemini 2.5 Pro)...")
    
    try:
        res = await pipeline.run(
            db=db,
            prompt_text=prompt,
            candidate_model="google/gemini-2.5-flash",
            judge_model="google/gemini-2.5-pro"
        )
        
        print("\n=== EVALUATION REPORT ===")
        print(f"Decision: {res['decision']}")
        print(f"Reason: {res['decision_reason']}")
        print(f"Response: {res['response']}")
        print("\n--- Judge Scores ---")
        for k, v in res['judge'].items():
            if isinstance(v, (int, float)):
                print(f"  {k.capitalize()}: {v}/10")
                
        print("\n--- Safety Validator Scores ---")
        for k, v in res['validators'].items():
            print(f"  {k.replace('_', ' ').capitalize()}: {v.get('score', v.get('toxicity', v.get('risk_score', v.get('jailbreak_score', 0))))} ({v.get('status', 'safe')})")
            
        print("\n--- Explainability Details ---")
        print(f"  Justification: {res['judge'].get('justification')}")
        print(f"  Strengths: {res['judge'].get('strengths', [])}")
        print(f"  Weaknesses: {res['judge'].get('weaknesses', [])}")
        
    except Exception as e:
        print(f"\nPipeline failed: {e}")
        
    finally:
        db.close()
        engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_live_test())
