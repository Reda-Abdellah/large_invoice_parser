# Test script
from src.llm.base_provider import LLMConfig
from src.llm.edenai_provider import EdenAIProvider


config = LLMConfig(
    provider="edenai",
    model="openai/gpt-3.5-turbo",
    api_key="API_key_here",  # Replace with your actual API key
)
# print("Config:", config)
provider = EdenAIProvider(config)
response = provider.invoke("Hello, world!")
print("Response:", response)