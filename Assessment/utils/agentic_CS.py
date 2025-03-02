# agentic_CS.py
import os
import re
import json
import pprint
import asyncio
import streamlit as st
from Assessment.utils.pydantic_models import FacilitatorGuideExtraction
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from llama_index.llms.openai import OpenAI as llama_openai
from utils.helper import parse_json_content  # Ensure this helper is available

def extract_learning_outcome_id(lo_text: str) -> str:
    """
    Extracts the learning outcome id (e.g., 'LO4') from a learning outcome string.
    Handles formats like 'LO4: Description' or 'LO4 - Description'.
    """
    pattern = r"^(LO\d+)(?:[:\s-]+)"
    match = re.match(pattern, lo_text, re.IGNORECASE)
    return match.group(1) if match else ""

async def retrieve_content_for_learning_outcomes(extracted_data, engine, premium_mode=False):
    """
    Asynchronously retrieves all content for topics under each learning unit.
    
    For each learning unit, builds a query to extract all available content for the associated topics.
    
    Returns a list of dictionaries with keys:
      - "learning_outcome"
      - "learning_outcome_id"
      - "abilities" (list of ability IDs)
      - "ability_texts" (list of ability statements)
      - "retrieved_content"
    """
    async def query_learning_unit(learning_unit):
        learning_outcome = learning_unit["learning_outcome"]
        lo_id = extract_learning_outcome_id(learning_outcome)
        ability_ids = []
        ability_texts = []
        topics_names = []
        for topic in learning_unit["topics"]:
            ability_ids.extend([ability["id"] for ability in topic["tsc_abilities"]])
            ability_texts.extend([ability["text"] for ability in topic["tsc_abilities"]])
            topics_names.append(topic["name"])
        
        if not topics_names:
            return learning_outcome, {
                "learning_outcome": learning_outcome,
                "learning_outcome_id": lo_id,
                "abilities": ability_ids,
                "ability_texts": ability_texts,
                "retrieved_content": "⚠️ No relevant information found."
            }
        
        topics_str = ", ".join(topics_names)
        query = f"""
        Show me all module content aligning with the following topics: {topics_str}
        for the Learning Outcome: {learning_outcome}.
        Retrieve ALL available content as it appears in the source without summarizing or omitting any details.
        """
        
        response = await engine.aquery(query)
        if not response or not getattr(response, "source_nodes", None) or not response.source_nodes:
            content = "⚠️ No relevant information found."
        else:
            if premium_mode:
                content = "\n\n".join([
                    f"### Page {node.metadata.get('page', 'Unknown')}\n{node.text}"
                    for node in response.source_nodes
                ])
            else:
                content = "\n\n".join([
                    f"### {node.text}" for node in response.source_nodes
                ])
        return learning_outcome, {
            "learning_outcome": learning_outcome,
            "learning_outcome_id": lo_id,
            "abilities": ability_ids,
            "ability_texts": ability_texts,
            "retrieved_content": content
        }
    
    tasks = [query_learning_unit(lu) for lu in extracted_data["learning_units"]]
    results = await asyncio.gather(*tasks)
    return [result[1] for result in results]

async def generate_cs_scenario(data: FacilitatorGuideExtraction, model_client) -> str:

    course_title = data["course_title"]

    learning_outcomes = [lu["learning_outcome"] for lu in data["learning_units"]]
    abilities = [ability["text"] for lu in data["learning_units"] for topic in lu["topics"] for ability in topic["tsc_abilities"]]
    
    outcomes_text = "\n".join([f"- {lo}" for lo in learning_outcomes])
    abilities_text = "\n".join([f"- {ability}" for ability in abilities])
    
    agent_task = f"""
    You are an instructional design assistant tasked with generating a concise, realistic, and practical case study scenario for the course '{course_title}'.
    
    The scenario should align with the following:
    
    Learning Outcomes:
    {outcomes_text}
    
    Abilities:
    {abilities_text}
    
    The scenario must be at least 2 paragraphs long, 250 words and describe a real-world organizational challenge that aligns with the Learning Outcomes and abilities.
    Use only the relevant information from the specified Learning Units.    
    Do not include introductory labels like **"Case Study Scenario:"** at the beginning of the response.
    Do not mention any form of learning outcome id like (LO1) inside the scenario.
    Do not include unrelated content.
    """
    
    scenario_agent = AssistantAgent(
        name="scenario_generator",
        model_client=model_client,
        system_message="You are an expert instructional design assistant. Create a realistic case study scenario based on the provided course details."
    )
    
    response = await scenario_agent.on_messages(
        [TextMessage(content=agent_task, source="user")],
        CancellationToken()
    )
    
    scenario = response.chat_message.content.strip()
    return scenario

