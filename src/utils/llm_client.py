from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain.llms import Ollama, OpenAI
from langchain.chat_models import ChatOpenAI

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    def create_llm_with_context(self, model_name: str, context_size: Optional[int] = None):
        """Create LLM instance with specified context window"""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        pass
    
    def check_context_requirements(self, text: str, context_size: int) -> Dict[str, Any]:
        """Check if text fits within context window"""
        estimated_tokens = self.estimate_tokens(text)
        return {
            "estimated_tokens": estimated_tokens,
            "context_size": context_size,
            "fits_in_context": estimated_tokens <= context_size,
            "utilization_percentage": (estimated_tokens / context_size) * 100
        }

class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str = "http://localhost:11434",
                 context_window_size: int = 8192,
                 timeout: int = 300):
        self.base_url = base_url
        self.context_window_size = context_window_size
        self.timeout = timeout
    
    def create_llm_with_context(self, model_name: str, context_size: Optional[int] = None):
        effective_context_size = context_size or self.context_window_size
        return Ollama(
            model=model_name,
            num_ctx=effective_context_size,
            timeout=self.timeout,
        )
    
    def estimate_tokens(self, text: str) -> int:
        """Rough estimation for Ollama (1 token ≈ 0.75 words)"""
        word_count = len(text.split())
        return int(word_count / 0.75)

class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str,
                 context_window_size: int = 4096,
                 timeout: int = 300):
        self.api_key = api_key
        self.context_window_size = context_window_size
        self.timeout = timeout
    
    def create_llm_with_context(self, model_name: str, context_size: Optional[int] = None):
        effective_context_size = context_size or self.context_window_size
        
        if "gpt-3.5" in model_name or "gpt-4" in model_name:
            return ChatOpenAI(
                model_name=model_name,
                openai_api_key=self.api_key,
                max_tokens=effective_context_size,
                timeout=self.timeout,
            )
        else:
            return OpenAI(
                model_name=model_name,
                openai_api_key=self.api_key,
                max_tokens=effective_context_size,
                timeout=self.timeout,
            )
    
    def estimate_tokens(self, text: str) -> int:
        """More accurate estimation for OpenAI (1 token ≈ 4 characters)"""
        return len(text) // 4