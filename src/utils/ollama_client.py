# src/utils/ollama_client.py
import requests
from typing import Dict, Any, Optional
from langchain.llms import Ollama

class EnhancedOllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", 
                 context_window_size: int = 8192,
                 timeout: int = 300):
        self.base_url = base_url
        self.context_window_size = context_window_size
        self.timeout = timeout
    
    def create_llm_with_context(self, model_name: str, 
                               context_size: Optional[int] = None) -> Ollama:
        """Create Ollama LLM instance with specified context window"""
        effective_context_size = context_size or self.context_window_size
        
        return Ollama(
            model=model_name,
            base_url=self.base_url,
            timeout=self.timeout,
            # Set context window size via model options
            model_kwargs={
                "options": {
                    "num_ctx": effective_context_size
                }
            }
        )
    
    def estimate_tokens(self, text: str) -> int:
        """Rough estimation of token count (1 token ≈ 0.75 words)"""
        word_count = len(text.split())
        return int(word_count / 0.75)
    
    def check_context_requirements(self, text: str, 
                                 context_size: int) -> Dict[str, Any]:
        """Check if text fits within context window"""
        estimated_tokens = self.estimate_tokens(text)
        
        return {
            "estimated_tokens": estimated_tokens,
            "context_size": context_size,
            "fits_in_context": estimated_tokens <= context_size,
            "utilization_percentage": (estimated_tokens / context_size) * 100
        }
