import asyncio
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent

GEMINI_API_KEY="AIzaSyBmOW-thoavyrEGO5wlcd9PF3om_IZHvMw"

# Gemini
gemini_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "gemini-2.0-flash-exp",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": GEMINI_API_KEY,
        "model_info": {
            "family": "unknown",
            "function_calling": True,
            "json_output": True,
            "vision": True,
        }
    }
}

async def create_assessment_team(model_choice: str): # magnetic-one group chat pattern
    chosen_config = model_choice
    model_client = ChatCompletionClient.load_component(chosen_config)
    m1 = MagenticOne(client=model_client)
    task = "Write a set of 1 exam papers and answers involving 2 open ended questions and 10 MCQ, the answers have to be detailed and sufficiently answers the questions, regarding the topic of 'The History of the United States', adjusted to the level of an undergraduate student."
    result = await Console(m1.run_stream(task=task))
    print(result)

async def main():
    await create_assessment_team(model_choice=gemini_config)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")