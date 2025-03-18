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
)
from CourseProposal.utils.json_mapping import map_values
from CourseProposal.utils.jinja_docu_replace import replace_placeholders_with_docxtpl
import json
from CourseProposal.cv_main import create_course_validation
import streamlit as st
from CourseProposal.excel_main import process_excel

async def main(input_tsc) -> None:
    model_choice = st.session_state.get('selected_model', "GPT-4o Mini (Default)")
    # Parse document
    parse_document(input_tsc, "CourseProposal/json_output/output_TSC.json")
    # load the json variables first then pass it in, if you pass it in within the agent scripts it will load the previous json states
    # Load the JSON file into a Python variable
    with open("CourseProposal/json_output/output_TSC.json", 'r', encoding='utf-8') as file:
        tsc_data = json.load(file)        
    # TSC Agent Process
    tsc_agent = create_tsc_agent(tsc_data=tsc_data, model_choice=model_choice)
    stream = tsc_agent.run_stream(task=tsc_agent_task(tsc_data))
    await Console(stream)
    #TSC JSON management
    state = await tsc_agent.save_state()
    with open("CourseProposal/json_output/tsc_agent_state.json", "w") as f:
        json.dump(state, f)
    tsc_data = extract_tsc_agent_json("CourseProposal/json_output/tsc_agent_state.json")
    with open("CourseProposal/json_output/output_TSC.json", "w", encoding="utf-8") as out:
        json.dump(tsc_data, out, indent=2)

    # Extraction Process
    with open("CourseProposal/json_output/output_TSC.json", 'r', encoding='utf-8') as file:
        tsc_data = json.load(file)    
    group_chat = create_extraction_team(tsc_data, model_choice=model_choice)
    stream = group_chat.run_stream(task=extraction_task(tsc_data))
    await Console(stream)

    # Extraction Team JSON management
    state = await group_chat.save_state()
    with open("CourseProposal/json_output/group_chat_state.json", "w") as f:
        json.dump(state, f)
    aggregator_data = extract_final_aggregator_json("CourseProposal/json_output/group_chat_state.json")
    with open("CourseProposal/json_output/ensemble_output.json", "w", encoding="utf-8") as out:
        json.dump(aggregator_data, out, indent=2)
    
    # JSON key validation for ensemble_output to ensure that key names are constant
    rename_keys_in_json_file("CourseProposal/json_output/ensemble_output.json")

    update_knowledge_ability_mapping('CourseProposal/json_output/output_TSC.json', 'CourseProposal/json_output/ensemble_output.json')

    validate_knowledge_and_ability()

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
    with open("CourseProposal/json_output/research_output.json", "w", encoding="utf-8") as out:
        json.dump(editor_data, out, indent=2)

    with open("CourseProposal/json_output/ensemble_output.json", 'r', encoding='utf-8') as file:
        ensemble_output = json.load(file)      
    # Justification Agent Process
    justification_agent = run_assessment_justification_agent(ensemble_output, model_choice=model_choice)
    stream = justification_agent.run_stream(task=justification_task(ensemble_output))
    await Console(stream)

    justification_state = await justification_agent.save_state()
    with open("CourseProposal/json_output/assessment_justification_agent_state.json", "w") as f:
        json.dump(justification_state, f)
    justification_data = extract_final_agent_json("CourseProposal/json_output/assessment_justification_agent_state.json")  
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
    with open("CourseProposal/json_output/research_output.json", "w", encoding="utf-8") as out:
        json.dump(editor_data, out, indent=2)
    
    # Course Validation Form Process
    await create_course_validation(model_choice=model_choice)

    # uncomment when ready to insert excel processing
    # await process_excel(model_choice=model_choice)
    

# if __name__ == "__main__":
#     asyncio.run(main())
