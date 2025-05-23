import json
import re
import sys
import os
import traceback

def validate_knowledge_and_ability():
    try:
        # Read data from the JSON file
        with open('CourseProposal/json_output/ensemble_output.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Extract Knowledge and Ability factors from the data
        knowledge_factors = set()
        for i, k in enumerate(data['Learning Outcomes'].get('Knowledge', []), 1):
            # Add the expected factor (e.g., K1, K2) based on position
            knowledge_factors.add(f"K{i}")
            # Also extract any explicitly mentioned K factors
            k_matches = re.findall(r'(K\d+)', k)
            for k_match in k_matches:
                knowledge_factors.add(k_match)

        ability_factors = set()
        for i, a in enumerate(data['Learning Outcomes'].get('Ability', []), 1):
            # Add the expected factor (e.g., A1, A2) based on position
            ability_factors.add(f"A{i}")
            # Also extract any explicitly mentioned A factors
            a_matches = re.findall(r'(A\d+)', a)
            for a_match in a_matches:
                ability_factors.add(a_match)

        print(f"Found {len(knowledge_factors)} Knowledge factors: {sorted(knowledge_factors)}")
        print(f"Found {len(ability_factors)} Ability factors: {sorted(ability_factors)}")

        # 1. EXTRACT FACTORS FROM TOPICS
        # Extract topics and their factors
        tsc_and_topics_section = data.get('TSC and Topics', {})
        
        # Try different possible key names for topics
        topics = None
        for key in ['Topic', 'Topics', 'topics']:
            if key in tsc_and_topics_section:
                topics = tsc_and_topics_section[key]
                break

        if topics is None:
            # If topics not found directly, check within Learning Units description
            topics = []
            course_outline = data.get('Assessment Methods', {}).get('Course Outline', {}).get('Learning Units', {})
            for lu_key, lu_data in course_outline.items():
                descriptions = lu_data.get('Description', [])
                for desc in descriptions:
                    if isinstance(desc, dict) and 'Topic' in desc:
                        topics.append(desc['Topic'])

        if not topics:
            print("Warning: No topics found in any expected location in ensemble_output.json.")
            topics = []
        
        # 2. EXTRACT FACTORS FROM TOPICS
        topic_factors = []
        all_topic_factors = set()

        # More flexible regex to capture various formats
        ka_pattern = r'(?:\(|\s|^)(K\d+|A\d+)(?:\)|,|\s|:|$)'
        
        for topic in topics:
            if not isinstance(topic, str):
                continue
                
            # Extract K and A factors from the topic with more flexible regex
            factors = re.findall(ka_pattern, topic)
            topic_factors.append(set(factors))
            all_topic_factors.update(factors)
            
        print(f"Found {len(all_topic_factors)} unique K&A factors in topics: {sorted(all_topic_factors)}")
            
        # 3. CHECK KNOWLEDGE AND ABILITY MAPPING
        # If we didn't find all factors in topics, check if they're in the mapping
        mapping_factors = set()
        ka_mapping = data.get('Learning Outcomes', {}).get('Knowledge and Ability Mapping', {})
        
        for key, values in ka_mapping.items():
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str) and (value.startswith('K') or value.startswith('A')):
                        mapping_factors.add(value)
        
        print(f"Found {len(mapping_factors)} unique K&A factors in mapping: {sorted(mapping_factors)}")
        
        # Combine factors from both sources
        combined_factors = all_topic_factors.union(mapping_factors)
        print(f"Combined unique K&A factors: {sorted(combined_factors)}")

        # 4. PERFORM VALIDATION
        missing_factors = []
        covered_factors = set()

        # Check each Knowledge factor
        for k in knowledge_factors:
            if k in combined_factors:
                covered_factors.add(k)
            else:
                missing_factors.append(f"Knowledge factor {k} is missing from both topics and mapping")

        # Check each Ability factor
        for a in ability_factors:
            if a in combined_factors:
                covered_factors.add(a)
            else:
                missing_factors.append(f"Ability factor {a} is missing from both topics and mapping")
        
        # Check for undefined factors (those in topics but not in K or A lists)
        undefined_factors = []
        for factor in combined_factors:
            if factor not in knowledge_factors and factor not in ability_factors:
                undefined_factors.append(f"Factor {factor} is referenced but not defined in Knowledge or Ability lists")

        # 5. GENERATE REPORT
        # Print out coverage percentage
        total_factors = len(knowledge_factors) + len(ability_factors)
        covered_count = len(covered_factors)
        coverage_pct = (covered_count / total_factors * 100) if total_factors > 0 else 0
        print(f"K&A factor coverage: {covered_count}/{total_factors} ({coverage_pct:.1f}%)")
        
        # Determine validation result
        validation_success = len(missing_factors) == 0 and len(undefined_factors) == 0
        
        # Prepare result data structure
        validation_results = {
            "success": validation_success,
            "knowledge_factors": sorted(list(knowledge_factors)),
            "ability_factors": sorted(list(ability_factors)),
            "topic_factors": sorted(list(all_topic_factors)),
            "mapping_factors": sorted(list(mapping_factors)),
            "combined_factors": sorted(list(combined_factors)),
            "missing_factors": missing_factors,
            "undefined_factors": undefined_factors,
            "coverage_percentage": coverage_pct,
            "total_factors": total_factors,
            "covered_factors": sorted(list(covered_factors))
        }
        
        if validation_success:
            print("SUCCESS: All Knowledge and Ability factors are accounted for.")
            return validation_results
        else:
            # Organize errors by type
            error_sections = []
            
            if missing_factors:
                error_sections.append("Missing factors: " + "; ".join(missing_factors))
            
            if undefined_factors:
                error_sections.append("Undefined factors: " + "; ".join(undefined_factors))
            
            full_error = "FAIL: " + ". ".join(error_sections)
            print(full_error)
            
            # Provide guidance for fixing the issues
            print("\nGUIDANCE FOR FIXING:")
            if missing_factors:
                print("- Ensure all Knowledge and Ability statements are referenced in at least one topic")
                print("- Check if any Learning Units are missing their K&A factors in parentheses")
            if undefined_factors:
                print("- Remove references to non-existent K&A factors from topics")
                print("- Or add these factors to the Knowledge/Ability lists")
            
            # Instead of exiting, return the results
            return validation_results
    
    except FileNotFoundError:
        error_message = "ERROR: ensemble_output.json file not found. Please ensure the file exists."
        print(error_message)
        return {
            "success": False,
            "error": error_message,
            "error_type": "file_not_found"
        }
    except json.JSONDecodeError:
        error_message = "ERROR: ensemble_output.json contains invalid JSON."
        print(error_message)
        return {
            "success": False,
            "error": error_message,
            "error_type": "json_decode_error"
        }
    except Exception as e:
        error_message = f"ERROR in validate_knowledge_and_ability: {str(e)}"
        print(error_message)
        return {
            "success": False,
            "error": error_message,
            "error_type": "general_error"
        }

