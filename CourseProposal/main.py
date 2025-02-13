from agents.extraction_team import create_extraction_team, extraction_task
from agents.research_team import create_research_team, research_task
from agents.justification_agent import run_assessment_justification_agent, recreate_assessment_phrasing_dynamic, justification_task
from agents.course_validation_team import create_course_validation_team
from agents.tsc_agent import create_tsc_agent, tsc_task
from autogen_agentchat.ui import Console
from utils.helpers import (
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
from utils.json_mapping import map_values
from utils.jinja_docu_replace import replace_placeholders_with_docxtpl
import json
import asyncio
import sys
from cv_main import create_course_validation

async def main() -> None:
    # TSC Agent Process
    tsc_agent = create_tsc_agent()
    stream = tsc_agent.run_stream(task=tsc_task)
    await Console(stream)
    #TSC JSON management
    state = await tsc_agent.save_state()
    with open("json_output/tsc_agent_state.json", "w") as f:
        json.dump(state, f)
    tsc_data = extract_tsc_agent_json("json_output/tsc_agent_state.json")
    with open("json_output/output_TSC.json", "w", encoding="utf-8") as out:
        json.dump(tsc_data, out, indent=2)

    # Extraction Process
    group_chat = create_extraction_team()
    stream = group_chat.run_stream(task=extraction_task)
    await Console(stream)

    # Extraction Team JSON management
    state = await group_chat.save_state()
    with open("json_output/group_chat_state.json", "w") as f:
        json.dump(state, f)
    aggregator_data = extract_final_aggregator_json("json_output/group_chat_state.json")
    with open("json_output/ensemble_output.json", "w", encoding="utf-8") as out:
        json.dump(aggregator_data, out, indent=2)
    
    # JSON key validation for ensemble_output to ensure that key names are constant
    rename_keys_in_json_file("json_output/ensemble_output.json")

    update_knowledge_ability_mapping('json_output/output_TSC.json', 'json_output/ensemble_output.json')

    validate_knowledge_and_ability()

    # Research Team Process
    research_group_chat = create_research_team()
    stream = research_group_chat.run_stream(task=research_task)
    await Console(stream)

    # Research Team JSON management
    state = await research_group_chat.save_state()
    with open("json_output/research_group_chat_state.json", "w") as f:
        json.dump(state, f)
    editor_data = extract_final_editor_json("json_output/research_group_chat_state.json")
    with open("json_output/research_output.json", "w", encoding="utf-8") as out:
        json.dump(editor_data, out, indent=2)
    
    # Justification Agent Process
    justification_agent = run_assessment_justification_agent()
    stream = justification_agent.run_stream(task=justification_task)
    await Console(stream)

    justification_state = await justification_agent.save_state()
    with open("json_output/assessment_justification_agent_state.json", "w") as f:
        json.dump(justification_state, f)
    justification_data = extract_final_agent_json("json_output/assessment_justification_agent_state.json")    
    output_phrasing = recreate_assessment_phrasing_dynamic(justification_data)
    # Load the existing research_output.json
    with open('json_output/research_output.json', 'r', encoding='utf-8') as f:
        research_output = json.load(f)
    
    # Append the new output phrasing to the research_output
    if "Assessment Phrasing" not in research_output:
        research_output["Assessment Phrasing"] = []
    # Append the new result
    research_output["Assessment Phrasing"].append(output_phrasing)

    # Save the updated research_output.json
    with open('json_output/research_output.json', 'w', encoding='utf-8') as f:
        json.dump(research_output, f, indent=4)
    
    # Load CP Template with placeholders
    with open('json_output/output_CP.json', 'r') as file:
        output_CP = json.load(file)

    # Load mapping template with key:empty list pair
    with open('json_output/mapping_source.json', 'r') as file:
        mapping_source = json.load(file)

    with open('json_output/ensemble_output.json', encoding='utf-8') as f:
        ensemble_output = json.load(f)    

    updated_mapping_source = map_values(mapping_source, ensemble_output, research_output)
    try:
        with open('json_output/generated_mapping.json', 'w') as json_file:
            json.dump(updated_mapping_source, json_file, indent=4)
        print(f"Output saved to json_output/generated_mapping.json")
    except IOError as e:
        print(f"Error saving JSON to file: {e}")   

    # Load the JSON file
    with open('json_output/generated_mapping.json', 'r') as file:
        gmap = json.load(file) 
    # Flatten the JSON
    flattened_gmap = flatten_json(gmap)    
    # Save the flattened JSON back to the file
    output_filename = 'json_output/generated_mapping.json'
    try:
        with open(output_filename, 'w') as json_file:
            json.dump(flattened_gmap, json_file, indent=4)
        print(f"Output saved to {output_filename}")
    except IOError as e:
        print(f"Error saving JSON to file: {e}")

    # Parameters
    # json_file = sys.argv[1]
    # word_file = sys.argv[2]
    # new_word_file = sys.argv[3]
    json_file = "json_output/generated_mapping.json"
    word_file = "templates/CP Template_jinja.docx"
    new_word_file = "output_docs/CP_output.docx"       
    replace_placeholders_with_docxtpl(json_file, word_file, new_word_file)

    validation_group_chat = create_course_validation_team()
    stream = research_group_chat.run_stream(task=research_task)
    await Console(stream)

    # Research Team JSON management
    state = await research_group_chat.save_state()
    with open("json_output/research_group_chat_state.json", "w") as f:
        json.dump(state, f)
    editor_data = extract_final_editor_json("json_output/research_group_chat_state.json")
    with open("json_output/research_output.json", "w", encoding="utf-8") as out:
        json.dump(editor_data, out, indent=2)
    
    # Course Validation Form Process
    await create_course_validation()
    

if __name__ == "__main__":
    asyncio.run(main())
