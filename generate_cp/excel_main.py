from generate_cp.utils.excel_replace_xml import process_excel_update, preserve_excel_metadata, cleanup_old_files
from generate_cp.utils.excel_conversion_pipeline import map_new_key_names_excel, create_instructional_dataframe
from generate_cp.agents.excel_agents import (
    course_task,
    ka_task,
    create_course_agent,
    create_ka_analysis_agent,
    create_instructional_methods_agent,
    im_task
)
import json
import asyncio
import os
from autogen_agentchat.ui import Console
from generate_cp.utils.helpers import extract_final_agent_json, extract_agent_json
from generate_cp.utils.helpers import load_json_file

def combine_json_files(file1_path, file2_path):
    """
    Combines the data from two JSON files into a list of dictionaries.

    Args:
        file1_path (str): The path to the first JSON file (course_agent_data.json).
        file2_path (str): The path to the second JSON file (ka_agent_data.json).

    Returns:
        list: A list containing two dictionaries, one for course_overview and one for KA_Analysis.
    """
    with open(file1_path, 'r', encoding='utf-8') as f1:
        data1 = json.load(f1)
    with open(file2_path, 'r', encoding='utf-8') as f2:
        data2 = json.load(f2)

    combined_data = [
        data1,
        data2
    ]
    return combined_data

async def process_excel(model_choice: str) -> None:

    json_data_path = "generate_cp/json_output/generated_mapping.json" 
    excel_template_path = "generate_cp/templates/CP_excel_template.xlsx"
    output_excel_path_modified = "generate_cp/output_docs/CP_template_updated_cells_output.xlsx" # Intermediate output after cell update
    output_excel_path_preserved = "generate_cp/output_docs/CP_template_metadata_preserved.xlsx" # Final output with metadata preserved
    ensemble_output_path = "generate_cp/json_output/ensemble_output.json"
    # insert excel agents function here
    # Load the existing research_output.json
    with open('generate_cp/json_output/research_output.json', 'r', encoding='utf-8') as f:
        research_output = json.load(f)
    with open('generate_cp/json_output/ensemble_output.json', 'r', encoding='utf-8') as f:
        ensemble_output = json.load(f)

    course_agent = create_course_agent(ensemble_output, model_choice=model_choice)
    stream = course_agent.run_stream(task=course_task())
    await Console(stream)

    course_agent_state = await course_agent.save_state()
    with open("generate_cp/json_output/course_agent_state.json", "w") as f:
        json.dump(course_agent_state, f)
    course_agent_data = extract_agent_json("generate_cp/json_output/course_agent_state.json", "course_agent_validator")  
    with open("generate_cp/json_output/course_agent_data.json", "w", encoding="utf-8") as f:
        json.dump(course_agent_data, f)  

    with open('generate_cp/json_output/ensemble_output.json', 'r', encoding='utf-8') as f:
        ensemble_output = json.load(f)
    # K and A analysis pipeline
    instructional_methods_data = create_instructional_dataframe(ensemble_output)
    print(instructional_methods_data)
    ka_agent = create_ka_analysis_agent(ensemble_output, instructional_methods_data, model_choice=model_choice)
    stream = ka_agent.run_stream(task=ka_task())
    await Console(stream)
    #TSC JSON management
    state = await ka_agent.save_state()
    with open("generate_cp/json_output/ka_agent_state.json", "w") as f:
        json.dump(state, f)
    ka_agent_data = extract_agent_json("generate_cp/json_output/ka_agent_state.json", "ka_analysis_agent")
    with open("generate_cp/json_output/ka_agent_data.json", "w", encoding="utf-8") as out:
        json.dump(ka_agent_data, out, indent=2)


    # Combine the JSON files
    excel_data = combine_json_files(
        "generate_cp/json_output/course_agent_data.json",
        "generate_cp/json_output/ka_agent_data.json"
    )

    # instructional methods pipeline
    with open('generate_cp/json_output/instructional_methods.json', 'r', encoding='utf-8') as f:
        instructional_methods_descriptions = json.load(f)
    im_agent = create_instructional_methods_agent(ensemble_output, instructional_methods_descriptions, model_choice=model_choice)
    stream = im_agent.run_stream(task=im_task())
    await Console(stream)
    #TSC JSON management
    state = await im_agent.save_state()
    with open("generate_cp/json_output/im_agent_state.json", "w") as f:
        json.dump(state, f)
    ka_agent_data = extract_agent_json("generate_cp/json_output/im_agent_state.json", "instructional_methods_agent")
    with open("generate_cp/json_output/im_agent_data.json", "w", encoding="utf-8") as out:
        json.dump(ka_agent_data, out, indent=2)    

    # Write the combined data to excel_data.json
    with open("generate_cp/json_output/excel_data.json", "w", encoding="utf-8") as out:
        json.dump(excel_data, out, indent=2)

    generated_mapping_path = "generate_cp/json_output/generated_mapping.json"
    generated_mapping = load_json_file(generated_mapping_path)

    output_json_file = "generate_cp/json_output/generated_mapping.json"
    excel_data_path = "generate_cp/json_output/excel_data.json"

    map_new_key_names_excel(generated_mapping_path, generated_mapping, output_json_file, excel_data_path, ensemble_output)
    # --- CALL CLEANUP FUNCTION HERE ---
    cleanup_old_files(output_excel_path_modified, output_excel_path_preserved)

    # First, run the XML-based code to update cell values (output to _modified file)
    process_excel_update(json_data_path, excel_template_path, output_excel_path_modified, ensemble_output_path)

    # Then, preserve metadata, taking the modified file and template, and outputting the final, preserved file
    preserve_excel_metadata(excel_template_path, output_excel_path_modified, output_excel_path_preserved)

# if __name__ == "__main__":
#     model_choice = "Gemini-Flash-2.0-Exp"
#     asyncio.run(process_excel(model_choice=model_choice))