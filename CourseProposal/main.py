from CourseProposal.utils.document_parser import parse_document
from CourseProposal.agents.extraction_team import create_extraction_team, extraction_task
from CourseProposal.agents.research_team import create_research_team, research_task
from CourseProposal.agents.justification_agent import run_assessment_justification_agent, recreate_assessment_phrasing_dynamic, justification_task
from CourseProposal.agents.course_validation_team import create_course_validation_team
from CourseProposal.agents.tsc_agent import create_tsc_agent, tsc_agent_task
from autogen_agentchat.ui import Console
from CourseProposal.utils.helpers import (
    extract_final_aggregator_json, 
    rename_keys_in_json_file,
    update_knowledge_ability_mapping,
    validate_knowledge_and_ability,
    extract_final_editor_json,
    extract_final_agent_json,
    flatten_json,
    flatten_list,
    extract_tsc_agent_json,
    fix_missing_ka_references,
)
from CourseProposal.utils.json_mapping import map_values
from CourseProposal.utils.jinja_docu_replace import replace_placeholders_with_docxtpl
import json
from CourseProposal.cv_main import create_course_validation
import streamlit as st
from CourseProposal.excel_main import process_excel
import os
import shutil
from datetime import datetime

def clear_session_state():
    """Clear all relevant session states"""
    states_to_clear = [
        'ka_validation_results',
        'error',
        'warning',
        'process_state',
        'last_successful_step'
    ]
    for state in states_to_clear:
        if state in st.session_state:
            del st.session_state[state]

def backup_and_clear_file(file_path):
    """Backup and clear a file if it exists"""
    try:
        if os.path.exists(file_path):
            # Create backup
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
            # Clear the file
            with open(file_path, 'w') as f:
                json.dump({}, f)
            return True
    except Exception as e:
        print(f"Warning: Could not handle {file_path}: {e}")
        return False

def validate_json_file(file_path, required_keys=None):
    """Validate a JSON file exists and has required structure"""
    try:
        if not os.path.exists(file_path):
            return False, f"File {file_path} does not exist"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if required_keys and isinstance(data, dict):
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                return False, f"Missing required keys: {missing_keys}"
        
        return True, data
    except json.JSONDecodeError:
        return False, f"Invalid JSON in {file_path}"
    except Exception as e:
        return False, f"Error reading {file_path}: {str(e)}"

def update_process_state(step_name, status, error=None):
    """Update the process state in session state"""
    if 'process_state' not in st.session_state:
        st.session_state['process_state'] = {}
    
    st.session_state['process_state'][step_name] = {
        'status': status,
        'error': error,
        'timestamp': datetime.now().isoformat()
    }

