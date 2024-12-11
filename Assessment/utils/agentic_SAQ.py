from llama_index.llms.openai import OpenAI
from Assessment.utils.pydantic_models import FacilitatorGuideExtraction
from autogen import AssistantAgent, UserProxyAgent
from autogen.cache import Cache
from typing import List
import json
import re

def generate_saq(extracted_data, index, llm_config):
    openai_api_key = llm_config["config_list"][0]["api_key"]
    system_prompt = """\
    You are a content retrieval assistant. Your role is to retrieve topic content that aligns strictly with the specified Knowledge Statement.

    Your role:
    1. Restrict your retrieval strictly to the specified topic provided in the query.
    2. Retrieve content from the topic that directly aligns with the provided Knowledge Statement.
    3. If no specific content directly aligns with the Knowledge Statement, provide a general summary of the specified topic instead.
    4. Include any example/usecase code or equations relevant to the topic or subtopics.
    5. Prioritize retrieving content that are theoretical.
    6. Identify and extract the exact inline segments from the provided documents that directly correspond to the content used to generate the given answer. The extracted segments must be verbatim snippets from the documents, ensuring a word-for-word match with the text in the provided documents.

    Ensure that:
    - (Important) Each retrieved segment is an exact match to a part of the document and is fully contained within the document text.
    - The relevance of each segment to the Knowledge Statement is clear and directly supports the summary provided.
    - (Important) If you didn't used the specific document or topic, do not mention it.
    - If no relevant information is found for the Knowledge Statement, clearly state this and provide a general topic summary instead.

    Restrictions:
    - Do not include content from other topics or slides outside the specified topic.
    - Each retrieved segment must explicitly belong to the given topic.
    - Avoid including assumptions or content outside the scope of the Knowledge Statement.

    You must always provide:
    1. The retrieved content aligned with the Knowledge Statement.
    2. A list of verbatim extracted segments that directly support the retrieved content, each labeled with the topic and document it belongs to.
    """

    ks_generation_llm = OpenAI(model="gpt-4o-mini", api_key=openai_api_key, system_prompt=system_prompt)
    ks_generation_query_engine = index.as_query_engine(
        similarity_top_k=10,
        llm=ks_generation_llm,
        # response_mode="tree_summarize"
        response_mode="compact",
    )
    retrieved_content = retrieve_content_for_knowledge_statement(extracted_data, ks_generation_query_engine)

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
        You are an expert educator in '{extracted_data.course_title}'. You will create knowledge-based scenario question-answer pairs based on course data.
        
        The data will include:
        - Retrieved content aligned with learning outcomes and abilities

        ### Instructions:
        1. Use the provided retrieved content to generate one knowledge-based question-and-answer pairs per knowledge statement.
        2. Each question should be aligned with the knowledge statement and provide an opportunity to demonstrate understanding of the content. 
        3. Each answer should clearly and concisely address the question while demonstrating understanding of the knowledge statement.
        4. Ensure all keys and values are double-quoted in the JSON output.
        5. Return the output in JSON format with the following structure:
            import
            ```json
            {{
                "course_title": "<course_title_here>",
                "duration": "<assessment_duration>",
                "questions": [
                {{
                    "scenario": "<scenario_here>",
                    "question_statement": "<question_text>",
                    "knowledge_id": "<knowledge_id>",
                    "answer": "<answer_text>"
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
            Please generate the questions and answer using the following course title:'{extracted_data.course_title}', assessment_duration:'{assessment_duration}', and topic contents:{retrieved_content}
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

# Retrieve contents for the short answer questions
def retrieve_content_for_knowledge_statement(extracted_data: FacilitatorGuideExtraction, engine):
    """
    Retrieves content related to the knowledge statements from the provided data.

    Args:
        extracted_data (FacilitatorGuideExtraction): The extracted data instance containing course details.

    Returns:
        List[Dict]: A list of dictionaries containing retrieved content and associated abilities.
    """
    retrieved_content = []
    for learning_unit in extracted_data.learning_units:
        for topic in learning_unit.topics:
            for knowledge in topic.tsc_knowledges:
                knowledge_id = knowledge.id
                knowledge_statement = knowledge.text
                topic_name = topic.name
                # Query the index to retrieve topic content for this Knowledge Statement
                response = engine.query(
                    + f"Retrieve the most relevant inline segments aligned to Knowledge Statement: {knowledge_statement}\n"
                    + f"From the given Topic: {topic_name}"        
                )
                # Add the structured data using Pydantic model
                try:
                    retrieved_content.append({
                        "knowledge_id": knowledge_id,
                        "knowledge_statement": knowledge_statement,
                        "retrieved_content": response.response
                    })
                except Exception as e:
                    print(f"Error adding structured data for {knowledge_id}: {e}")
    return retrieved_content
