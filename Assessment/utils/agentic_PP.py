import os
import re
import json
import pprint
import streamlit as st
from Assessment.utils.pydantic_models import FacilitatorGuideExtraction
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from llama_index.llms.openai import OpenAI as llama_openai

async def generate_pp(extracted_data, index, model_client):
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    system_prompt = """
    You are an instructional design assistant tasked with generating concise, realistic, and practical scenario-based question-answer pairs for educational purposes.

    Your role:
    1. **Generate a real-world scenario** for the given Course Title and Learning Outcome (LO). The scenario must:
    - Be concise while clearly describing the organizational challenges or context.
    - Align directly with the Learning Outcome and be applicable to the associated abilities.
    - Highlight specific organizational data, challenges, and objectives to ensure relevance and practicality.

    2. Use only the information relevant to the specified Learning Unit, Learning Outcome, and its abilities. Do not include information from unrelated topics.

    3. Ensure that:
    - Each scenario and question-answer pair is realistic, aligned to Bloom's Taxonomy level for the LO, and practically applicable.
    - If no relevant content exists, create a general scenario that remains educationally valuable and tied to the broader course theme.

    4. **Output Format:**
    - The practical performance scenario have to be at least 500 words long.
    - You will output your response in the following format. For example:
    TechFusion, a leading software solutions provider, has been approached by a global bank to develop a new mobile banking application. The bank wants to offer its customers a seamless, secure, and intuitive banking experience on their smartphones. Given the competitive landscape, the bank emphasizes the need for rapid delivery without compromising on quality. TechFusion has recently adopted Agile methodologies with Scrum and DevOps practices and sees this project as an opportunity to showcase its capabilities in these areas.

    **Restrictions:**
    - Do not include content from other topics or unrelated slides.
    - Do not invent abilities or knowledge outside the scope of the LO and its associated abilities.
    """

    scenario_llm = llama_openai(model="gpt-4o-mini", api_key=openai_api_key, system_prompt=system_prompt)

    scenario_query_engine = index.as_query_engine(
        similarity_top_k=10,
        llm=scenario_llm,
        response_mode="compact",
    )
    # Generate the shared scenario
    scenario = generate_pp_scenario(extracted_data, scenario_query_engine)

    system_prompt = """
    You are a content retrieval assistant. Your role is to retrieve topic content that aligns strictly with the specified Learning Outcome (LO) and its associated abilities.

    Your role:
    1. Restrict your retrieval strictly to the specified topic provided in the query.
    2. Retrieve content from the topic that directly aligns with the provided Learning Outcome (LO) and its abilities.
    3. If no specific content directly aligns with the Learning Outcome or abilities, provide a general summary of the topic instead.
    4. Include any example/usecase code or equations relevant to the topic or subtopics.
    5. Prioritize retrieving content that are practical.
    6. Identify and extract the exact inline segments from the provided documents that directly correspond to the content used to generate the summary. The extracted segments must be verbatim snippets from the documents, ensuring a word-for-word match with the text in the provided documents.

    Ensure that:
    - (Important) Each retrieved segment is an exact match to a part of the document and is fully contained within the document text.
    - The relevance of each segment to the Learning Outcome or abilities is clear and directly supports the summary provided.
    - (Important) If you didn't use the specific document or topic, do not mention it.
    - If no relevant information is found for the Learning Outcome, clearly state this and provide a general topic summary instead.

    Restrictions:
    - Do not include content from other topics or slides outside the specified topic.
    - Each retrieved segment must explicitly belong to the given topic.
    - Avoid including assumptions or content outside the scope of the Learning Outcome and abilities.

    You must always provide:
    1. The retrieved content aligned with the Learning Outcome and abilities.
    2. A list of verbatim extracted segments that directly support the retrieved content, each labeled with the topic and document it belongs to.
    """

    lo_retriever_llm = llama_openai(model="gpt-4o-mini", api_key=openai_api_key, system_prompt=system_prompt)
    qa_generation_query_engine = index.as_query_engine(
        similarity_top_k=10,
        llm=lo_retriever_llm,
        response_mode="tree_summarize",
    )
    retrieved_content = retrieve_content_for_learning_outcomes(extracted_data, qa_generation_query_engine)
    
    # Autogen setup
    qa_generation_agent = AssistantAgent(
        name="question_answer_generator",
        model_client=model_client,
        system_message=f"""
        You are an expert educator in '{extracted_data.course_title}'. You will create scenario-based practical performance assessment (PPA) question-answer pairs based on course data.
        The data will include:
        - A scenario
        - Retrieved content aligned with learning outcomes and abilities

        ### Instructions:
        1. Use the provided scenario and retrieved content to generate **one practical question-answer pair per learning outcome.**

        2. **Question Requirements:**
        - Each question must describe a hands-on task or practical activity related to the scenario.
        - Ensure the task can be performed based on the scenario's context without assuming learners have additional information.
        - For coding courses, specify programming tasks with clear starting points. For non-coding courses, describe actions such as planning, decision-making, evaluating data, or implementing processes.
        - Ensure the question ends with "Take snapshots of your commands at each step and paste them below."

        3. **Answer Requirements:**
        - **Provide the exact solutions** (e.g., final code, commands, outputs, or tangible deliverables) rather than describing how to capture the snapshots.
        - If there is relevant text or direct quotes from the retrieved content, include them verbatim with proper citations, for example, "(Source: [retrieved_content_reference])".
        - Each answer should contain only the final (correct) output or solution. Avoid step-by-step instructions on capturing or documenting the process.
        - If any part of an answer cannot be found in the retrieved content, explicitly state that 'The retrieved content does not include that (information).'

        4. Structure the final output in valid JSON with the following format:
        
        ```json
        {{
            "course_title": "<course_title_here>",
            "duration": "<assessment_duration_here>",
            "scenario": "<scenario_here>",
            "questions": [
                {{
                    "question_statement": "<question_text>",
                    "answer": ["<list_of exact final solutions or outputs>"],
                    "ability_id": ["<list_of_ability_ids>"]
                }},
                ...
            ]
        }}
        ```
        5. Ensure the generated practical tasks align strictly with the retrieved content and abilities. If there is relevant text or direct quotes from the retrieved content, include them verbatim. Use a format like “(Source: [retrieved_content_reference])” where needed.
        6. Return the JSON between triple backticks followed by 'TERMINATE'.
        """
    )
    assessment_duration = ""
    for assessment in extracted_data.assessments:
        if "PP" in assessment.code:
            assessment_duration = assessment.duration

    agent_task= f"""
        Please generate practical performance assessment questions using the following course title: '{extracted_data.course_title}', 
        assessment duration: '{assessment_duration}', scenario: '{scenario}', and topic contents: {retrieved_content}.
        Phrase your question in alignment with Bloom's Taxonomy Level: {extracted_data.tsc_proficiency_level}.
        Example Bloom's Taxonomy Levels:
            - Level 1: Remembering
            - Level 2: Understanding
            - Level 3: Applying
            - Level 4: Analyzing
            - Level 5: Evaluating
            - Level 6: Creating
        Ensure the question ends with "Take snapshots of your commands at each step and paste them below."
        Ensure the answer begins with "The snapshot should include: " and specifies only practical steps to test hands-on skills without any writing or documenting.
        Return the question and answer as a JSON object directly.
    """

    # Process sample input
    response = await qa_generation_agent.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )
    try:
        if not response.chat_message.content:
            print("No content found in the agent's last message.")
        json_content = response.chat_message.content.strip()
        json_pattern = re.compile(r'```json\s*(\{.*?\})\s*```', re.DOTALL)
        json_match = json_pattern.search(json_content)
        if json_match:
            json_str = json_match.group(1)
            context = json.loads(json_str)
            print(f"CONTEXT JSON MAPPING: \n\n{context}")
    except json.JSONDecodeError as e:
        print(f"Error parsing context JSON: {e}")
    return context

