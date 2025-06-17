# src/llm/openai_provider.py
from langchain_openai import OpenAI, ChatOpenAI
from .base_provider import BaseLLMProvider, LLMConfig

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=config.api_key
        )
    
    def invoke(self, prompt: str) -> str:
        try:
            response = self.client.invoke(prompt)
            return response.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    def validate_config(self) -> bool:
        return bool(self.config.api_key and self.config.model)
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # GPT-4 pricing example
        if "gpt-4" in self.config.model:
            return (input_tokens * 0.00003) + (output_tokens * 0.00006)
        return (input_tokens * 0.0000015) + (output_tokens * 0.000002)
