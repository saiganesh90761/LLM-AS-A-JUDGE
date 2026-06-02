from typing import Dict, Any, Optional
from app.validators.base import BaseValidator

class InstructionAdherenceChecker(BaseValidator):
    name: str = "instruction_adherence"

    async def validate(
        self, 
        prompt: str, 
        response: Optional[str] = None, 
        reference: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if not response:
            return {"adherence_score": 0.0, "reason": "No response text to evaluate."}
            
        system_prompt = (
            "You are an AI quality assurance system. Your job is to check if the generated response adhered "
            "to all explicit and implicit instructions, formatting constraints, length limits, and rules specified in the prompt.\n\n"
            "Assess the prompt and the response. Respond in JSON format with keys:\n"
            "- 'adherence_score': a float between 0.0 (completely ignored instructions) and 10.0 (perfect adherence)\n"
            "- 'missed_instructions': a list of instructions/constraints that the response failed to follow\n"
            "- 'reason': brief explanation of the score"
        )
        
        user_prompt = (
            f"User Prompt (Instructions):\n\"\"\"\n{prompt}\n\"\"\"\n\n"
            f"Generated Response (To check):\n\"\"\"\n{response}\n\"\"\""
        )
        
        fallback = {
            "adherence_score": 5.0,
            "missed_instructions": [],
            "reason": "Fallback default. Unable to determine instruction adherence via LLM."
        }
        
        llm_result = await self._call_llm_json(system_prompt, user_prompt, fallback)
        
        adherence_score = float(llm_result.get("adherence_score", 5.0))
        
        return {
            "adherence_score": round(adherence_score, 1),
            "missed_instructions": llm_result.get("missed_instructions", []),
            "reason": llm_result.get("reason", fallback["reason"])
        }
