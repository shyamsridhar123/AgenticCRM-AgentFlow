import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("AZURE_OPENAI_API_KEY")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_CHAT", "gpt-5.2-chat")

print(f"Endpoint: {endpoint}")
print(f"Deployment: {deployment}")

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=endpoint
)

try:
    print("\nAttempting completion (without max_tokens)...")
    # Trying with max_completion_tokens instead, or just omitting it
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "user", "content": "Hello, are you working?"}
        ]
        # Removed max_tokens
    )
    print("✅ Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"\n❌ Error: {e}")
    if hasattr(e, 'response'):
        print(f"Response JSON: {e.response.json()}")
