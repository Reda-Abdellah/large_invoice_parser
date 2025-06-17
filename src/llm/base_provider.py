# src/llm/base_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class LLMConfig(BaseModel):
    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class BaseLLMProvider(ABC):
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """Generate text completion from prompt"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        pass
    
    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API call cost"""
        pass