def fix_missing_ka_references():
    """
    Attempts to fix missing Knowledge and Ability references in topics by using
    the Knowledge and Ability Mapping if available.
    """
    try:
        # Read data from the JSON file
        with open('CourseProposal/json_output/ensemble_output.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Get the Knowledge and Ability mapping
        ka_mapping = data.get('Learning Outcomes', {}).get('Knowledge and Ability Mapping', {})
        if not ka_mapping:
            print("No Knowledge and Ability Mapping found, cannot fix missing references.")
            return {
                "success": False,
                "message": "No Knowledge and Ability Mapping found, cannot fix missing references.",
                "fixed_topics": [],
                "fixed_count": 0
            }
            
        # Check if we have Topics directly
        tsc_and_topics = data.get('TSC and Topics', {})
        has_direct_topics = False
        
        for topic_key in ['Topic', 'Topics', 'topics']:
            if topic_key in tsc_and_topics and isinstance(tsc_and_topics[topic_key], list):
                has_direct_topics = True
                break
        
        # If we have direct topics, we'll need to update the Learning Units
        # But if we only have Learning Units with topics inside, we'll update those
        course_outline = data.get('Assessment Methods', {}).get('Course Outline', {}).get('Learning Units', {})
        
        # Track if we made any changes
        made_changes = False
        fixed_topics = []
        
        # Check each Learning Unit
        for lu_idx, (lu_key, lu_data) in enumerate(course_outline.items(), 1):
            # Find corresponding KA mapping
            ka_key = f"KA{lu_idx}"
            ka_factors = ka_mapping.get(ka_key, [])
            
            if not ka_factors:
                continue
                
            # Update topics in this Learning Unit
            if isinstance(lu_data, dict) and 'Description' in lu_data:
                descriptions = lu_data['Description']
                for desc_idx, desc in enumerate(descriptions):
                    if isinstance(desc, dict) and 'Topic' in desc:
                        topic = desc['Topic']
                        # Check if topic already has K/A references
                        if '(' in topic and any(f in topic for f in ka_factors):
                            continue
                            
                        # If no references, add them from the mapping
                        if '(' not in topic:
                            # Add at the end of the topic name
                            original_topic = topic
                            desc['Topic'] = f"{topic} ({', '.join(ka_factors)})"
                            made_changes = True
                            fixed_topics.append({
                                "learning_unit": lu_key,
                                "original": original_topic,
                                "fixed": desc['Topic'],
                                "added_factors": ka_factors
                            })
                        else:
                            # Has parentheses but no K/A references - try to add to existing parentheses
                            parts = topic.split('(')
                            base = parts[0].strip()
                            closing_paren_pos = topic.rfind(')')
                            
                            if closing_paren_pos != -1:
                                # Replace the content in parentheses
                                original_topic = topic
                                desc['Topic'] = f"{base} ({', '.join(ka_factors)})"
                                made_changes = True
                                fixed_topics.append({
                                    "learning_unit": lu_key,
                                    "original": original_topic,
                                    "fixed": desc['Topic'],
                                    "added_factors": ka_factors
                                })
        
        # If we made changes, save the file
        results = {
            "success": made_changes,
            "fixed_topics": fixed_topics,
            "fixed_count": len(fixed_topics)
        }
        
        if made_changes:
            with open('CourseProposal/json_output/ensemble_output.json', 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4)
            print(f"Fixed {len(fixed_topics)} missing K&A references in topics.")
            results["message"] = f"Fixed {len(fixed_topics)} missing K&A references in topics."
        else:
            print("No missing K&A references found that could be fixed.")
            results["message"] = "No missing K&A references found that could be fixed."
        
        return results
            
    except Exception as e:
        error_message = f"Error in fix_missing_ka_references: {str(e)}"
        print(error_message)
        return {
            "success": False,
            "error": error_message,
            "error_type": "general_error",
            "fixed_topics": [],
            "fixed_count": 0
        }

def extract_final_aggregator_json(file_path: str = "group_chat_state.json"):
    """
    Reads the specified JSON file (default: 'group_chat_state.json'),
    finds the aggregator agent's final response, and extracts the
    substring from the first '{' to the last '}'.
    
    Attempts to parse the extracted substring as JSON, returning
    a Python dictionary. If parsing fails or if no final message
    is found, returns None.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    aggregator_key_name = "aggregator"  # Exact agent name
    found_key = None
    if "agent_states" not in data or not isinstance(data["agent_states"], dict):
        print(f"Warning: 'agent_states' not found or not a dictionary in {file_path}.")
        return {}

    for key in data["agent_states"]:
        if key == aggregator_key_name:
            found_key = key
            break

    if not found_key:
        print(f"No key for agent '{aggregator_key_name}' found in agent_states of {file_path}.")
        return {}

    aggregator_state = data["agent_states"][found_key]
    if not isinstance(aggregator_state, dict) or "agent_state" not in aggregator_state or \
       not isinstance(aggregator_state["agent_state"], dict) or "llm_context" not in aggregator_state["agent_state"] or \
       not isinstance(aggregator_state["agent_state"]["llm_context"], dict) or "messages" not in aggregator_state["agent_state"]["llm_context"]:
        print(f"Unexpected structure for agent '{found_key}' state in {file_path}.")
        return {}

    messages = aggregator_state["agent_state"]["llm_context"]["messages"]
    if not messages or not isinstance(messages, list):
        print(f"No messages found or messages is not a list for agent '{found_key}' in {file_path}.")
        return {}

    final_message_obj = messages[-1]
    if not isinstance(final_message_obj, dict) or "content" not in final_message_obj:
        print(f"Final message for agent '{found_key}' has unexpected structure or no content in {file_path}.")
        return {}

    final_message = final_message_obj.get("content", "")

    parsed_json = clean_and_parse_json(final_message)
    if parsed_json is None:
        print(f"CRITICAL: Failed to clean and parse JSON output from aggregator agent in state file: {{file_path}}")
        # Optionally, log the original final_message for deeper debugging if needed
        # print(f"Original problematic string from aggregator was: {{final_message[:1000]}}...")
    return parsed_json

def extract_final_editor_json(file_path: str = "research_group_chat_state.json"):
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

    # 1. Identify the editor key
    editor_agent_name = "editor"  # Exact agent name
    found_key = None
    if "agent_states" not in data or not isinstance(data["agent_states"], dict):
        print(f"Warning: 'agent_states' not found or not a dictionary in {file_path}.")
        return {}

    for key in data["agent_states"]:
        if key == editor_agent_name:
            found_key = key
            break

    if not found_key:
        print(f"No key for agent '{editor_agent_name}' found in agent_states of {file_path}.")
        return {}

    # 2. Get the editor agent state and retrieve the final message
    editor_state = data["agent_states"][found_key]
    if not isinstance(editor_state, dict) or "agent_state" not in editor_state or \
       not isinstance(editor_state["agent_state"], dict) or "llm_context" not in editor_state["agent_state"] or \
       not isinstance(editor_state["agent_state"]["llm_context"], dict) or "messages" not in editor_state["agent_state"]["llm_context"]:
        print(f"Unexpected structure for agent '{found_key}' state in {file_path}.")
        return {}

    messages = editor_state["agent_state"]["llm_context"]["messages"]
    if not messages or not isinstance(messages, list):
        print(f"No messages found or messages is not a list for agent '{found_key}' in {file_path}.")
        return {}
        
    final_message_obj = messages[-1]
    if not isinstance(final_message_obj, dict) or "content" not in final_message_obj:
        print(f"Final message for agent '{found_key}' has unexpected structure or no content in {file_path}.")
        return {}

    final_message = final_message_obj.get("content", "")
    if not final_message or not isinstance(final_message, str):
        print(f"Final message for agent '{{found_key}}' is empty or not a string in {{file_path}}.")
        return {{}}

    parsed_json = clean_and_parse_json(final_message)
    if parsed_json is None:
        print(f"CRITICAL: Failed to clean and parse JSON output from editor agent in state file: {{file_path}}")
    return parsed_json

def rename_keys_in_json_file(filename):
    key_mapping = {
    "course_info": "Course Information",
    "learning_outcomes": "Learning Outcomes",
    "tsc_and_topics": "TSC and Topics",
    "assessment_methods": "Assessment Methods"
    }
    # Load the JSON data from the file
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
    if not data or not isinstance(data, dict):
        print(f"Warning: {filename} is empty or not a dict. Skipping key renaming.")
        return
    # Rename keys according to the key_mapping
    for old_key, new_key in key_mapping.items():
        if old_key in data:
            data[new_key] = data.pop(old_key)
    # Save the updated JSON data back to the same file
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)
    print(f"Updated JSON saved to {filename}")

def update_knowledge_ability_mapping(tsc_json_path, ensemble_output_json_path):
    """
    Updates the Knowledge and Ability Mapping in ensemble_output.json using multiple sources:
    1. Extracts from the TSC agent output (if available in expected format)
    2. If source 1 fails, extracts from Learning Units list in ensemble_output
    3. If source 2 fails, extracts from the TSC mapping table in output_TSC_raw.json
    4. If source 3 fails, uses a more exhaustive scanning approach
    5. If all sources fail, falls back to generating a basic mapping
    
    Each learning unit will use data from the first source that provides a mapping for it.
    
    Additionally, it extracts the Knowledge and Ability statements from the TSC data and adds them to the ensemble output.
    """
    try:
        # Load the JSON files
        with open(tsc_json_path, 'r', encoding='utf-8') as tsc_file:
            tsc_data = json.load(tsc_file)
        with open(ensemble_output_json_path, 'r', encoding='utf-8') as ensemble_file:
            ensemble_data = json.load(ensemble_file)
        
        # Ensure "Learning Outcomes" key exists and is a dictionary
        learning_outcomes_section = ensemble_data.get("Learning Outcomes")
        if not isinstance(learning_outcomes_section, dict):
            print(f"Warning: 'Learning Outcomes' key in {ensemble_output_json_path} is missing or not a dictionary. Initializing as empty dict.")
            ensemble_data["Learning Outcomes"] = {}
            learning_outcomes_section = ensemble_data["Learning Outcomes"]

        # Ensure "Knowledge" and "Ability" lists exist under "Learning Outcomes"
        if "Knowledge" not in learning_outcomes_section:
            print(f"Warning: 'Knowledge' key missing under 'Learning Outcomes' in {ensemble_output_json_path}. Initializing as empty list.")
            learning_outcomes_section["Knowledge"] = []
        if "Ability" not in learning_outcomes_section:
            print(f"Warning: 'Ability' key missing under 'Learning Outcomes' in {ensemble_output_json_path}. Initializing as empty list.")
            learning_outcomes_section["Ability"] = []

        # IMPORTANT: Extract actual Knowledge and Ability statements from TSC data
        # This is crucial for validation to pass - we need to know what each K1, K2, etc. actually represents
        knowledge_statements = {}
        ability_statements = {}
        
        # Try to extract from Course_Proposal_Form
        cp_form = tsc_data.get("Course_Proposal_Form", {})
        for key, values in cp_form.items():
            if key.startswith("TSC") or key == "null":
                for value in values:
                    if isinstance(value, str):
                        # Look for Knowledge statements (format: "K1: description")
                        k_match = re.match(r'K(\d+):\s*(.*)', value)
                        if k_match:
                            k_num = int(k_match.group(1))
                            k_desc = k_match.group(2).strip()
                            knowledge_statements[k_num] = k_desc
                            continue
                        
                        # Look for statements starting with "K1 description"
                        k_match = re.match(r'K(\d+)\s+(.*)', value)
                        if k_match:
                            k_num = int(k_match.group(1))
                            k_desc = k_match.group(2).strip()
                            knowledge_statements[k_num] = k_desc
                            continue
                        
                        # Look for Ability statements (format: "A1: description")
                        a_match = re.match(r'A(\d+):\s*(.*)', value)
                        if a_match:
                            a_num = int(a_match.group(1))
                            a_desc = a_match.group(2).strip()
                            ability_statements[a_num] = a_desc
                            continue
                        
                        # Look for statements starting with "A1 description"
                        a_match = re.match(r'A(\d+)\s+(.*)', value)
                        if a_match:
                            a_num = int(a_match.group(1))
                            a_desc = a_match.group(2).strip()
                            ability_statements[a_num] = a_desc
                            continue
        
        # If we couldn't find statements in Course_Proposal_Form, try TSC_raw data
        if not knowledge_statements or not ability_statements:
            # Try to extract from TSC_raw content
            tsc_content = tsc_data.get("TSC and Topics", {}).get("content", [])
            for item in tsc_content:
                if isinstance(item, str):
                    # Look for Knowledge statements
                    k_match = re.match(r'K(\d+)[ :]+(.*)', item)
                    if k_match:
                        k_num = int(k_match.group(1))
                        k_desc = k_match.group(2).strip()
                        knowledge_statements[k_num] = k_desc
                        continue
                    
                    # Look for Ability statements
                    a_match = re.match(r'A(\d+)[ :]+(.*)', item)
                    if a_match:
                        a_num = int(a_match.group(1))
                        a_desc = a_match.group(2).strip()
                        ability_statements[a_num] = a_desc
                        continue
        
        # Convert the extracted statements to ordered lists for ensemble output
        k_list = []
        a_list = []
        
        # Order by number
        for k_num in sorted(knowledge_statements.keys()):
            k_desc = knowledge_statements[k_num]
            k_list.append(f"K{k_num}: {k_desc}")
        
        for a_num in sorted(ability_statements.keys()):
            a_desc = ability_statements[a_num]
            a_list.append(f"A{a_num}: {a_desc}")
        
        # Update the ensemble output with these statements
        if k_list:
            learning_outcomes_section["Knowledge"] = k_list
            print(f"Added {len(k_list)} Knowledge statements from TSC data")
        
        if a_list:
            learning_outcomes_section["Ability"] = a_list
            print(f"Added {len(a_list)} Ability statements from TSC data")
        
        # Prepare the Knowledge and Ability Mapping structure
        if "Knowledge and Ability Mapping" not in learning_outcomes_section:
            learning_outcomes_section["Knowledge and Ability Mapping"] = {}
        
        # Extract all K and A statements to ensure we have a valid list
        knowledge_statements_list = learning_outcomes_section.get("Knowledge", [])
        ability_statements_list = learning_outcomes_section.get("Ability", [])
        
        # Record all expected K and A factors based on the statements list
        expected_k_factors = [f"K{i+1}" for i in range(len(knowledge_statements_list))]
        expected_a_factors = [f"A{i+1}" for i in range(len(ability_statements_list))]
        
        # SOURCE 1: Extract mapping from TSC data - Course_Proposal_Form
        tsc_mapping = {}
        has_tsc_mapping = False
        try:
            course_proposal_form = tsc_data.get("Course_Proposal_Form", {})
            
            # Look for Learning Unit entries with KA references in the keys
            learning_units = {}
            for key, value in course_proposal_form.items():
                if key.startswith("LU") and "(" in key and ")" in key:
                    learning_units[key] = value
            
            if learning_units:
                has_tsc_mapping = True
                # Extract K and A factors from Learning Unit key strings
                for lu_key, topics in learning_units.items():
                    # Extract LU number from key
                    lu_match = re.match(r'LU(\d+)', lu_key)
                    if not lu_match:
                        continue
                    
                    lu_num = lu_match.group(1)
                    ka_key = f"KA{lu_num}"
                    
                    # Extract K/A factors from parentheses
                    parenthesis_match = re.search(r'\((.*?)\)', lu_key)
                    if not parenthesis_match:
                        continue
                        
                    ka_content = parenthesis_match.group(1)
                    ka_factors = re.findall(r'\b(K\d+|A\d+)\b', ka_content)
                    
                    if ka_factors:  # Only add if we found factors
                        # Add to mapping
                        tsc_mapping[ka_key] = ka_factors
        except Exception as e:
            print(f"Error extracting mapping from TSC Course_Proposal_Form: {e}")
        
        # SOURCE 2: Extract mapping from Learning Units in ensemble_output
        ensemble_mapping = {}
        has_ensemble_mapping = False
        try:
            learning_units = ensemble_data.get("TSC and Topics", {}).get("Learning Units", [])
            
            if learning_units:
                has_ensemble_mapping = True
                # Extract K and A factors from Learning Unit titles in ensemble_output
                for index, lu_title in enumerate(learning_units, start=1):
                    ka_key = f"KA{index}"
                    ka_mapping = []

                    if not isinstance(lu_title, str):
                        continue
                    
                    # Extract K and A factors from the Learning Unit title using regex
                    # This looks for patterns like "LU1: Title (K9, K10, A8, A5)"
                    parenthesis_match = re.search(r'\((.*?)\)', lu_title)
                    if parenthesis_match:
                        # Extract content inside parentheses
                        parenthesis_content = parenthesis_match.group(1)
                        # Find all K and A factors
                        matches = re.findall(r'\b(K\d+|A\d+)\b', parenthesis_content)
                        if matches:
                            ka_mapping.extend(matches)

        # Ensure only unique K and A factors are added
                    if ka_mapping:  # Only add if we found factors
                        ka_mapping = list(dict.fromkeys(ka_mapping))  # Remove duplicates while preserving order
                        ensemble_mapping[ka_key] = ka_mapping
        except Exception as e:
            print(f"Error extracting mapping from ensemble Learning Units: {e}")
        
        # SOURCE 3: Extract mapping from TSC mapping table in raw TSC data
        table_mapping = {}
        has_table_mapping = False
        try:
            # Find the TSC mapping table in TSC data
            tsc_content = tsc_data.get("TSC and Topics", {}).get("content", [])
            for item in tsc_content:
                if isinstance(item, dict) and "table" in item:
                    table = item["table"]
                    # Skip header row
                    if len(table) > 1:
                        has_table_mapping = True
                        # Process each row to extract LU# and K&A mapping
                        for row in table[1:]:  # Skip header row
                            if len(row) >= 5:  # Ensure row has enough columns
                                lu_num = row[0].replace("LU", "")
                                ka_factors_str = row[4]  # K&A column
                                
                                # Extract K/A factors
                                ka_factors = re.findall(r'\b(K\d+|A\d+)\b', ka_factors_str)
                                
                                if ka_factors:  # Only add if we found factors
                                    # Add to mapping
                                    ka_key = f"KA{lu_num}"
                                    if ka_key in table_mapping:
                                        table_mapping[ka_key].extend(ka_factors)
                                    else:
                                        table_mapping[ka_key] = ka_factors
                        
                        # Deduplicate K/A factors in each mapping
                        for ka_key in table_mapping:
                            table_mapping[ka_key] = list(dict.fromkeys(table_mapping[ka_key]))
                    break
        except Exception as e:
            print(f"Error extracting mapping from TSC mapping table: {e}")
        
        # SOURCE 4: Last-resort structured scan - check for all K/A references in any content fields
        content_mapping = {}
        has_content_mapping = False
        
        # Helper function to scan recursive structure for K/A references
        def scan_for_ka_references(obj, lu_pattern=r'LU(\d+)'):
            results = {}
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Check if key contains LU reference
                    lu_match = re.search(lu_pattern, key)
                    if lu_match:
                        lu_num = lu_match.group(1)
                        ka_key = f"KA{lu_num}"
                        
                        # Find all K/A references in the key and value
                        all_text = key + " " + (str(value) if isinstance(value, (str, int, float)) else "")
                        ka_factors = re.findall(r'\b(K\d+|A\d+)\b', all_text)
                        
                        if ka_factors:
                            if ka_key in results:
                                results[ka_key].extend(ka_factors)
                            else:
                                results[ka_key] = ka_factors
                    
                    # Recursively scan value
                    if isinstance(value, (dict, list)):
                        sub_results = scan_for_ka_references(value, lu_pattern)
                        for sub_key, sub_factors in sub_results.items():
                            if sub_key in results:
                                results[sub_key].extend(sub_factors)
                            else:
                                results[sub_key] = sub_factors
            
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        sub_results = scan_for_ka_references(item, lu_pattern)
                        for sub_key, sub_factors in sub_results.items():
                            if sub_key in results:
                                results[sub_key].extend(sub_factors)
                            else:
                                results[sub_key] = sub_factors
                    elif isinstance(item, str):
                        # Find LU references in the string
                        lu_matches = re.finditer(lu_pattern, item)
                        for lu_match in lu_matches:
                            lu_num = lu_match.group(1)
                            ka_key = f"KA{lu_num}"
                            
                            # Find all K/A references in the string
                            ka_factors = re.findall(r'\b(K\d+|A\d+)\b', item)
                            
                            if ka_factors:
                                if ka_key in results:
                                    results[ka_key].extend(ka_factors)
                                else:
                                    results[ka_key] = ka_factors
            
            # Deduplicate results
            for key in results:
                results[key] = list(dict.fromkeys(results[key]))
                
            return results
        
        try:
            # Scan both TSC and ensemble data for K/A references
            tsc_scan_results = scan_for_ka_references(tsc_data)
            ensemble_scan_results = scan_for_ka_references(ensemble_data)
            
            # Merge results
            content_mapping = tsc_scan_results.copy()
            for key, value in ensemble_scan_results.items():
                if key in content_mapping:
                    content_mapping[key].extend(value)
                    content_mapping[key] = list(dict.fromkeys(content_mapping[key]))
                else:
                    content_mapping[key] = value
            
            has_content_mapping = len(content_mapping) > 0
        except Exception as e:
            print(f"Error in fallback content scanning: {e}")
        
        # Get the number of Learning Units we need to map
        num_learning_units = 0
        if has_tsc_mapping:
            num_learning_units = max(num_learning_units, max([int(re.sub(r'KA', '', key)) for key in tsc_mapping.keys()]) if tsc_mapping else 0)
        if has_ensemble_mapping:
            num_learning_units = max(num_learning_units, max([int(re.sub(r'KA', '', key)) for key in ensemble_mapping.keys()]) if ensemble_mapping else 0)
        if has_table_mapping:
            num_learning_units = max(num_learning_units, max([int(re.sub(r'KA', '', key)) for key in table_mapping.keys()]) if table_mapping else 0)
        if has_content_mapping:
            num_learning_units = max(num_learning_units, max([int(re.sub(r'KA', '', key)) for key in content_mapping.keys()]) if content_mapping else 0)
        
        if num_learning_units == 0:
            # If no mapping sources found, use the number of Learning Outcomes as a fallback
            num_learning_units = len(learning_outcomes_section.get("Learning Outcomes", []))
            if num_learning_units == 0:
                # Last resort: default to 4 learning units (common number)
                num_learning_units = 4
                print(f"Warning: No Learning Units found in any source. Using default of {num_learning_units} units.")
        
        # Create the final mapping - using sources in priority order
        final_mapping = {}
        source_used_count = {
            "SOURCE 1": 0,
            "SOURCE 2": 0,
            "SOURCE 3": 0, 
            "SOURCE 4": 0,
            "FALLBACK": 0
        }
        
        # For each Learning Unit, try sources in priority order
        for idx in range(1, num_learning_units + 1):
            ka_key = f"KA{idx}"
            
            # Try SOURCE 1 first (highest priority)
            if ka_key in tsc_mapping and tsc_mapping[ka_key]:
                final_mapping[ka_key] = tsc_mapping[ka_key]
                source_used_count["SOURCE 1"] += 1
                print(f"{ka_key}: Using SOURCE 1 (TSC Course Form) with {len(tsc_mapping[ka_key])} factors")
            
            # If SOURCE 1 didn't have data for this LU, try SOURCE 2
            elif ka_key in ensemble_mapping and ensemble_mapping[ka_key]:
                final_mapping[ka_key] = ensemble_mapping[ka_key]
                source_used_count["SOURCE 2"] += 1
                print(f"{ka_key}: Using SOURCE 2 (Ensemble Learning Units) with {len(ensemble_mapping[ka_key])} factors")
            
            # If SOURCE 2 didn't have data, try SOURCE 3
            elif ka_key in table_mapping and table_mapping[ka_key]:
                final_mapping[ka_key] = table_mapping[ka_key]
                source_used_count["SOURCE 3"] += 1
                print(f"{ka_key}: Using SOURCE 3 (TSC Table) with {len(table_mapping[ka_key])} factors")
            
            # If SOURCE 3 didn't have data, try SOURCE 4
            elif ka_key in content_mapping and content_mapping[ka_key]:
                final_mapping[ka_key] = content_mapping[ka_key]
                source_used_count["SOURCE 4"] += 1
                print(f"{ka_key}: Using SOURCE 4 (Comprehensive Scan) with {len(content_mapping[ka_key])} factors")
            
            # If no source provided data for this LU, generate a reasonable fallback
            else:
                print(f"Warning: No K&A mapping found for {ka_key}. Generating fallback mapping.")
                # Distribute K and A factors evenly across learning units
                k_per_unit = max(1, len(expected_k_factors) // num_learning_units)
                a_per_unit = max(1, len(expected_a_factors) // num_learning_units)
                
                start_k_idx = (idx - 1) * k_per_unit
                end_k_idx = min(start_k_idx + k_per_unit, len(expected_k_factors))
                start_a_idx = (idx - 1) * a_per_unit
                end_a_idx = min(start_a_idx + a_per_unit, len(expected_a_factors))
                
                # Add K and A factors for this unit
                ka_factors = []
                
                # Add K factors for this unit
                for k_idx in range(start_k_idx, end_k_idx):
                    if k_idx < len(expected_k_factors):
                        ka_factors.append(expected_k_factors[k_idx])
                
                # Add A factors for this unit
                for a_idx in range(start_a_idx, end_a_idx):
                    if a_idx < len(expected_a_factors):
                        ka_factors.append(expected_a_factors[a_idx])
                
                final_mapping[ka_key] = ka_factors
                source_used_count["FALLBACK"] += 1
                print(f"{ka_key}: Using FALLBACK with {len(ka_factors)} factors")
        
        # Log source usage summary
        print("\nK&A Mapping Source Usage Summary:")
        print(f"SOURCE 1 (TSC Course Form): {source_used_count['SOURCE 1']} learning units")
        print(f"SOURCE 2 (Ensemble Learning Units): {source_used_count['SOURCE 2']} learning units")
        print(f"SOURCE 3 (TSC Table): {source_used_count['SOURCE 3']} learning units")
        print(f"SOURCE 4 (Comprehensive Scan): {source_used_count['SOURCE 4']} learning units")
        print(f"FALLBACK: {source_used_count['FALLBACK']} learning units")
        
        # Update the ensemble_output with the final mapping
        learning_outcomes_section["Knowledge and Ability Mapping"] = final_mapping

    except Exception as e:
        print(f"Error in update_knowledge_ability_mapping: {e}")
        traceback_info = traceback.format_exc()
        print(f"Traceback:\n{traceback_info}")
        return False

    # Save the updated JSON to the same file path
    with open(ensemble_output_json_path, 'w', encoding='utf-8') as outfile:
        json.dump(ensemble_data, outfile, indent=4, ensure_ascii=False)

    print(f"Updated Knowledge and Ability Mapping saved to {ensemble_output_json_path}")
    return True

def extract_final_agent_json(file_path: str = "assessment_justification_agent_state.json"):
    """
    Reads the specified JSON file (default: 'assessment_justification_agent_state.json'),
    finds the editor agent's final response, and extracts the
    substring from the first '{' to the last '}'.
    
    Attempts to parse the extracted substring as JSON, returning
    a Python dictionary. If parsing fails or if no final message
    is found, returns None.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Identify the assessment_justification_agent key
    agent_name_to_find = "assessment_justification_agent"  # Exact agent name
    found_key = None
    if "agent_states" not in data or not isinstance(data["agent_states"], dict):
        print(f"Warning: 'agent_states' not found or not a dictionary in {file_path}.")
        return {}
        
    for key in data["agent_states"]:
        if key == agent_name_to_find:
            found_key = key
            break

    if not found_key:
        print(f"No key for agent '{agent_name_to_find}' found in agent_states of {file_path}.")
        return {}

    # 2. Get the agent state and retrieve the final message
    agent_state_data = data["agent_states"][found_key]
    if not isinstance(agent_state_data, dict) or "agent_state" not in agent_state_data or \
       not isinstance(agent_state_data["agent_state"], dict) or "llm_context" not in agent_state_data["agent_state"] or \
       not isinstance(agent_state_data["agent_state"]["llm_context"], dict) or "messages" not in agent_state_data["agent_state"]["llm_context"]:
        print(f"Unexpected structure for agent '{found_key}' state in {file_path}.")
        return {}
        
    messages = agent_state_data["agent_state"]["llm_context"]["messages"]
    if not messages or not isinstance(messages, list):
        print(f"No messages found or messages is not a list for agent '{found_key}' in {file_path}.")
        return {}

    final_message_obj = messages[-1]
    if not isinstance(final_message_obj, dict) or "content" not in final_message_obj:
        print(f"Final message for agent '{found_key}' has unexpected structure or no content in {file_path}.")
        return {}

    final_message = final_message_obj.get("content", "")
    if not final_message or not isinstance(final_message, str):
        print(f"Final message for agent '{{found_key}}' is empty or not a string in {{file_path}}.")
        return {{}}

    parsed_json = clean_and_parse_json(final_message)
    if parsed_json is None:
        print(f"CRITICAL: Failed to clean and parse JSON output from '{{agent_name_to_find}}' agent in state file: {{file_path}}")
    return parsed_json

def extract_tsc_agent_json(file_path: str = "tsc_agent_state.json"):
    """
    Reads the specified JSON file (default: 'tsc_agent_state.json'),
    finds the editor agent's final response, and extracts the
    substring from the first '{' to the last '}'.
    
    Attempts to parse the extracted substring as JSON, returning
    a Python dictionary. If parsing fails or if no final message
    is found, returns None.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Identify the tsc_agent key
    tsc_agent_name = "tsc_agent"  # Exact agent name
    found_key = None # Renamed from editor_key for clarity
    if "agent_states" not in data or not isinstance(data["agent_states"], dict):
        print(f"Warning: 'agent_states' not found or not a dictionary in {file_path}.")
        return {}

    for key in data["agent_states"]:
        if key == tsc_agent_name:
            found_key = key
            break

    if not found_key:
        print(f"No key for agent '{tsc_agent_name}' found in agent_states of {file_path}.") # Updated log message
        return {}

    # 2. Get the tsc_agent state and retrieve the final message
    agent_state_data = data["agent_states"][found_key] # Renamed from aggregator_state and editor_state
    if not isinstance(agent_state_data, dict) or "agent_state" not in agent_state_data or \
       not isinstance(agent_state_data["agent_state"], dict) or "llm_context" not in agent_state_data["agent_state"] or \
       not isinstance(agent_state_data["agent_state"]["llm_context"], dict) or "messages" not in agent_state_data["agent_state"]["llm_context"]:
        print(f"Unexpected structure for agent '{found_key}' state in {file_path}.")
        return {}

    messages = agent_state_data["agent_state"]["llm_context"]["messages"]
    if not messages or not isinstance(messages, list):
        print(f"No messages found or messages is not a list for agent '{found_key}' in {file_path}.") # Updated log message
        return {}

    final_message_obj = messages[-1]
    if not isinstance(final_message_obj, dict) or "content" not in final_message_obj:
        print(f"Final message for agent '{found_key}' has unexpected structure or no content in {file_path}.")
        return {}
        
    final_message = final_message_obj.get("content", "")
    if not final_message or not isinstance(final_message, str):
        print(f"Final message for agent '{found_key}' is empty or not a string in {file_path}.") # Updated log message
        return {{}}

    parsed_json = clean_and_parse_json(final_message)
    if parsed_json is None:
        print(f"CRITICAL: Failed to clean and parse JSON output from tsc_agent in state file: {{file_path}}")
    return parsed_json


# Function to recursively flatten lists within the JSON structure
def flatten_json(obj):
    if isinstance(obj, dict):
        # Recursively apply to dictionary values
        return {k: flatten_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Flatten the list and apply to each element in the list
        return flatten_list(obj)
    else:
        return obj

# Function to flatten any nested list
def flatten_list(nested_list):
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))  # Recursively flatten any nested lists
        else:
            flat_list.append(item)
    return flat_list

import json

def append_validation_output(
    ensemble_output_path: str = "ensemble_output.json",
    validation_output_path: str = "validation_output.json",
    analyst_responses: list = None
):
    """
    Reads data from `ensemble_output.json` and appends the new course information 
    into `validation_output.json`. If `validation_output.json` already exists, 
    it will append the new course data instead of overwriting it.

    Additionally, it allows appending `analyst_responses` as a list of dictionaries 
    containing responses about industry performance gaps and course impact.

    Structure:
    {
        "course_info": { Course Title, Industry, Learning Outcomes, TSC Title, TSC Code },
        "analyst_responses": [ {...}, {...} ]  # List of analyst responses
    }
    """

    # Load the existing data if the file exists, otherwise start fresh
    if os.path.exists(validation_output_path):
        with open(validation_output_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = {}
    else:
        existing_data = {}

    # Load ensemble_output.json
    with open(ensemble_output_path, "r", encoding="utf-8") as f:
        ensemble_data = json.load(f)

    # Extract required fields
    course_title = ensemble_data.get("Course Information", {}).get("Course Title", "")
    industry = ensemble_data.get("Course Information", {}).get("Industry", "")
    learning_outcomes = ensemble_data.get("Learning Outcomes", {}).get("Learning Outcomes", [])
    
    # Extract TSC Title and TSC Code (first element if list exists)
    tsc_titles = ensemble_data.get("TSC and Topics", {}).get("TSC Title", [])
    tsc_codes = ensemble_data.get("TSC and Topics", {}).get("TSC Code", [])

    ensemble_tsc_title = tsc_titles[0] if tsc_titles and isinstance(tsc_titles, list) and len(tsc_titles) > 0 else ""
    ensemble_tsc_code = tsc_codes[0] if tsc_codes and isinstance(tsc_codes, list) and len(tsc_codes) > 0 else ""
    
    # Initialize or get existing course_info
    course_info = existing_data.get("course_info", {})
    if not isinstance(course_info, dict):
        course_info = {}
    
    # Check if the existing TSC values are placeholders or invalid
    existing_tsc_title = course_info.get("TSC Title", "")
    existing_tsc_code = course_info.get("TSC Code", "")
    
    # Define known placeholder values to detect and replace
    placeholder_values = ["Title", "Code", "TSC Title", "TSC Code", 
                          "placeholder", "sample", "example", "unknown"]
    
    # Validate TSC Title - check if it's a placeholder or very short string
    is_tsc_title_invalid = (
        not existing_tsc_title or 
        existing_tsc_title.lower() in [p.lower() for p in placeholder_values] or
        len(existing_tsc_title) <= 2 or  # Too short to be valid
        existing_tsc_title.startswith("The EXACT") or  # Template text
        "from ensemble_output" in existing_tsc_title  # Template text
    )
    
    # Validate TSC Code - check if it's a placeholder or not in expected format
    is_tsc_code_invalid = (
        not existing_tsc_code or 
        existing_tsc_code.lower() in [p.lower() for p in placeholder_values] or
        len(existing_tsc_code) <= 2 or  # Too short to be valid
        existing_tsc_code.startswith("The EXACT") or  # Template text
        "from ensemble_output" in existing_tsc_code or  # Template text
        not re.search(r'\w+-\w+-\d+', existing_tsc_code)  # Not in expected format like ACC-ADV-0002
    )
    
    # Build the course information dictionary, using ensemble data as the source of truth
    new_course_info = {
        "Course Title": course_title or course_info.get("Course Title", ""),
        "Industry": industry or course_info.get("Industry", ""),
        "Learning Outcomes": learning_outcomes or course_info.get("Learning Outcomes", []),
        # Only replace TSC values if they're invalid or empty
        "TSC Title": ensemble_tsc_title if is_tsc_title_invalid else existing_tsc_title,
        "TSC Code": ensemble_tsc_code if is_tsc_code_invalid else existing_tsc_code
    }
    
    # Log what's happening
    if is_tsc_title_invalid and ensemble_tsc_title:
        print(f"Fixing invalid TSC Title: '{existing_tsc_title}' → '{ensemble_tsc_title}'")
    if is_tsc_code_invalid and ensemble_tsc_code:
        print(f"Fixing invalid TSC Code: '{existing_tsc_code}' → '{ensemble_tsc_code}'")

    # Update the course_info
    existing_data["course_info"] = new_course_info

    # Handle analyst_responses (ensure it's a list in the final output)
    if analyst_responses:
        if "analyst_responses" not in existing_data:
            existing_data["analyst_responses"] = []
        existing_data["analyst_responses"].extend(analyst_responses)

    # Write back to validation_output.json
    with open(validation_output_path, "w", encoding="utf-8") as out_f:
        json.dump(existing_data, out_f, indent=2)

    print(f"Updated validation data saved to {validation_output_path}.")

def safe_json_loads(json_str):
    """Fix common JSON issues like unescaped quotes before parsing."""
    # Escape unescaped double quotes within strings
    json_str = re.sub(r'(?<!\\)"(?![:,}\]\s])', r'\"', json_str)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error: {e}")
        return None

def load_json_file(file_path):
    """Loads JSON data from a file and ensures it is a list or dict."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            if not isinstance(data, (list, dict)):
                print(f"Error: JSON loaded from '{file_path}' is not a list or dict, got {type(data)}")
                return None
            return data
    except FileNotFoundError:
        print(f"Error: JSON file not found at '{file_path}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from file '{file_path}'. Please ensure it is valid JSON.")
        return None

def extract_lo_keys(json_data):
    """
    Extracts keys that match the pattern '#LO' followed by a number.

    Args:
        json_data (dict): The JSON data as a dictionary.

    Returns:
        list: A list of keys that match the pattern '#LO' followed by a number.
    """
    lo_keys = []
    pattern = re.compile(r'^#LO\d+$')
    for key in json_data.keys():
        print(f"Checking key: {key}")  # Debugging statement
        if pattern.match(key):
            print(f"Matched key: {key}")  # Debugging statement
            lo_keys.append(key)
    return lo_keys

def recursive_get_keys(json_data, key_prefix=""):
    """
    Extracts keys from a JSON dictionary that start with '#Topics' and returns them as a list.

    Args:
        json_data (dict): A dictionary loaded from a JSON file.

    Returns:
        list: A list of strings, where each string is a key from the json_data
              that starts with '#Topics'. For example: ['#Topics[0]', '#Topics[1]', '#Topics[2]', ...].
              Returns an empty list if no keys start with '#Topics'.
    """
    topic_keys = []
    for key in json_data.keys():
        # if key.startswith("#Topics"):
        if key.startswith(key_prefix):
            topic_keys.append(key)
    return topic_keys

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

    # Identify the agent key (support both new and old formats)
    agent_key = None
    for key in data.get("agent_states", {}):
        if key.startswith(f"{agent_name}/") or key == agent_name:
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

    parsed_json = clean_and_parse_json(final_message)
    if parsed_json is None:
        print(f"CRITICAL: Failed to clean and parse JSON output from '{{agent_name}}' agent in state file: {{file_path}}")
    return parsed_json

def clean_and_parse_json(llm_output_string: str) -> dict | None:
    """
    Attempts to clean and parse a JSON string that might have common LLM errors.
    Returns a dictionary if successful, None otherwise.
    """
    if not isinstance(llm_output_string, str):
        print(f"[JSON Cleaner] Input is not a string: {type(llm_output_string)}")
        return None

    # 1. Strip leading/trailing whitespace
    cleaned_string = llm_output_string.strip()

    # 2. Remove markdown code block fences (```json ... ``` or ``` ... ```)
    cleaned_string = re.sub(r"^```(?:json)?\s*\n?|\n?\s*```$", "", cleaned_string, flags=re.DOTALL).strip()
    
    # 3. Handle potential byte order mark (BOM) if present
    if cleaned_string.startswith('\ufeff'):
        cleaned_string = cleaned_string[1:]

    # 4. Remove any non-JSON text before the first '{' and after the last '}'
    first_brace = cleaned_string.find('{')
    last_brace = cleaned_string.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned_string = cleaned_string[first_brace:last_brace+1]

    # 5. Try to parse the cleaned JSON directly first
    try:
        return json.loads(cleaned_string)
    except json.JSONDecodeError as e:
        # Log the initial error
        error_snippet = cleaned_string[:500]
        print(f"[JSON Cleaner] Initial JSON parsing failed: {e}")
        print(f"[JSON Cleaner] Problematic JSON string snippet (first 500 chars): {error_snippet}...")
        
        # 6. Apply more aggressive cleaning steps for common LLM JSON errors
        try:
            # Fix trailing commas in objects: { "a": 1, "b": 2, }
            cleaned_string = re.sub(r',\s*}', '}', cleaned_string)
            # Fix trailing commas in arrays: [ 1, 2, 3, ]
            cleaned_string = re.sub(r',\s*]', ']', cleaned_string)
            
            # Fix missing quotes around keys: {key: "value"} -> {"key": "value"}
            cleaned_string = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned_string)
            
            # Try parsing again after these fixes
            try:
                return json.loads(cleaned_string)
            except json.JSONDecodeError as e2:
                print(f"[JSON Cleaner] Still failed after basic fixes: {e2}")
                
                # 7. Try json5 if available
                try:
                    import json5
                    print("[JSON Cleaner] Attempting to parse with json5...")
                    return json5.loads(cleaned_string)
                except (ImportError, Exception) as e3:
                    print(f"[JSON Cleaner] JSON5 parsing failed or not available: {e3}")
                    
                    # 8. Last resort: Try to extract valid JSON with balanced braces
                    try:
                        # Find balanced braces
                        stack = []
                        potential_jsons = []
                        start_index = -1
                        
                        for i, char in enumerate(cleaned_string):
                            if char == '{':
                                if not stack:  # Start of a potential JSON object
                                    start_index = i
                                stack.append('{')
                            elif char == '}' and stack:
                                stack.pop()
                                if not stack and start_index != -1:  # End of a balanced JSON object
                                    potential_jsons.append(cleaned_string[start_index:i+1])
                        
                        # Try each potential JSON object from largest to smallest
                        if potential_jsons:
                            for potential_json in sorted(potential_jsons, key=len, reverse=True):
                                try:
                                    parsed = json.loads(potential_json)
                                    print("[JSON Cleaner] Successfully extracted JSON with balanced braces approach")
                                    return parsed
                                except Exception:
                                    # Try next potential JSON
                                    continue
                                    
                        print("[JSON Cleaner] Could not extract valid JSON with balanced braces approach")
                    except Exception as e4:
                        print(f"[JSON Cleaner] Last resort extraction failed: {e4}")
        except Exception as e_general:
            print(f"[JSON Cleaner] General error during advanced cleaning: {e_general}")
    
    # If all attempts fail, return None
    print("[JSON Cleaner] All JSON parsing attempts failed.")
    return None
