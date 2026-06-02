import os
import json
import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RAGService:
    _dataset: List[Dict[str, str]] = []

    @classmethod
    def _load_dataset(cls):
        if cls._dataset:
            return
        
        # Look for dataset file in standard locations
        current_dir = os.path.dirname(os.path.abspath(__file__))
        paths_to_check = [
            os.path.join(current_dir, "..", "..", "..", "Ecommerce_FAQ_Chatbot_dataset.json"),
            os.path.join(os.getcwd(), "Ecommerce_FAQ_Chatbot_dataset.json"),
            os.path.join(os.getcwd(), "..", "Ecommerce_FAQ_Chatbot_dataset.json"),
            os.path.join(current_dir, "..", "..", "Ecommerce_FAQ_Chatbot_dataset.json")
        ]
        
        dataset_loaded = False
        for path in paths_to_check:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cls._dataset = data.get("questions", [])
                        logger.info(f"Loaded {len(cls._dataset)} FAQ items from {abs_path}")
                        dataset_loaded = True
                        break
                except Exception as e:
                    logger.error(f"Failed to load dataset at {abs_path}: {e}")
                    
        if not dataset_loaded:
            logger.warning("Ecommerce FAQ dataset JSON file not found in any search path.")
            cls._dataset = []

    # Common English stop words to filter out
    STOP_WORDS = {
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
        "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", 
        "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", 
        "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", 
        "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
        "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", 
        "for", "with", "about", "against", "between", "into", "through", "during", "before", 
        "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", 
        "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", 
        "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", 
        "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", 
        "will", "just", "don", "should", "now"
    }

    @classmethod
    def retrieve_faqs(cls, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        cls._load_dataset()
        if not cls._dataset:
            return []

        # Tokenize query and remove stop words
        query_words = set(re.findall(r"\w+", query.lower()))
        filtered_query = query_words - cls.STOP_WORDS
        
        # If query is empty after filtering (e.g. "What is it?"), fall back to full query words
        active_query = filtered_query if filtered_query else query_words
        if not active_query:
            return cls._dataset[:top_k]

        scored_faqs = []
        for item in cls._dataset:
            q_text = item.get("question", "")
            ans_text = item.get("answer", "")
            
            # Tokenize question and answer
            q_words = set(re.findall(r"\w+", q_text.lower()))
            ans_words = set(re.findall(r"\w+", ans_text.lower()))
            
            # Filter stop words
            q_words_filtered = q_words - cls.STOP_WORDS
            ans_words_filtered = ans_words - cls.STOP_WORDS
            
            # Calculate weighted overlap (weight 3 for question matches, 1 for answer matches)
            q_overlap = len(active_query.intersection(q_words_filtered))
            ans_overlap = len(active_query.intersection(ans_words_filtered))
            
            score = (q_overlap * 3) + ans_overlap
            
            # Add bonus weight for exact phrase matches in question
            if q_text.lower() in query.lower() or query.lower() in q_text.lower():
                score += 15
                
            scored_faqs.append((score, item))
            
        # Sort by score descending
        scored_faqs.sort(key=lambda x: x[0], reverse=True)
        
        # Filter to matches with positive score, or fallback to top_k default items if none found
        results = [item for score, item in scored_faqs if score > 0][:top_k]
        return results if results else cls._dataset[:top_k]
