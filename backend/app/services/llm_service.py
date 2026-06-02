import httpx
import time
import logging
from typing import Dict, Any, Tuple, Optional
from app.config.config import settings

logger = logging.getLogger(__name__)

# Model cost configurations (Price per 1M tokens in USD)
MODEL_PRICING = {
    "google/gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "google/gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "google/gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "google/gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 5.00, "output": 15.00},
    "openai/gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "openai/gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    "anthropic/claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "meta-llama/llama-3-8b-instruct": {"input": 0.05, "output": 0.05},
    "meta-llama/llama-3-70b-instruct": {"input": 0.59, "output": 0.79},
    "meta-llama/llama-3.1-8b-instruct": {"input": 0.05, "output": 0.05},
    "meta-llama/llama-3.1-70b-instruct": {"input": 0.52, "output": 0.75},
    "meta-llama/llama-3.1-405b-instruct": {"input": 2.66, "output": 2.66},
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek/deepseek-r1": {"input": 0.55, "output": 2.19},
    "qwen/qwen-2.5-7b-instruct": {"input": 0.05, "output": 0.05},
    "qwen/qwen-2.5-72b-instruct": {"input": 0.40, "output": 0.40},
    "qwen/qwen-2.5-coder-32b-instruct": {"input": 0.20, "output": 0.20},
    "mistralai/mistral-7b-instruct": {"input": 0.05, "output": 0.05},
    "mistralai/mixtral-8x7b-instruct": {"input": 0.24, "output": 0.24},
}

