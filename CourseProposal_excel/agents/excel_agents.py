from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
import json
import asyncio
import os
from dotenv import load_dotenv
from CourseProposal.model_configs import get_model_config

def overview_task():
    overview_task = f"""
    1. Based on the provided data, generate your justifications.
    2. Ensure your responses are structured in JSON format.
    3. Return a full JSON object with all your answers according to the schema.
    """
    return overview_task

def create_course_agent(research_output, model_choice: str) -> RoundRobinGroupChat:

    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)

    # insert research analysts
    about_course_message = f"""
    As a training consultant focusing on analyzing performance gaps and training needs based on course learning outcomes,
    your task is to assess the targeted sector(s) background and needs for the training. Your analysis should be structured
    clearly and based on the provided course title and industry.
    Do not use any control characters such as newlines.
    Do not mention the course name in your answer.
    Do not use more than 300 words, it should be a concise summary of the course and what it has to offer.

    Provide learners with a clear overview of the course:
    Highlight the benefits your course offers including skils, competencies and needs that the course will address
    Explain how the course is relevant to the industry and how it may impact the learner's career in terms of employment/ job upgrading opportunities
    Indicate that the course is for beginner learners.

    Achieve an answer for the following points based on the already synthesized data in {research_output}:

    Format your response in the given JSON structure under "course_overview".
    "course_overview": {{

        }}
    """

    course_agent = AssistantAgent(
        name="course_agent",
        model_client=model_client,
        system_message=about_course_message,
    )

    course_agent_chat = RoundRobinGroupChat([course_agent], max_turns=1)

    return course_agent_chat

def create_ka_analysis_agent(instructional_methods_data, model_choice: str) -> RoundRobinGroupChat:

    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)

    # instructional_methods_data = create_instructional_dataframe()
    ka_analysis_message = f"""
    You are responsible for elaborating on the appropriateness of the assessment methods in relation to the K and A statements. For each LO-MoA (Learning Outcome - Method of Assessment) pair, input rationale for each on why this MoA was chosen, and specify which K&As it
    pair, input rationale for each on why this MoA was chosen, and specify which K&As it will assess.

    The data provided which contains the ensemble of K and A statements, and the Learning Outcomes and Methods of Assessment, is in this dataframe: {instructional_methods_data}
    For each explanation, you are to provide no more than 50 words.
    Your response should be structured in the given JSON format under "KA_Analysis".
    KA_Analysis: {{
    K1: [explanation],
    A1: [explanation],
    K2: [explanation],
    A2: [explanation],
    }}

    """

    ka_analysis_agent = AssistantAgent(
        name="ka_analysis_agent",
        model_client=model_client,
        system_message=ka_analysis_message,
    )

    ka_analysis_chat = RoundRobinGroupChat([ka_analysis_agent], max_turns=1)

    return ka_analysis_chat

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

