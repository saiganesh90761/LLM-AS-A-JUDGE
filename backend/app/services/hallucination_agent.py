import json
import logging
import time
import httpx
from typing import Dict, Any, List, Optional
from app.config.config import settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

def clean_and_parse_json(text: str) -> Any:
    """
    Cleans markdown backticks and extracts the JSON object/array from raw text before parsing.
    """
    clean = text.strip()
    # Search for first and last curly braces for objects
    first_brace = clean.find('{')
    last_brace = clean.rfind('}')
    if first_brace != -1 and last_brace != -1:
        clean = clean[first_brace:last_brace + 1]
    else:
        # Search for first and last square brackets for arrays
        first_bracket = clean.find('[')
        last_bracket = clean.rfind(']')
        if first_bracket != -1 and last_bracket != -1:
            clean = clean[first_bracket:last_bracket + 1]
        else:
            # Strip standard markdown blocks
            if clean.startswith("```json"):
                clean = clean[7:]
            elif clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()
    return json.loads(clean)

class HallucinationAgent:
    def __init__(self, judge_model: Optional[str] = None):
        self.judge_model = judge_model or settings.DEFAULT_JUDGE_MODEL

    async def extract_claims(self, prompt: str, response: str) -> List[Dict[str, Any]]:
        """
        Analyzes prompt and response and extracts verifiable factual claims.
        Each claim will have a 'claim' and a 'search_query'.
        """
        system_prompt = (
            "You are an expert fact-checking coordinator. Your task is to analyze the user's prompt and the model's response, "
            "and extract the 3 to 5 key verifiable factual claims made in the response. "
            "For each claim, write a short, highly-optimized search engine query that can be used to verify that specific claim.\n\n"
            "Return a JSON object with a single key 'claims' which is a list of objects, each containing:\n"
            "- 'claim': The precise factual claim extracted from the response (keep it concise, e.g. 'Argentina won the 2022 World Cup').\n"
            "- 'search_query': A concise, keyword-based search query to verify the claim (e.g. 'Argentina FIFA World Cup winner 2022').\n"
            "Ensure the output is strictly valid JSON."
        )

        user_content = (
            f"User Prompt: {prompt}\n\n"
            f"Model Response: {response}"
        )

        fallback = {
            "claims": [
                {
                    "claim": "General factual content in response.",
                    "search_query": prompt[:50]
                }
            ]
        }

        try:
            text, _, _, _ = await LLMService.generate_response(
                model=self.judge_model,
                prompt=user_content,
                system_prompt=system_prompt,
                temperature=0.2,
                json_mode=True
            )
            data = clean_and_parse_json(text)
            return data.get("claims", fallback["claims"])
        except Exception as e:
            logger.error(f"Error extracting claims: {e}")
            return fallback["claims"]

    async def search_google(self, query: str) -> List[Dict[str, str]]:
        """
        Executes Google Custom Search, falling back to LLM-generated search simulation if credentials are missing.
        """
        if settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID:
            try:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": settings.GOOGLE_API_KEY,
                    "cx": settings.GOOGLE_CSE_ID,
                    "q": query
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("items", [])
                        results = []
                        for item in items[:3]:
                            results.append({
                                "title": item.get("title", ""),
                                "snippet": item.get("snippet", ""),
                                "link": item.get("link", "")
                            })
                        if results:
                            return results
                    else:
                        logger.error(f"Google Search API returned {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Google Custom Search API error: {e}")

        # Fallback: Simulate Google Search using LLM
        logger.info(f"Using simulated search engine fallback for query: '{query}'")
        system_prompt = (
            "You are a search engine simulation tool. Given a search query, you must return 3 realistic "
            "search results containing snippets from websites (like Wikipedia, news outlets, official docs) "
            "that represent the factual ground truth for that query. Be highly accurate.\n\n"
            "Return a JSON object with a single key 'results' which is a list of objects, each containing:\n"
            "- 'title': The title of the search result webpage.\n"
            "- 'snippet': A short, realistic text snippet summarizing the info.\n"
            "- 'link': A realistic placeholder URL (e.g. https://en.wikipedia.org, https://www.officialsite.com).\n"
            "Ensure the output is strictly valid JSON."
        )

        user_content = f"Search query: '{query}'"

        fallback_results = [
            {
                "title": f"Search result for {query}",
                "snippet": f"This is simulated search results for query '{query}' due to missing credentials.",
                "link": "https://www.google.com"
            }
        ]

        try:
            text, _, _, _ = await LLMService.generate_response(
                model=settings.DEFAULT_CANDIDATE_MODEL,
                prompt=user_content,
                system_prompt=system_prompt,
                temperature=0.3,
                json_mode=True
            )
            data = clean_and_parse_json(text)
            return data.get("results", fallback_results)
        except Exception as e:
            logger.error(f"Error simulating search: {e}")
            return fallback_results

    async def verify_claim(self, claim: str, search_results: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Cross-checks a claim against search result snippets.
        """
        system_prompt = (
            "You are an AI fact-checking agent. Your job is to verify a candidate claim against a list of Web Search results.\n"
            "You must output a JSON report with keys:\n"
            "- 'status': 'SUPPORTED' if the search results confirm the claim is true; "
            "'REFUTED' if the search results contradict the claim; "
            "'UNVERIFIED' if the search results do not contain enough information to determine the truth of the claim.\n"
            "- 'reasoning': a brief justification of your decision referencing the snippets.\n"
            "- 'citations': an array of indexes (0-indexed) of the search results that support or refute the claim.\n"
            "Ensure the output is strictly valid JSON. Base your judgment ONLY on the provided search results."
        )

        results_str = ""
        for idx, res in enumerate(search_results):
            results_str += f"[{idx}] Title: {res.get('title')}\nSnippet: {res.get('snippet')}\nLink: {res.get('link')}\n\n"

        user_content = (
            f"Factual Claim: \"{claim}\"\n\n"
            f"Web Search Results:\n{results_str}"
        )

        fallback = {
            "status": "UNVERIFIED",
            "reasoning": "Verification execution failed.",
            "citations": []
        }

        try:
            text, _, _, _ = await LLMService.generate_response(
                model=self.judge_model,
                prompt=user_content,
                system_prompt=system_prompt,
                temperature=0.1,
                json_mode=True
            )
            data = clean_and_parse_json(text)
            return {
                "status": data.get("status", "UNVERIFIED"),
                "reasoning": data.get("reasoning", ""),
                "citations": data.get("citations", [])
            }
        except Exception as e:
            logger.error(f"Error verifying claim '{claim}': {e}")
            return fallback

    async def run_verification(self, prompt: str, response: str) -> Dict[str, Any]:
        """
        Runs the full verification pipeline.
        """
        start_time = time.time()
        
        # 1. Extract claims
        claims = await self.extract_claims(prompt, response)
        
        verified_claims = []
        supported_count = 0
        refuted_count = 0
        
        for item in claims:
            claim_text = item.get("claim")
            query = item.get("search_query")
            
            # 2. Search
            search_results = await self.search_google(query)
            
            # 3. Verify
            verification = await self.verify_claim(claim_text, search_results)
            
            status = verification.get("status", "UNVERIFIED")
            if status == "SUPPORTED":
                supported_count += 1
            elif status == "REFUTED":
                refuted_count += 1
                
            verified_claims.append({
                "claim": claim_text,
                "search_query": query,
                "search_results": search_results,
                "status": status,
                "reasoning": verification.get("reasoning", ""),
                "citations": verification.get("citations", [])
            })
            
        # 4. Calculate Groundedness Score
        total_claims = len(verified_claims)
        if total_claims > 0:
            score = ((supported_count + (0.3 * (total_claims - supported_count - refuted_count))) / total_claims) * 100
            score = round(max(0.0, min(100.0, score)), 1)
        else:
            score = 100.0
            
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "groundedness_score": score,
            "claims": verified_claims,
            "latency_ms": round(latency_ms, 2),
            "summary": f"Audited {total_claims} claims. Supported: {supported_count}, Refuted: {refuted_count}, Unverified: {total_claims - supported_count - refuted_count}."
        }