# Generate a detailed scenario for the case study
def generate_pp_scenario(data: FacilitatorGuideExtraction, engine) -> str:
    """
    Generates a concise, realistic scenario for the practical performance.
    Args:
        course_title (str): The title of the course.
        learning_outcomes (List[str]): A list of learning outcomes.

    Returns:
        str: A concise scenario for the case study.
    """
    
    # Retrieve the course title and bloom taxonomy level
    course_title = data.course_title
    bloom_taxonomy_level = data.tsc_proficiency_level

    # Extract the learning outcomes as a list of strings
    learning_outcomes = [lu.learning_outcome for lu in data.learning_units]
    abilities = [ability.text for lu in data.learning_units for topic in lu.topics for ability in topic.tsc_abilities]
    
    outcomes_text = "\n".join([f"- {lo}" for lo in learning_outcomes])
    abilities_text = "\n".join([f"- {ability}" for ability in abilities])

    prompt = (
        f"You are tasked with designing a realistic practical performance assessment scenario for the course '{course_title}'.\n\n"
        f"The scenario should align with the following:\n\n"
        f"Learning Outcomes:\n{outcomes_text}\n\n"
        f"Abilities:\n{abilities_text}\n\n"
        f"Bloom's Taxonomy Level:\n{bloom_taxonomy_level}\n\n"
        "The scenario should describe a company or organization facing practical challenges and provide context for the learners to apply their skills.\n"
        "Ensure the scenario is concise (1 paragraph), realistic, and action-oriented, focusing on the summary of tasks learners must perform without requiring extensive deliverables."
    )
    response = engine.query(prompt)
    return response.response.strip()

def retrieve_content_for_learning_outcomes(extracted_data, engine):
    """
    Retrieves content related to the learning outcomes and abilities from the provided data.

    Args:
        extracted_data (FacilitatorGuideExtraction): The extracted data instance containing course details.

    Returns:
        List[Dict]: A list of dictionaries containing retrieved content and associated abilities.
    """
    retrieved_content = []

    for learning_unit in extracted_data.learning_units:
        learning_outcome = learning_unit.learning_outcome
        associated_abilities = []
        ability_ids = []
        for topic in learning_unit.topics:
            associated_abilities.extend(topic.tsc_abilities)
            ability_ids.extend([ability.id for ability in topic.tsc_abilities])

        # Define the content retrieval prompt
        retrieval_prompt = (
            f"Retrieve the most relevant inline segments aligned to Learning Outcome: {learning_outcome}\n"
            f"Associated Abilities:\n"
            + "\n".join([f"- [{ability.id}] {ability.text}" for ability in associated_abilities])
            + f"\nFrom the given Topics: {', '.join([topic.name for topic in learning_unit.topics])}"
        )

        response = engine.query(retrieval_prompt)
        retrieved_content.append({
            "learning_outcome": learning_outcome,
            "abilities": ability_ids,
            "retrieved_content": response.response
        })
    
    return retrieved_content