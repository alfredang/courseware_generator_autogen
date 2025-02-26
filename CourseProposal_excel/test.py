from agents.excel_agents import create_course_agent, create_ka_analysis_agent, overview_task
import json
import asyncio



if __name__ == "__main__":
    # Load the existing research_output.json
    with open('json_output/research_output.json', 'r', encoding='utf-8') as f:
        research_output = json.load(f)

    course_agent = create_course_agent(research_output, model_choice=model_choice)
    stream = course_agent.run_stream(task=overview_task)
    await Console(stream)

    course_agent_state = await course_agent.save_state()
    with open("json_output/course_agent_state.json", "w") as f:
        json.dump(course_agent_state, f)
    course_agent_data = extract_final_agent_json("json_output/course_agent_state.json")  
    with open("json_output/excel_data.json", "w", encoding="utf-8") as f:
        json.dump(course_agent_data, f)  

    # K and A analysis pipeline
    instructional_methods_data = create_instructional_dataframe()
    ka_agent = create_ka_analysis_agent(instructional_methods_data, model_choice=model_choice)
    stream = ka_agent.run_stream(task=overview_task)
    await Console(stream)
    #TSC JSON management
    state = await ka_agent.save_state()
    with open("json_output/ka_agent_state.json", "w") as f:
        json.dump(state, f)
    ka_agent_data = extract_final_agent_json("json_output/ka_agent_state.json")
    with open("json_output/excel_data.json", "w", encoding="utf-8") as out:
        json.dump(ka_agent_data, out, indent=2)

