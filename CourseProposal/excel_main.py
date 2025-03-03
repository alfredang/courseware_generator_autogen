from CourseProposal.utils.excel_replace_xml import process_excel_update, preserve_excel_metadata, cleanup_old_files
from CourseProposal.utils.excel_conversion_pipeline import map_new_key_names_excel, create_instructional_dataframe
from CourseProposal.agents.excel_agents import (
    course_task,
    ka_task,
    create_course_agent,
    create_ka_analysis_agent
)
import json
import asyncio
import os
from autogen_agentchat.ui import Console
from CourseProposal.utils.helpers import extract_final_agent_json, extract_agent_json

async def process_excel(model_choice: str) -> None:
    map_new_key_names_excel()
    # json_data_path = os.path.join('json_output', 'generated_mapping.json')
    # excel_template_path = os.path.join( 'templates', 'CP_excel_template.xlsx')
    # output_excel_path_modified = os.path.join( 'output_docs', 'CP_template_updated_cells_output.xlsx') # Intermediate output after cell update
    # output_excel_path_preserved = os.path.join( 'output_docs', 'CP_template_metadata_preserved.xlsx') # Final output with metadata preserved
    # ensemble_output_path = os.path.join( 'json_output', 'ensemble_output.json')

    json_data_path = "CourseProposal/json_output/generated_mapping.json" 
    excel_template_path = "CourseProposal/templates/CP_excel_template.xlsx"
    output_excel_path_modified = "CourseProposal/output_docs/CP_template_updated_cells_output.xlsx" # Intermediate output after cell update
    output_excel_path_preserved = "CourseProposal/output_docs/CP_template_metadata_preserved.xlsx" # Final output with metadata preserved
    ensemble_output_path = "CourseProposal/json_output/ensemble_output.json"
    # insert excel agents function here
    # Load the existing research_output.json
    with open('CourseProposal/json_output/research_output.json', 'r', encoding='utf-8') as f:
        research_output = json.load(f)

    course_agent = create_course_agent(research_output, model_choice=model_choice)
    stream = course_agent.run_stream(task=course_task())
    await Console(stream)

    course_agent_state = await course_agent.save_state()
    with open("CourseProposal/json_output/course_agent_state.json", "w") as f:
        json.dump(course_agent_state, f)
    course_agent_data = extract_agent_json("CourseProposal/json_output/course_agent_state.json", "course_agent")  
    with open("CourseProposal/json_output/excel_data.json", "w", encoding="utf-8") as f:
        json.dump(course_agent_data, f)  

    with open('CourseProposal/json_output/ensemble_output.json', 'r', encoding='utf-8') as f:
        ensemble_output = json.load(f)
    # K and A analysis pipeline
    instructional_methods_data = create_instructional_dataframe(ensemble_output)
    ka_agent = create_ka_analysis_agent(instructional_methods_data, model_choice=model_choice)
    stream = ka_agent.run_stream(task=ka_task())
    await Console(stream)
    #TSC JSON management
    state = await ka_agent.save_state()
    with open("CourseProposal/json_output/ka_agent_state.json", "w") as f:
        json.dump(state, f)
    ka_agent_data = extract_agent_json("CourseProposal/json_output/ka_agent_state.json", "ka_analysis_agent")
    with open("CourseProposal/json_output/excel_data.json", "w", encoding="utf-8") as out:
        json.dump(ka_agent_data, out, indent=2)

    # --- CALL CLEANUP FUNCTION HERE ---
    cleanup_old_files(output_excel_path_modified, output_excel_path_preserved)

    # First, run the XML-based code to update cell values (output to _modified file)
    process_excel_update(json_data_path, excel_template_path, output_excel_path_modified, ensemble_output_path)

    # Then, preserve metadata, taking the modified file and template, and outputting the final, preserved file
    preserve_excel_metadata(excel_template_path, output_excel_path_modified, output_excel_path_preserved)

# if __name__ == "__main__":
#     asyncio.run(process_excel())