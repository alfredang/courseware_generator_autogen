import os
import re
import json
from Assessment.utils.pydantic_models import CaseStudy, CaseStudyQuestion, FacilitatorGuideExtraction
from autogen import AssistantAgent, UserProxyAgent
from autogen.cache import Cache
from llama_index.llms.openai import OpenAI
from IPython.display import display, Markdown

def generate_cs(extracted_data, index, llm_config):
    openai_api_key = llm_config["config_list"][0]["api_key"]
    system_prompt = """\
    You are an instructional design assistant tasked with generating concise, realistic, and practical scenario-based question-answer pairs for educational purposes.

    Your role:
    1. **Generate a real-world scenario** for the given Course Title and Learning Outcome (LO). The scenario must:
    - Be concise (1-2 paragraphs) while clearly describing the organizational challenges or context.
    - Align directly with the Learning Outcome and be applicable to the associated abilities.
    - Highlight specific organizational data, challenges, and objectives to ensure relevance and practicality.

    2. Use only the information relevant to the specified Learning Unit, Learning Outcome, and its abilities. Do not include information from unrelated topics.

    3. Ensure that:
    - Each scenario and question-answer pair is realistic, aligned to Bloom's Taxonomy level for the LO, and practically applicable.
    - If no relevant content exists, create a general scenario that remains educationally valuable and tied to the broader course theme.

    **Output Format:**
    - Tase study scenario have to be at least 500 words long.
    - You will output your response in the following format. For example:
    TechFusion, a leading software solutions provider, has been approached by a global bank to develop a new mobile banking application. The bank wants to offer its customers a seamless, secure, and intuitive banking experience on their smartphones. Given the competitive landscape, the bank emphasizes the need for rapid delivery without compromising on quality. TechFusion has recently adopted Agile methodologies with Scrum and DevOps practices and sees this project as an opportunity to showcase its capabilities in these areas.

    **Restrictions:**
    - Do not include content from other topics or unrelated slides.
    - Do not invent abilities or knowledge outside the scope of the LO and its associated abilities.
    """

    scenario_llm = OpenAI(model="gpt-4o-mini", api_key=openai_api_key, system_prompt=system_prompt)

    scenario_query_engine = index.as_query_engine(
        similarity_top_k=10,
        llm=scenario_llm,
        response_mode="compact",
    )
    # Generate the shared scenario
    scenario = generate_case_study_scenario(extracted_data, scenario_query_engine)

    system_prompt = """\
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

    lo_retriever_llm = OpenAI(model="gpt-4o-mini", api_key=openai_api_key, system_prompt=system_prompt)
    qa_generation_query_engine = index.as_query_engine(
        similarity_top_k=10,
        llm=lo_retriever_llm,
        response_mode="compact",
    )
    retrieved_content = retrieve_content_for_learning_outcomes(extracted_data, qa_generation_query_engine)
    
    user_proxy_agent = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda msg: msg.get("content", "") and "TERMINATE" in msg["content"],
        code_execution_config={"work_dir": "output", "use_docker": False}
    )

    # Autogen setup
    qa_generation_agent = AssistantAgent(
        name="Question Answer Generator",
        system_message=f"""
        You are an expert educator in '{extracted_data.course_title}'. You will create scenario-based case study question-answer pairs based on course data.
        The data will include:
        - A scenario
        - Retrieved content aligned with learning outcomes and abilities

        ### Instructions:
        1. Use the provided scenario and retrieved content to generate one question-and-answer pairs per one learning outcome.
        2. Each question should be aligned with the learning outcome and abilities implied by the retrieved content and the Bloom's Taxonomy Level.
        3. The answer should demonstrate mastery of the abilities and address the scenario context.
        4. Ensure all keys and values are double-quoted in the JSON output.
        5. Return the output in JSON format with the following structure:
            import
            ```json
            {{
                "course_title": "<course_title_here>",
                "duration": "<assessment_duration_here>",
                "scenario": "<scenario_here>",
                "questions": [
                {{
                    "question_statement": "<question_text>",
                    "answer": "<answer_text>",
                    "ability_id": ["<list_of_ability_ids>"]
                }},
                ...
                ]
            }}
            ```
        """,
        llm_config=llm_config,
    )
    assessment_duration = ""
    for assessment in extracted_data.assessments:
        if "PP" in assessment.code:
            assessment_duration = assessment.duration

    with Cache.disk() as cache:
        chat_result = user_proxy_agent.initiate_chat(
            qa_generation_agent,
            message=f"""
            Please generate the questions and answer using the following course title:'{extracted_data.course_title}', assessment_duration:'{assessment_duration}', scenario: '{scenario}' and topic contents:{retrieved_content}
            Phrase your question in accordance with the Bloom's Taxonomy Level: {extracted_data.tsc_proficiency_level}
            Bloom's Taxonomy Level Information:
                Level 1: Remembering
                Level 2: Understanding
                Level 3: Applying
                Level 4: Analyzing
                Level 5: Evaluating
                Level 6: Creating
            Return the question and answer as a complete JSON dictionary containing the specified fields.
            RETURN 'TERMINATE' once the generation is done.
            """,
            summary_method="reflection_with_llm",
            cache=cache,
    )
    try:
        last_message_content = chat_result.chat_history[-1].get("content", "")
        if not last_message_content:
            print("No content found in the agent's last message.")
        last_message_content = last_message_content.strip()
        json_pattern = re.compile(r'```json\s*(\{.*?\})\s*```', re.DOTALL)
        json_match = json_pattern.search(last_message_content)
        if json_match:
            json_str = json_match.group(1)
            context = json.loads(json_str)
            print(f"CONTEXT JSON MAPPING: \n\n{context}")
    except json.JSONDecodeError as e:
        print(f"Error parsing context JSON: {e}")

    return context

# Generate a detailed scenario for the case study
def generate_case_study_scenario(data: FacilitatorGuideExtraction, engine) -> str:
    """
    Generates a concise, realistic scenario for the case study.
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
        f"You are tasked with designing a concise, realistic case study scenario for the course '{course_title}'.\n\n"
        f"The scenario should align with the following:\n\n"
        f"Learning Outcomes:\n{outcomes_text}\n\n"
        f"Abilities:\n{abilities_text}\n\n"
        f"Bloom's Taxonomy Level:\n{bloom_taxonomy_level}\n\n"
        "The scenario should describe a company or organization facing challenges related to communication, collaboration, or customer satisfaction. "
        "Ensure the scenario is realistic and practical, and keep it to 1-2 paragraphs without markdown elements or formatting."
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