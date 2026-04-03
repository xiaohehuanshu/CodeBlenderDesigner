import sys
sys.path.insert(0, 'langgraph_agent/src')

import os
from langgraph_space_agent.config import AgentSettings
from langgraph_space_agent.llm_clients import OpenAICompatibleClient

# Load env
env_file = 'langgraph_agent/.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

settings = AgentSettings()
client = OpenAICompatibleClient(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    default_model=settings.openai_model
)

print("Testing full agent flow...")
print("This would normally run through all 8 nodes")
print("Let's test a simple chat first...")

result = client.chat_text(
    system_prompt='You are a helpful assistant for architectural design.',
    user_content='What is a cantilever in architecture? Answer in one sentence.',
    temperature=0.2
)
print("LLM Response:", result)
