# src/llm/ollama_provider.py
from langchain.llms import Ollama
from .base_provider import BaseLLMProvider, LLMConfig

class OllamaProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = Ollama(
            model=config.model,
            base_url=config.base_url or "http://localhost:11434",
            temperature=config.temperature
        )
    
    def invoke(self, prompt: str) -> str:
        return self.client.invoke(prompt)
    
    def validate_config(self) -> bool:
        return bool(self.config.model)
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0  # Local inference is free
