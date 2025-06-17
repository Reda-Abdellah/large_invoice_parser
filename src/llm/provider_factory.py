# src/llm/provider_factory.py
from typing import Dict, Type
from .base_provider import BaseLLMProvider, LLMConfig
from .openai_provider import OpenAIProvider
from .edenai_provider import EdenAIProvider
from .ollama_provider import OllamaProvider

class LLMProviderFactory:
    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "openai": OpenAIProvider,
        "edenai": EdenAIProvider,
        "ollama": OllamaProvider
    }
    
    @classmethod
    def create_provider(cls, config: LLMConfig) -> BaseLLMProvider:
        provider_class = cls._providers.get(config.provider)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {config.provider}")
        
        provider = provider_class(config)
        if not provider.validate_config():
            raise ValueError(f"Invalid configuration for {config.provider}")
        
        return provider
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseLLMProvider]):
        """Register custom provider"""
        cls._providers[name] = provider_class
