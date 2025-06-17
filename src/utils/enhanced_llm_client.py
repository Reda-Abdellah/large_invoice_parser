# src/utils/enhanced_llm_client.py
from typing import Dict, Any, Optional
from ..llm.provider_factory import LLMProviderFactory
from ..llm.base_provider import LLMConfig

class EnhancedLLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all configured providers"""
        for task, provider_config in self.config.get('llm_providers', {}).items():
            try:
                llm_config = LLMConfig(**provider_config)
                provider = LLMProviderFactory.create_provider(llm_config)
                self.providers[task] = provider
                print(f"✅ Initialized {provider_config['provider']} for {task}")
            except Exception as e:
                print(f"❌ Failed to initialize {task}: {e}")
                self._setup_fallback(task)
    
    def _setup_fallback(self, task: str):
        """Setup fallback provider for failed initialization"""
        fallbacks = self.config.get('fallback_providers', [])
        for fallback_config in fallbacks:
            try:
                llm_config = LLMConfig(**fallback_config)
                provider = LLMProviderFactory.create_provider(llm_config)
                self.providers[task] = provider
                print(f"🔄 Using fallback {fallback_config['provider']} for {task}")
                break
            except Exception:
                continue
    
    def invoke(self, task: str, prompt: str) -> str:
        """Invoke LLM for specific task"""
        if task not in self.providers:
            raise ValueError(f"No provider configured for task: {task}")
        
        return self.providers[task].invoke(prompt)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (provider-agnostic)"""
        return max(1, len(text.split()) // 0.75)
    
    def get_provider_info(self, task: str) -> Dict[str, Any]:
        """Get information about provider for specific task"""
        if task not in self.providers:
            return {}
        
        provider = self.providers[task]
        return {
            "provider": provider.config.provider,
            "model": provider.config.model,
            "temperature": provider.config.temperature
        }
