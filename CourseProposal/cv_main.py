from CourseProposal.agents.course_validation_team import create_course_validation_team, validation_task
from autogen_agentchat.ui import Console
from CourseProposal.utils.helpers import (
    extract_final_editor_json,
    append_validation_output,
)
from CourseProposal.utils.json_docu_replace import replace_placeholders_in_doc
import json
import asyncio
import sys
import os

async def create_course_validation(model_choice: str) -> None:
    # Load the JSON file into a Python variable
    with open('CourseProposal/json_output/ensemble_output.json', 'r', encoding="utf-8") as file:
        ensemble_output = json.load(file)    
    # Course Validation Form Process
    validation_group_chat = create_course_validation_team(ensemble_output, model_choice=model_choice)
    stream = validation_group_chat.run_stream(task=validation_task(ensemble_output))
    await Console(stream)

    # Validation Team JSON management
    state = await validation_group_chat.save_state()
    with open("CourseProposal/json_output/validation_group_chat_state.json", "w") as f:
        json.dump(state, f)
    
    # Extract editor data with better error handling
    try:
        editor_data = extract_final_editor_json("CourseProposal/json_output/validation_group_chat_state.json")
        if editor_data is None:
            print("Warning: Editor data extraction returned None. Checking analyst data directly...")
            # Try to find analyst data directly in the group chat state
            with open("CourseProposal/json_output/validation_group_chat_state.json", "r") as f:
                chat_state = json.load(f)
                
            analyst_messages = []
            for agent_key, agent_state in chat_state.get("agent_states", {}).items():
                if agent_key == "analyst" or agent_key.startswith("analyst/"):
                    messages = agent_state.get("agent_state", {}).get("llm_context", {}).get("messages", [])
                    if messages and len(messages) > 0:
                        analyst_messages = [msg.get("content", "") for msg in messages if msg.get("role") == "assistant"]
            
            # If we found analyst messages, try to parse the last one
            if analyst_messages:
                last_analyst_message = analyst_messages[-1]
                editor_data = clean_and_parse_json(last_analyst_message)
                print("Fallback: Used analyst message directly as editor_data")
        
        # If we still don't have valid editor_data, create a minimal structure
        if editor_data is None:
            print("Warning: Couldn't extract valid JSON from either editor or analyst. Creating minimal structure.")
            editor_data = {
                "course_info": {},
                "analyst_responses": []
            }
    except Exception as e:
        print(f"Error extracting editor data: {e}")
        editor_data = {
            "course_info": {},
            "analyst_responses": []
        }
    
    # Save the editor data
    with open("CourseProposal/json_output/validation_output.json", "w", encoding="utf-8") as out:
        json.dump(editor_data, out, indent=2)
    
    # Try to update validation output with data from ensemble_output
    try:
        append_validation_output(
            "CourseProposal/json_output/ensemble_output.json",
            "CourseProposal/json_output/validation_output.json",
        )
    except Exception as e:
        print(f"Warning: Failed to append validation output: {e}")
    
    # Load the validation output for further processing
    try:
        with open('CourseProposal/json_output/validation_output.json', 'r') as file:
            validation_output = json.load(file)
    except Exception as e:
        print(f"Error loading validation_output.json: {e}")
        validation_output = {"course_info": {}, "analyst_responses": []}
        
    # If validation_output is a JSON string, parse it first
    if isinstance(validation_output, str):
        try:
            validation_output = json.loads(validation_output)
        except Exception as e:
            print(f"Error parsing validation_output JSON string: {e}")
            validation_output = {"course_info": {}, "analyst_responses": []}

    # Verify course_info and fix any issues with TSC Title and Code
    if "course_info" in validation_output:
        course_info = validation_output["course_info"]
        
        # Re-load the original ensemble output to verify against
        with open('CourseProposal/json_output/ensemble_output.json', 'r', encoding="utf-8") as file:
            ensemble_output = json.load(file)
        
        # Get correct TSC values from ensemble output
        tsc_titles = ensemble_output.get("TSC and Topics", {}).get("TSC Title", [])
        tsc_codes = ensemble_output.get("TSC and Topics", {}).get("TSC Code", [])
        
        correct_tsc_title = tsc_titles[0] if tsc_titles and isinstance(tsc_titles, list) and len(tsc_titles) > 0 else ""
        correct_tsc_code = tsc_codes[0] if tsc_codes and isinstance(tsc_codes, list) and len(tsc_codes) > 0 else ""
        
        # Validate and correct if needed
        if not correct_tsc_title or not correct_tsc_code:
            print("Warning: Could not find valid TSC Title or Code in ensemble_output.json")
        else:
            # Check current values
            current_tsc_title = course_info.get("TSC Title", "")
            current_tsc_code = course_info.get("TSC Code", "")
            
            # Placeholder detection
            placeholder_values = ["G", "A", "Title", "Code", "TSC Title", "TSC Code"]
            
            # Fix if the values are invalid/placeholder values
            if not current_tsc_title or current_tsc_title in placeholder_values or len(current_tsc_title) <= 2:
                print(f"CV Main: Fixing invalid TSC Title: '{current_tsc_title}' → '{correct_tsc_title}'")
                course_info["TSC Title"] = correct_tsc_title
                
            if not current_tsc_code or current_tsc_code in placeholder_values or len(current_tsc_code) <= 2:
                print(f"CV Main: Fixing invalid TSC Code: '{current_tsc_code}' → '{correct_tsc_code}'")
                course_info["TSC Code"] = correct_tsc_code
            
            # Apply the changes back to validation_output
            validation_output["course_info"] = course_info
            
            # Save the corrected version
            with open("CourseProposal/json_output/validation_output.json", "w", encoding="utf-8") as out:
                json.dump(validation_output, out, indent=2)
                print("Saved corrected validation output with verified TSC information")
    
    # Load mapping template with key:empty list pair
    with open('CourseProposal/json_output/validation_mapping_source.json', 'r') as file:
        validation_mapping_source = json.load(file) 
    # Step 2: Loop through the responses and create three different output documents
    responses = validation_output.get('analyst_responses', [])
    if len(responses) < 3:
        print("Error: Less than 3 responses found in the JSON file.")
        sys.exit(1)

    # load CV templates
    CV_template_1 = "CourseProposal/templates/CP_validation_template_bernard.docx"
    CV_template_2 = "CourseProposal/templates/CP_validation_template_dwight.docx"
    CV_template_3 = "CourseProposal/templates/CP_validation_template_ferris.docx"
    CV_templates = [CV_template_1, CV_template_2, CV_template_3]
    # Iterate over responses and templates
    for i, (response, CV_template) in enumerate(zip(responses[:3], CV_templates), 1):
        # Check that 'course_info' is in 'data'
        course_info = validation_output.get("course_info")
        if not course_info:
            print(f"Error: 'course_info' is missing from the JSON data during iteration {i}.")
            sys.exit(1)
        
        # Verify TSC Title and Code one more time before creating the temp file
        if "TSC Title" not in course_info or not course_info["TSC Title"] or course_info["TSC Title"] in ["G", "A"] or len(course_info["TSC Title"]) <= 2:
            print(f"Warning: Invalid TSC Title: '{course_info.get('TSC Title', '')}' in temp_response_{i}.json")
            # Re-load ensemble_output to get correct values
            with open('CourseProposal/json_output/ensemble_output.json', 'r', encoding="utf-8") as file:
                ensemble_data = json.load(file)
            tsc_titles = ensemble_data.get("TSC and Topics", {}).get("TSC Title", [])
            if tsc_titles and isinstance(tsc_titles, list) and len(tsc_titles) > 0:
                correct_tsc_title = tsc_titles[0]
                print(f"Final fix: Replacing TSC Title with '{correct_tsc_title}'")
                course_info["TSC Title"] = correct_tsc_title
                
        if "TSC Code" not in course_info or not course_info["TSC Code"] or course_info["TSC Code"] in ["G", "A"] or len(course_info["TSC Code"]) <= 2:
            print(f"Warning: Invalid TSC Code: '{course_info.get('TSC Code', '')}' in temp_response_{i}.json")
            # Re-load ensemble_output to get correct values
            with open('CourseProposal/json_output/ensemble_output.json', 'r', encoding="utf-8") as file:
                ensemble_data = json.load(file)
            tsc_codes = ensemble_data.get("TSC and Topics", {}).get("TSC Code", [])
            if tsc_codes and isinstance(tsc_codes, list) and len(tsc_codes) > 0:
                correct_tsc_code = tsc_codes[0]
                print(f"Final fix: Replacing TSC Code with '{correct_tsc_code}'")
                course_info["TSC Code"] = correct_tsc_code
        
        # Create a temporary JSON file for the current response
        temp_response_json = f"CourseProposal/json_output/temp_response_{i}.json"
        
        # Prepare the content to write to the JSON file
        json_content = {
            "course_info": course_info,
            "analyst_responses": [response]
        }
        
        # Write to the temporary JSON file
        with open(temp_response_json, 'w', encoding="utf-8") as temp_file:
            json.dump(json_content, temp_file, indent=4)

        # Debugging: Print the contents of temp_response_json to confirm correctness
        print(f"Debug: Contents of temp_response_json ({temp_response_json}):")
        with open(temp_response_json, 'r', encoding="utf-8") as temp_file:
            print(temp_file.read())
            analyst_response = json_content["analyst_responses"][0]

        # Extract the name of the word template without the file extension
        template_name_without_extension = os.path.splitext(os.path.basename(CV_template))[0]
        output_directory = "CourseProposal/output_docs"
        os.makedirs(output_directory, exist_ok=True)   
        # Define the output file name for this response in the same directory as the input file
        output_docx_version = os.path.join(output_directory, f"{template_name_without_extension}_updated.docx")


        replace_placeholders_in_doc(temp_response_json, CV_template, output_docx_version, analyst_response)


if __name__ == "__main__":
    asyncio.run(create_course_validation())
