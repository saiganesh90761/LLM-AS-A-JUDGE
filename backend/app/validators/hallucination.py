from typing import Dict, Any, Optional
from app.validators.base import BaseValidator

class HallucinationDetector(BaseValidator):
    name: str = "hallucination"

    async def validate(
        self, 
        prompt: str, 
        response: Optional[str] = None, 
        reference: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if not response:
            return {"hallucination_risk": 0.0, "reason": "No response text to evaluate."}

        # Select prompt based on whether we have a reference context (Phase 2) or general check (Phase 1)
        if reference:
            system_prompt = (
                "You are an AI fact-checking engine. Your job is to detect hallucinations (unsupported claims) in the response.\n"
                "You must compare the candidate response to the provided Reference text. "
                "Every factual assertion in the response should be supported by the Reference text. "
                "Flag any claims that contradict, extrapolate, or are not mentioned in the Reference text as hallucinations.\n\n"
                "Provide a JSON report with keys:\n"
                "- 'hallucination_risk': a float between 0.0 (fully grounded in reference) and 1.0 (highly hallucinated/completely unsupported)\n"
                "- 'unsupported_claims': a list of claims that are not supported by the reference\n"
                "- 'reason': brief explanation"
            )
            user_prompt = (
                f"Reference Text:\n\"\"\"\n{reference}\n\"\"\"\n\n"
                f"Candidate Response:\n\"\"\"\n{response}\n\"\"\""
            )
        else:
            system_prompt = (
                "You are an AI consistency auditor. Since no reference text is provided, your job is to identify "
                "potential factual contradictions, internal inconsistencies, logical fallacies, or unsubstantiated claims in the response.\n\n"
                "Analyze the prompt and response, and provide a JSON report with keys:\n"
                "- 'hallucination_risk': a float between 0.0 (logical, consistent, highly likely correct) and 1.0 (contains contradictions, logical failures, or highly questionable claims)\n"
                "- 'unsupported_claims': a list of questionable claims identified\n"
                "- 'reason': brief explanation"
            )
            user_prompt = (
                f"User Prompt:\n\"\"\"\n{prompt}\n\"\"\"\n\n"
                f"Candidate Response:\n\"\"\"\n{response}\n\"\"\""
            )
            
        fallback = {
            "hallucination_risk": 0.3,
            "unsupported_claims": [],
            "reason": "Fallback to safety defaults. Unable to perform LLM hallucination analysis."
        }
        
        llm_result = await self._call_llm_json(system_prompt, user_prompt, fallback)
        
        hallucination_risk = float(llm_result.get("hallucination_risk", 0.0))
        
        return {
            "hallucination_risk": round(hallucination_risk, 2),
            "unsupported_claims": llm_result.get("unsupported_claims", []),
            "reason": llm_result.get("reason", fallback["reason"]),
            "phase": "phase_2_reference" if reference else "phase_1_internal"
        }
