"""
Configuration module for the Agentic CRM backend.
Loads environment variables and provides typed settings.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure OpenAI Configuration
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment_name: str = "gpt-5.2-chat"
    azure_openai_model: str = "gpt-5.2-chat"
    # Use gpt-5.2-chat for "gpt5" requests as well since pro is failing
    azure_openai_gpt5_deployment_name: str = "gpt-5.2-chat"
    azure_openai_gpt5_model: str = "gpt-5.2-chat"
    azure_openai_chat_deployment_name: str = "gpt-5.2-chat"
    azure_openai_textembedding_deployment_name: str = "text-embedding-3-small"
    azure_openai_textembedding_model: str = "text-embedding-3-small"
    
    # Database Configuration
    database_url: str = "postgresql://dbuser:dbpass123@localhost:5432/crm_db"
    
    # Application Settings
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # AgentFlow Configuration
    agentflow_max_steps: int = 10
    agentflow_max_time: int = 300
    agentflow_verbose: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience exports
settings = get_settings()