async def main(input_tsc) -> None:
    # Clear all relevant session states
    clear_session_state()
    
    # Initialize process state
    st.session_state['process_state'] = {}
    st.session_state['last_successful_step'] = None

    # Critical files to manage
    critical_files = [
        "CourseProposal/json_output/ensemble_output.json",
        "CourseProposal/json_output/research_output.json",
        "CourseProposal/json_output/generated_mapping.json",
        "CourseProposal/json_output/output_TSC.json",
        "CourseProposal/json_output/output_TSC_raw.json"
    ]
    
    # Clear and backup critical files
    for file_path in critical_files:
        if not backup_and_clear_file(file_path):
            st.error(f"Failed to prepare {file_path} for processing")
            return

    try:
        model_choice = st.session_state.get('selected_model', "GPT-4o Mini (Default)")
        cp_type = st.session_state.get('cp_type', "New CP")

        # Parse document
        update_process_state('document_parsing', 'in_progress')
        parse_document(input_tsc, "CourseProposal/json_output/output_TSC_raw.json")
        update_process_state('document_parsing', 'completed')

        # TSC Agent Process
        update_process_state('tsc_agent', 'in_progress')
        with open("CourseProposal/json_output/output_TSC_raw.json", 'r', encoding='utf-8') as file:
            tsc_data = json.load(file)
        
        tsc_agent = create_tsc_agent(tsc_data=tsc_data, model_choice=model_choice)
        stream = tsc_agent.run_stream(task=tsc_agent_task(tsc_data))
        await Console(stream)

        state = await tsc_agent.save_state()
        with open("CourseProposal/json_output/tsc_agent_state.json", "w") as f:
            json.dump(state, f)
        
        tsc_data = extract_tsc_agent_json("CourseProposal/json_output/tsc_agent_state.json")
        if tsc_data is None:
            update_process_state('tsc_agent', 'failed', "Failed to extract TSC agent JSON output")
            st.error("Critical error: Failed to extract or parse TSC agent JSON output. Pipeline cannot continue.")
            return

        with open("CourseProposal/json_output/output_TSC.json", "w", encoding="utf-8") as out:
            json.dump(tsc_data, out, indent=2)
        update_process_state('tsc_agent', 'completed')
        st.session_state['last_successful_step'] = 'tsc_agent'

        # Extraction Process
        update_process_state('extraction', 'in_progress')
        group_chat = create_extraction_team(tsc_data, model_choice=model_choice)
        stream = group_chat.run_stream(task=extraction_task(tsc_data))
        await Console(stream)

        state = await group_chat.save_state()
        with open("CourseProposal/json_output/group_chat_state.json", "w") as f:
            json.dump(state, f)
        
        aggregator_data = extract_final_aggregator_json("CourseProposal/json_output/group_chat_state.json")
        if aggregator_data is None:
            update_process_state('extraction', 'failed', "Failed to extract aggregator JSON output")
            st.error("Critical error: Failed to extract or parse aggregator JSON output. Pipeline cannot continue.")
            return

        with open("CourseProposal/json_output/ensemble_output.json", "w", encoding="utf-8") as out:
            json.dump(aggregator_data, out, indent=2)
        update_process_state('extraction', 'completed')
        st.session_state['last_successful_step'] = 'extraction'

        # JSON key validation for ensemble_output to ensure that key names are constant
        rename_keys_in_json_file("CourseProposal/json_output/ensemble_output.json")

        try:
            update_knowledge_ability_mapping('CourseProposal/json_output/output_TSC.json', 'CourseProposal/json_output/ensemble_output.json')
        except Exception as e:
            print(f"Warning: Knowledge and Ability mapping update failed: {e}")
            st.warning(f"Knowledge and Ability mapping update failed: {e}")

        print("\n--- Validating Knowledge and Ability factor coverage ---")
        # First try to fix any missing K&A references
        try:
            fix_results = fix_missing_ka_references()
        except Exception as e:
            print(f"Warning: Failed to fix missing K&A references: {e}")
            fix_results = {"success": False, "error": str(e), "fixed_count": 0}
        
        # Then run the validation
        try:
            validation_results = validate_knowledge_and_ability()
        except Exception as e:
            print(f"Warning: Knowledge and Ability validation failed: {e}")
            validation_results = {"success": False, "error": str(e)}
        
        # Store validation results in session state for Streamlit UI
        if 'ka_validation_results' not in st.session_state:
            st.session_state['ka_validation_results'] = {}
        st.session_state['ka_validation_results']['fix_results'] = fix_results
        st.session_state['ka_validation_results']['validation_results'] = validation_results

        # Research Team Process
        with open("CourseProposal/json_output/ensemble_output.json", 'r', encoding='utf-8') as file:
            ensemble_output = json.load(file)  
        research_group_chat = create_research_team(ensemble_output, model_choice=model_choice)
        stream = research_group_chat.run_stream(task=research_task(ensemble_output))
        await Console(stream)

        # Research Team JSON management
        state = await research_group_chat.save_state()
        with open("CourseProposal/json_output/research_group_chat_state.json", "w") as f:
            json.dump(state, f)
        editor_data = extract_final_editor_json("CourseProposal/json_output/research_group_chat_state.json")
        if editor_data is None:
            st.error("Critical error: Failed to extract or parse research editor JSON output. Pipeline cannot continue.")
            return  # Exit the main function
        with open("CourseProposal/json_output/research_output.json", "w", encoding="utf-8") as out:
            json.dump(editor_data, out, indent=2)

        with open("CourseProposal/json_output/ensemble_output.json", 'r', encoding='utf-8') as file:
            ensemble_output = json.load(file)   

        if cp_type == "Old CP":
            # Justification Agent Process
            justification_agent = run_assessment_justification_agent(ensemble_output, model_choice=model_choice)
            stream = justification_agent.run_stream(task=justification_task(ensemble_output))
            await Console(stream)

            justification_state = await justification_agent.save_state()
            with open("CourseProposal/json_output/assessment_justification_agent_state.json", "w") as f:
                json.dump(justification_state, f)
            justification_data = extract_final_agent_json("CourseProposal/json_output/assessment_justification_agent_state.json")  
            if justification_data is None:
                st.error("Critical error: Failed to extract or parse justification agent JSON output. Pipeline cannot continue with assessment justification generation.")
                # Instead of returning, we'll continue since this is an optional part
                # But we'll skip the rest of this if block
            else:
                with open("CourseProposal/json_output/justification_debug.json", "w") as f:
                    json.dump(justification_data, f)  
                output_phrasing = recreate_assessment_phrasing_dynamic(justification_data)
                # Load the existing research_output.json
                with open('CourseProposal/json_output/research_output.json', 'r', encoding='utf-8') as f:
                    research_output = json.load(f)
                
                # Append the new output phrasing to the research_output
                if "Assessment Phrasing" not in research_output:
                    research_output["Assessment Phrasing"] = []
                # Append the new result
                research_output["Assessment Phrasing"].append(output_phrasing)

                # Save the updated research_output.json
                with open('CourseProposal/json_output/research_output.json', 'w', encoding='utf-8') as f:
                    json.dump(research_output, f, indent=4)
        
        if cp_type == "New CP":
            with open('CourseProposal/json_output/research_output.json', 'r', encoding='utf-8') as f:
                research_output = json.load(f)


        # Load CP Template with placeholders
        with open('CourseProposal/json_output/output_CP.json', 'r') as file:
            output_CP = json.load(file)

        # Load mapping template with key:empty list pair
        with open('CourseProposal/json_output/mapping_source.json', 'r') as file:
            mapping_source = json.load(file)

        with open('CourseProposal/json_output/ensemble_output.json', encoding='utf-8') as f:
            ensemble_output = json.load(f)    

        updated_mapping_source = map_values(mapping_source, ensemble_output, research_output)
        try:
            with open('CourseProposal/json_output/generated_mapping.json', 'w') as json_file:
                json.dump(updated_mapping_source, json_file, indent=4)
            print(f"Output saved to json_output/generated_mapping.json")
        except IOError as e:
            print(f"Error saving JSON to file: {e}")   

        # Load the JSON file
        with open('CourseProposal/json_output/generated_mapping.json', 'r') as file:
            gmap = json.load(file) 
        # Flatten the JSON
        flattened_gmap = flatten_json(gmap)    
        # Save the flattened JSON back to the file
        output_filename = 'CourseProposal/json_output/generated_mapping.json'
        try:
            with open(output_filename, 'w') as json_file:
                json.dump(flattened_gmap, json_file, indent=4)
            print(f"Output saved to {output_filename}")
        except IOError as e:
            print(f"Error saving JSON to file: {e}")

        json_file = "CourseProposal/json_output/generated_mapping.json"
        word_file = "CourseProposal/templates/CP Template_jinja.docx"
        new_word_file = "CourseProposal/output_docs/CP_output.docx"       
        replace_placeholders_with_docxtpl(json_file, word_file, new_word_file)

        # Research Team JSON management
        state = await research_group_chat.save_state()
        with open("CourseProposal/json_output/research_group_chat_state.json", "w") as f:
            json.dump(state, f)
        editor_data = extract_final_editor_json("CourseProposal/json_output/research_group_chat_state.json")
        if editor_data is None:
            st.error("Critical error: Failed to extract or parse research editor JSON output a second time. Continuing with previous data.")
            # Continue with previously saved data
        else:
            with open("CourseProposal/json_output/research_output.json", "w", encoding="utf-8") as out:
                json.dump(editor_data, out, indent=2)
        
        # Course Validation Form Process
        await create_course_validation(model_choice=model_choice)

        if cp_type == "New CP":
            # # uncomment when ready to insert excel processing
            await process_excel(model_choice=model_choice)
        
    except Exception as e:
        # Log the error and update process state
        error_msg = f"Unexpected error: {str(e)}"
        update_process_state('main_process', 'failed', error_msg)
        st.error(error_msg)
        
        # If we have a last successful step, we can potentially recover
        if st.session_state['last_successful_step']:
            st.warning(f"Process failed. Last successful step was: {st.session_state['last_successful_step']}")
            
            # Offer recovery options
            if st.button("Attempt Recovery"):
                # Implement recovery logic based on last successful step
                pass

# if __name__ == "__main__":
#     asyncio.run(main())
