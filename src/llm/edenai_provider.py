import requests
import json
from .base_provider import BaseLLMProvider, LLMConfig
import logging

class EdenAIProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        
        if not config.api_key:
            raise ValueError("API key is required for EdenAI provider")
        
        # Parse model string
        if "/" in config.model:
            self.provider, self.model = config.model.split("/", 1)
        else:
            self.provider = "openai"
            self.model = config.model
        
        self.api_key = config.api_key
        self.base_url = "https://api.edenai.run/v2/llm/chat"
        
    def invoke(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "providers": self.provider,
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Handle OpenAI-compatible response format
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                if content:
                    return content
            
            # Fallback to original EdenAI format (if they switch back)
            if self.provider in result and "generated_text" in result[self.provider]:
                return result[self.provider]["generated_text"]
            
            raise RuntimeError(f"Unexpected response format: {result}")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"EdenAI API request failed: {e}")
            raise RuntimeError(f"EdenAI API error: {e}")
        except (KeyError, TypeError) as e:
            logging.error(f"EdenAI response parsing error: {e}")
            raise RuntimeError(f"Failed to parse EdenAI response: {e}")

    def validate_config(self) -> bool:
        return bool(self.config.api_key and self.config.model)
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # EdenAI pricing varies by provider
        pricing_map = {
            "openai": {"input": 0.0000015, "output": 0.000002},
            "anthropic": {"input": 0.000008, "output": 0.000024},
            "google": {"input": 0.000001, "output": 0.000002},
            "mistral": {"input": 0.000001, "output": 0.000003},
        }
        
        rates = pricing_map.get(self.provider, {"input": 0.000001, "output": 0.000001})
        return (input_tokens * rates["input"]) + (output_tokens * rates["output"])
