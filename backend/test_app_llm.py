import sys
import os
sys.path.append(os.getcwd())

from app.llm_engine import create_gpt5_engine, AzureOpenAIEngine
from app.config import settings

print(f"Testing App LLM Engine")
print(f"Deployment: {settings.azure_openai_deployment_name}")
print(f"API Version: {settings.azure_openai_api_version}")

try:
    engine = create_gpt5_engine()
    print(f"Engine created with model: {engine.deployment_name}")
    
    response = engine.generate("Hello, are you working?")
    print(f"Response: {response}")
    
except Exception as e:
    print(f"❌ Error: {e}")
