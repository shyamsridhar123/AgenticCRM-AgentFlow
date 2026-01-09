"""
Azure OpenAI LLM Engine for AgentFlow integration.
Provides a custom LLM engine that uses Azure OpenAI endpoints.
"""

from typing import Optional, List, Dict, Any
from openai import AzureOpenAI

from app.config import settings


class AzureOpenAIEngine:
    """
    Custom LLM engine for AgentFlow that uses Azure OpenAI.
    This integrates with AgentFlow's modular architecture.
    """
    
    def __init__(
        self,
        deployment_name: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4000,
        is_multimodal: bool = False
    ):
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
        self.deployment_name = deployment_name or settings.azure_openai_deployment_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.is_multimodal = is_multimodal
        self.model_string = f"azure-{self.deployment_name}"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate a completion from the Azure OpenAI model.
        
        Args:
            prompt: The user prompt/question
            system_prompt: Optional system message
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Optional stop sequences
            
        Returns:
            The generated text response
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Use max_completion_tokens for newer models (O1/GPT-5 class)
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_completion_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                stop=stop
            )
            
            return response.choices[0].message.content
        except Exception as e:
            # Log the error and return a fallback response
            print(f"⚠️ LLM Error: {str(e)}")
            return f"[LLM Unavailable - Error: {str(e)[:100]}]"
    
    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate a completion from a list of messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Optional stop sequences
            
        Returns:
            The generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_completion_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                stop=stop
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ LLM Error: {str(e)}")
            return f"[LLM Unavailable - Error: {str(e)[:100]}]"
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embeddings for text using Azure OpenAI embedding model.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding floats
        """
        response = self.client.embeddings.create(
            model=settings.azure_openai_textembedding_deployment_name,
            input=text
        )
        
        return response.data[0].embedding


def create_azure_engine(
    deployment_name: Optional[str] = None,
    temperature: float = 0.0,
    is_multimodal: bool = False
) -> AzureOpenAIEngine:
    """
    Factory function to create an Azure OpenAI engine.
    
    Args:
        deployment_name: Azure deployment name (defaults to config)
        temperature: Sampling temperature
        is_multimodal: Whether to use multimodal capabilities
        
    Returns:
        Configured AzureOpenAIEngine instance
    """
    return AzureOpenAIEngine(
        deployment_name=deployment_name,
        temperature=temperature,
        is_multimodal=is_multimodal
    )


def create_gpt5_engine(temperature: float = 1.0) -> AzureOpenAIEngine:
    """Create an engine using the GPT-5 Pro model."""
    return AzureOpenAIEngine(
        deployment_name=settings.azure_openai_gpt5_deployment_name,
        temperature=temperature
    )


# Singleton engine instance for simple function calls
_default_engine: Optional[AzureOpenAIEngine] = None


def get_llm_response(prompt: str, max_tokens: int = 1000, system_prompt: Optional[str] = None) -> str:
    """
    Simple function to get LLM response without managing engine instances.
    Used by AgentFlow solver components.
    
    Args:
        prompt: The prompt to send
        max_tokens: Maximum tokens in response
        system_prompt: Optional system prompt
        
    Returns:
        The LLM response text
    """
    global _default_engine
    
    if _default_engine is None:
        _default_engine = AzureOpenAIEngine(temperature=1.0)  # GPT-5.2 only supports temp=1
    
    return _default_engine.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens
    )
