def update_knowledge_ability_mapping(tsc_json_path, ensemble_output_json_path):
    # Load the JSON files
    with open(tsc_json_path, 'r', encoding='utf-8') as tsc_file:
        tsc_data = json.load(tsc_file)
    
    with open(ensemble_output_json_path, 'r', encoding='utf-8') as ensemble_file:
        ensemble_data = json.load(ensemble_file)
    
    # Extract the learning units from output_TSC
    course_proposal_form = tsc_data.get("TSC_Form", {})
    learning_units = {key: value for key, value in course_proposal_form.items() if key.startswith("LU")}
    
    # Prepare the Knowledge and Ability Mapping structure in ensemble_output if it does not exist
    if "Knowledge and Ability Mapping" not in ensemble_data:
        ensemble_data["Knowledge and Ability Mapping"] = {}

    # Loop through each Learning Unit to extract and map K and A factors
    for index, (lu_key, topics) in enumerate(learning_units.items(), start=1):
        ka_key = f"KA{index}"
        ka_mapping = []

        # Extract K and A factors from each topic within the Learning Unit
        for topic in topics:
            # Match K and A factors in the topic string using regex
            matches = re.findall(r'\b(K\d+|A\d+)\b', topic)
            if matches:
                ka_mapping.extend(matches)

        # Ensure only unique K and A factors are added
        ka_mapping = list(dict.fromkeys(ka_mapping))  # Remove duplicates while preserving order

        # Add the KA mapping to the ensemble_data
        ensemble_data["Knowledge and Ability Mapping"][ka_key] = ka_mapping

    # Save the updated JSON to the same file path
    with open(ensemble_output_json_path, 'w', encoding='utf-8') as outfile:
        json.dump(ensemble_data, outfile, indent=4, ensure_ascii=False)

    print(f"Updated Knowledge and Ability Mapping saved to {ensemble_output_json_path}")

def extract_final_agent_json(file_path: str, agent_name: str) -> Optional[Dict]:
    """
    Reads the specified JSON file (default: 'research_group_chat_state.json'),
    finds the editor agent's final response, and extracts the
    substring from the first '{' to the last '}'.
    
    Attempts to parse the extracted substring as JSON, returning
    a Python dictionary. If parsing fails or if no final message
    is found, returns None.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Identify the aggregator key (usually starts with "aggregator/")
    agent_key = None
    for key in data["agent_states"]:
        if key.startswith(agent_name + "/"):
            agent_key = key
            break

    if not editor_key:
        print(f"No {agent_name} key found in agent_states.")
        return None

    # 2. Get the aggregator agent state and retrieve the final message
    agent_state = data["agent_states"][agent_key]
    messages = agent_state["agent_state"]["llm_context"]["messages"]
    if not messages:
        print(f"No messages found under {agent_name} agent state.")
        return None

    final_message = messages[-1].get("content", "")
    if not final_message:
        print(f"Final {agent_name} message is empty.")
        return None

    # 3. Extract the substring from the first '{' to the last '}'
    start_index = final_message.find("{")
    end_index = final_message.rfind("}")
    if start_index == -1 or end_index == -1:
        print(f"No JSON braces found in the final {agent_name} message.")
        return None

    json_str = final_message[start_index:end_index + 1].strip()

    # 4. Parse the extracted substring as JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        print(f"Failed to parse {agent_name} content as valid JSON.")
        return None