async def generate_cs_for_lo(qa_generation_agent, course_title, assessment_duration, scenario, learning_outcome, learning_outcome_id, retrieved_content, ability_ids, ability_texts):
    """
    Args:
        qa_generation_agent: The Autogen AssistantAgent for question-answer generation.
        course_title: Course title.
        assessment_duration: Duration of the assessment.
        scenario: The shared scenario for the case study assessment.
        learning_outcome: The Learning Outcome statement.
        learning_outcome_id: The identifier for the Learning Outcome (e.g., LO1).
        retrieved_content: The retrieved content associated with the learning outcome.
        ability_ids: A list of ability identifiers associated with this learning outcome.
        ability_texts: A list of ability statements associated with this learning outcome.
        
    Returns:
        Generated question-answer dictionary with keys: learning_outcome_id, question_statement, answer, ability_id.
    """

    agent_task = f"""
    Generate one scenario-based case study question-answer pair using the following details:
    - Course Title: '{course_title}'
    - Assessment Duration: '{assessment_duration}'
    - Scenario: '{scenario}'
    - Learning Outcome: '{learning_outcome}'
    - Learning Outcome ID: '{learning_outcome_id}'
    - Associated Ability IDs: {', '.join(ability_ids)}
    - Associated Ability Statements: {', '.join(ability_texts)}
    - Retrieved Content: {retrieved_content}
    
    Instructions:
    1. Use the provided scenario and retrieved content to generate one question-answer pair aligned with the Learning Outcome.
    2. The question should be directly aligned with the Learning Outcome and the associated abilities, and must be in a case study style.
    3. The answer must be a detailed case study solution that explains what to do, why it matters, and includes a short rationale for each recommended action.
    4. If any part of the answer is missing from the retrieved content, state: 'The retrieved content does not include that (information).'
    5. Include the learning outcome id in your response as "learning_outcome_id" and the ability ids as "ability_id".
    6. Return your output in valid JSON.
    """

    response = await qa_generation_agent.on_messages(
        [TextMessage(content=agent_task, source="user")],
        CancellationToken()
    )

    if not response or not response.chat_message:
        return None

    qa_result = parse_json_content(response.chat_message.content)
    
    return {
        "learning_outcome_id": qa_result.get("learning_outcome_id", learning_outcome_id),
        "question_statement": qa_result.get("question_statement", "Question not provided."),
        "answer": qa_result.get("answer", ["Answer not available."]),
        "ability_id": qa_result.get("ability_id", ability_ids)
    }

async def generate_cs(extracted_data: FacilitatorGuideExtraction, index, model_client, premium_mode):
    """
    Generate case study assessment questions and answers asynchronously for all learning outcomes.

    Returns a dictionary with keys: course_title, duration, scenario, questions.
    """
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    extracted_data = dict(extracted_data)
    
    scenario = await generate_cs_scenario(extracted_data, model_client)
    print(f"#################### SCENARIO ###################\n\n{scenario}")

    lo_retriever_llm = llama_openai(
        model="gpt-4o-mini",
        api_key=openai_api_key,
        system_prompt="You are a content retrieval assistant. Retrieve inline segments that align strictly with the specified topics."
    )
    qa_generation_query_engine = index.as_query_engine(
        similarity_top_k=10,
        llm=lo_retriever_llm,
        response_mode="compact"
    )
    lo_content_dict = await retrieve_content_for_learning_outcomes(extracted_data, qa_generation_query_engine, premium_mode)

    qa_generation_agent = AssistantAgent(
        name="question_answer_generator",
        model_client=model_client,
        system_message=f"""
        You are an expert question-answer crafter with deep domain expertise. You will create a case study question and answer pair for a given Learning Outcome and its associated abilities, strictly grounded in the provided retrieved content.

        **Guidelines:**
        1. Base your response exclusively on the retrieved content.
        2. Each question should be aligned with the learning outcome and abilities implied by the retrieved content.
        3. The answer should demonstrate mastery of the abilities and address the scenario context.
        4. The answer must be in a structured, professional **case study solution style**:
        - Clearly outline the recommended approach and steps.
        - Each step must be written in **complete sentences** without using bullet points or numbered lists.
        - Avoid unnecessary formatting like markdown (`**bold**`, `- bullets`, etc.).
        - Use paragraphs and clear transitions between ideas instead of lists.

        **Answer Style:**
        - Provide a **clear introduction** explaining the key problem and objective.
        - Present a **logical, structured response** that explains what actions should be taken, why they are necessary, and the expected impact.
        - Use **full sentences** and **proper transitions** instead of list formatting.
        - Avoid phrases like "Step 1," "Step 2," or bullet points.
        - Conclude with a **summary statement** linking the solution back to the case study's goals.
        6. Return your output in valid JSON with the following format:
        
        ```json
        {{
            "learning_outcome_id": "<learning_outcome_id>",
            "question_statement": "<question_text>",
            "answer": ["<final output or solution>"],
            "ability_id": ["<list_of_ability_ids>"]
        }}
        ```

        Return the JSON between triple backticks followed by 'TERMINATE'.
        """
    )
    
    assessment_duration = ""
    for assessment in extracted_data["assessments"]:
        if "CS" in assessment["code"]:
            assessment_duration = assessment["duration"]
            break

    tasks = []
    for item in lo_content_dict:
        learning_outcome = item["learning_outcome"]
        learning_outcome_id = item.get("learning_outcome_id", "")
        retrieved_content = item["retrieved_content"]
        ability_ids = item.get("abilities", [])
        ability_texts = item.get("ability_texts", [])
        tasks.append(generate_cs_for_lo(
            qa_generation_agent,
            extracted_data["course_title"],
            assessment_duration,
            scenario,
            learning_outcome,
            learning_outcome_id,
            retrieved_content,
            ability_ids,
            ability_texts
        ))
    
    results = await asyncio.gather(*tasks)
    questions = [q for q in results if q is not None]

    return {
        "course_title": extracted_data["course_title"],
        "duration": assessment_duration,
        "scenario": scenario,
        "questions": questions
    }
