import json
import logging
from typing import Dict, Any, Optional
from app.services.llm_service import LLMService
from app.config.config import settings

logger = logging.getLogger(__name__)

class BaseValidator:
    name: str = "base_validator"

    def __init__(self):
        # We can use the default candidate model or a cheaper model for validation
        self.validator_model = settings.DEFAULT_CANDIDATE_MODEL

    async def validate(
        self, 
        prompt: str, 
        response: Optional[str] = None, 
        reference: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Executes validation. Must be overridden by subclasses.
        Returns:
            Dict containing the validator output scores and metadata.
        """
        raise NotImplementedError("Subclasses must implement the validate method")

    async def _call_llm_json(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        fallback_value: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Helper method to get structured JSON output from the LLM.
        """
        raw_text = ""
        try:
            raw_text, _, _, _ = await LLMService.generate_response(
                model=self.validator_model,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0, # Use temperature 0.0 for consistent evaluations
                max_tokens=512, # Validators return small JSON, keep token usage low
                json_mode=True
            )
            
            # Clean up JSON formatting if LLM wraps it in markdown code blocks
            clean_text = raw_text.strip()
            first_brace = clean_text.find('{')
            last_brace = clean_text.rfind('}')
            if first_brace != -1 and last_brace != -1:
                clean_text = clean_text[first_brace:last_brace + 1]
            else:
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
            
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Error in validator {self.name} LLM call: {e}. Raw response: {raw_text}")
            return fallback_value
