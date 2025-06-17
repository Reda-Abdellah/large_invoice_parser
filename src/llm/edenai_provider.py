# src/llm/edenai_provider.py
from langchain_community.llms import EdenAI
from .base_provider import BaseLLMProvider, LLMConfig

class EdenAIProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # Extract provider from model string (e.g., "openai/gpt-4")
        provider, model = config.model.split("/") if "/" in config.model else ("openai", config.model)
        
        self.client = EdenAI(
            edenai_api_key=config.api_key,
            provider=provider,
            model=model,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
    
    def invoke(self, prompt: str) -> str:
        try:
            return self.client.invoke(prompt)
        except Exception as e:
            raise RuntimeError(f"EdenAI API error: {str(e)}")
    
    def validate_config(self) -> bool:
        return bool(self.config.api_key and "/" in self.config.model)
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # EdenAI unified pricing - varies by provider
        return (input_tokens + output_tokens) * 0.000001  # Placeholder
