import json
import re
import sys
import os

def extract_agent_json(file_path: str, agent_name: str):
    """
    Reads the specified JSON file, finds the specified agent's final response,
    and extracts the substring from the first '{' to the last '}'.
    
    Attempts to parse the extracted substring as JSON, returning
    a Python dictionary. If parsing fails or if no final message
    is found, returns None.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Identify the agent key (usually starts with the agent name followed by '/')
    agent_key = None
    for key in data["agent_states"]:
        if key.startswith(f"{agent_name}/"):
            agent_key = key
            break

    if not agent_key:
        print(f"No {agent_name} key found in agent_states.")
        return None

    # Get the agent state and retrieve the final message
    agent_state = data["agent_states"][agent_key]
    messages = agent_state["agent_state"]["llm_context"]["messages"]
    if not messages:
        print(f"No messages found under {agent_name} agent state.")
        return None

    final_message = messages[-1].get("content", "")
    if not final_message:
        print(f"Final {agent_name} message is empty.")
        return None

    # Extract the substring from the first '{' to the last '}'
    start_index = final_message.find("{")
    end_index = final_message.rfind("}")
    if start_index == -1 or end_index == -1:
        print(f"No JSON braces found in the final {agent_name} message.")
        return None

    json_str = final_message[start_index:end_index + 1].strip()

    # Parse the extracted substring as JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        print(f"Failed to parse {agent_name} content as valid JSON.")
        return None