class LLMService:
    @staticmethod
    def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = MODEL_PRICING.get(model, {"input": 0.15, "output": 0.60}) # Fallback to mini-style pricing
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    @classmethod
    async def generate_response(
        cls,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False
    ) -> Tuple[str, float, Dict[str, int], float]:
        """
        Calls OpenRouter or local Ollama to generate a response.
        Returns:
            Tuple of (response_text, latency_ms, token_usage_dict, estimated_cost)
        """
        start_time = time.time()

        # Route to local Ollama if requested
        if model.startswith("ollama/"):
            ollama_model = model.replace("ollama/", "")
            ollama_url = "http://localhost:11434/api/chat"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": ollama_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_gpu": 0
                }
            }
            if json_mode:
                payload["format"] = "json"
                
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(ollama_url, json=payload)
                    if response.status_code == 200:
                        res_json = response.json()
                        text = res_json.get("message", {}).get("content", "").strip()
                        prompt_tokens = res_json.get("prompt_eval_count", 0) or len(prompt.split()) * 2
                        completion_tokens = res_json.get("eval_count", 0) or len(text.split()) * 2
                        token_usage = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens
                        }
                        latency_ms = (time.time() - start_time) * 1000
                        return text, latency_ms, token_usage, 0.0  # 0 cost for local models
                    else:
                        error_msg = f"Ollama returned error {response.status_code}: {response.text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
            except Exception as e:
                logger.error(f"Ollama call failed: {e}")
                raise Exception(f"Local Ollama evaluation failed: {e}. Please ensure Ollama is running and model '{ollama_model}' is pulled.")

        # If API key is empty, mock response to allow testing the dashboard offline
        if not settings.OPENROUTER_API_KEY:
            logger.warning("OPENROUTER_API_KEY is not configured. Returning mock response.")
            return cls._generate_mock_response(model, prompt, json_mode, start_time, system_prompt)
            
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/google-deepmind/ai-safety-guardrails",
            "X-Title": "AI Safety Guardrail Framework"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_body = response.text
                    logger.error(f"OpenRouter API Error {response.status_code}: {error_body}")
                    if response.status_code == 402:
                        raise Exception(f"API Key Budget Exceeded. Your OpenRouter/AICredits balance is $0. Please add credits at your provider dashboard, or switch to a local Ollama model.")
                    raise Exception(f"OpenRouter API Error (HTTP {response.status_code}): {error_body}")
                    
                result = response.json()
                
                # Extract text
                choices = result.get("choices", [])
                if not choices:
                    raise Exception("No choices returned from OpenRouter")
                text = choices[0].get("message", {}).get("content", "").strip()
                
                # Extract tokens
                usage = result.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                token_usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
                
                latency_ms = (time.time() - start_time) * 1000
                cost = cls.estimate_cost(model, prompt_tokens, completion_tokens)
                
                return text, latency_ms, token_usage, cost
                
            except Exception as e:
                logger.error(f"Failed to generate response from OpenRouter: {e}")
                if settings.OPENROUTER_API_KEY:
                    raise e
                # Fallback to mock for robust execution if network or API issues occur (offline demo mode)
                logger.info("Falling back to mock response due to missing API key / offline mode.")
                return cls._generate_mock_response(model, prompt, json_mode, start_time, system_prompt)

    @classmethod
    def _generate_mock_response(
        cls, 
        model: str, 
        prompt: str, 
        json_mode: bool, 
        start_time: float,
        system_prompt: Optional[str] = None
    ) -> Tuple[str, float, Dict[str, int], float]:
        import json
        time.sleep(0.05) # Simulate network lag
        latency_ms = (time.time() - start_time) * 1000
        
        prompt_tokens = len(prompt.split()) * 2
        
        if json_mode:
            prompt_lower = prompt.lower()
            system_prompt_lower = system_prompt.lower() if system_prompt else ""
            
            if "judge" in prompt_lower or "judge" in system_prompt_lower or "evaluat" in system_prompt_lower:
                # Determine candidate model
                cand_model = "unknown"
                if "Candidate Model:" in prompt:
                    try:
                        cand_model = prompt.split("Candidate Model:")[1].split("\n")[0].strip()
                    except Exception:
                        pass
                
                # Deterministic pseudo-random offset based on model size & prompt length
                offset = round(((len(prompt) % 7) - 3) * 0.1, 2) # ranges from -0.3 to +0.3
                
                if "claude" in cand_model or "gemini-2.5-pro" in cand_model or ("gpt-4o" in cand_model and "mini" not in cand_model):
                    base = 8.8
                elif "mini" in cand_model or "flash" in cand_model or "70b" in cand_model:
                    base = 7.8
                else:
                    base = 6.4
                
                score_val = base + offset
                rel = min(max(score_val + 0.4, 1.0), 10.0)
                corr = min(max(score_val + 0.1, 1.0), 10.0)
                comp = min(max(score_val - 0.2, 1.0), 10.0)
                clar = min(max(score_val + 0.3, 1.0), 10.0)
                cons = min(max(score_val + 0.2, 1.0), 10.0)
                adh = min(max(score_val, 1.0), 10.0)
                overall = (rel + corr + comp + clar + cons + adh) / 6.0
                
                strengths = ["Clear formatting and structures", "Accurate data parameters", "Coherent paragraphs"]
                weaknesses = ["Could use more code illustrations or examples" if overall < 8.0 else "None notable"]
                risks = []
                recommendations = ["Add code examples to back assertions" if overall < 8.0 else "Ready to serve"]
                justification = "The candidate model provided a coherent, accurate response directly answering the instructions of the prompt."
                
                text = f"""{{
                    "relevance": {round(rel, 1)},
                    "correctness": {round(corr, 1)},
                    "completeness": {round(comp, 1)},
                    "clarity": {round(clar, 1)},
                    "factual_consistency": {round(cons, 1)},
                    "instruction_adherence": {round(adh, 1)},
                    "overall_score": {round(overall, 1)},
                    "strengths": {json.dumps(strengths)},
                    "weaknesses": {json.dumps(weaknesses)},
                    "risks": {json.dumps(risks)},
                    "recommendations": {json.dumps(recommendations)},
                    "justification": "{justification}"
                }}"""
            elif "injection" in prompt_lower or "injection" in system_prompt_lower:
                text = '{"risk_score": 0.0, "status": "low", "threat_category": "None", "reason": "Bypassed"}'
            elif "jailbreak" in prompt_lower or "jailbreak" in system_prompt_lower:
                text = '{"jailbreak_score": 0.0, "status": "safe", "threat_category": "None", "reason": "Bypassed"}'
            elif "toxic" in prompt_lower or "toxic" in system_prompt_lower:
                text = '{"toxicity": 0.0, "explanation": "Bypassed"}'
            elif "hallucination" in prompt_lower or "hallucination" in system_prompt_lower:
                text = '{"hallucination_risk": 0.0, "explanation": "Bypassed"}'
            elif "adherence" in prompt_lower or "adherence" in system_prompt_lower:
                text = '{"adherence_score": 10.0, "explanation": "Bypassed"}'
            elif "compliance" in prompt_lower or "compliance" in system_prompt_lower:
                text = '{"compliance_score": 10.0, "explanation": "Bypassed"}'
            else:
                text = '{"message": "Mock JSON response"}'
        else:
            text = f"This is a simulated response generated from {model}. It answers the query with detailed explanations, simple examples, and clear structures suitable for quality evaluation benchmarks."
                
        completion_tokens = len(text.split()) * 2
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
        cost = cls.estimate_cost(model, prompt_tokens, completion_tokens)
        
        return text, latency_ms, token_usage, cost
