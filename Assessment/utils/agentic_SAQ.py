from llama_index.llms.openai import OpenAI as llama_openai
from Assessment.utils.pydantic_models import FacilitatorGuideExtraction
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
import streamlit as st
import json
import re
import pprint

async def generate_saq(extracted_data, index, model_client):
    openai_api_key = st.secrets["OPENAI_API_KEY"]

    system_prompt = """
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
    ks_generation_llm = llama_openai(model="gpt-4o-mini", api_key=openai_api_key, system_prompt=system_prompt)
    ks_generation_query_engine = index.as_query_engine(
        similarity_top_k=10,
        llm=ks_generation_llm,
        # response_mode="tree_summarize"
        response_mode="compact",
        # node_postprocessors=[cohere_rerank],
    )
    retrieved_content = retrieve_content_for_knowledge_statement(extracted_data, ks_generation_query_engine)

    # Autogen setup
    qa_generation_agent = AssistantAgent(
        name="question_answer_generator",
        model_client=model_client,
        system_message=f"""
        You are an expert educator in '{extracted_data.course_title}'. 
        You will create knowledge-based scenario question-answer pairs based on the retrieved content.

        ### Instructions:
        1. Generate **exactly one** question-and-answer pair per knowledge statement.
        2. **Scenario Requirements**:
        - Provide a **2–3 sentence** realistic scenario that offers context.
        - Describe an industry, organization, or setting related to the knowledge statement.
        - Include a brief goal or problem the scenario is trying to solve.
        - Write it in an **"analyze and recommend"** style, aligned with Bloom's Taxonomy Level 3 (Applying).
        - Example: 
            "An eCommerce company is considering AI applications but is unsure of the specific areas where AI could make the most impact. Analyze and recommend areas within the eCommerce industry where AI is most applicable."
        3. **Question Requirements**:
        - Phrase the question so it aligns with the scenario and Bloom's Taxonomy Level 3 (Applying).
        - Example:
            "Which AI applications can be implemented for maximum impact, and how should they be prioritized?"
        4. **Answer Requirements**:
        - Short Answer Question (SAQ) style.
        - Provide 3–4 concise bullet points **only** (no extra commentary).
        - Each bullet should be a key knowledge point or practical insight.
        5. **If no relevant content** is found for a given knowledge statement:
        - "scenario": "No relevant scenario found."
        - "question_statement": "No relevant content found for this knowledge statement."
        - "answer": ["No relevant content found."]
        6. Structure the final output in **valid JSON** with the format:

        ```json
        {{
            "course_title": "<course_title_here>",
            "duration": "<assessment_duration>",
            "questions": [
                {{
                    "scenario": "<scenario>",
                    "question_statement": "<question>",
                    "knowledge_id": "<knowledge_id>",
                    "answer": [
                        "<bullet_point_1>",
                        "<bullet_point_2>",
                        "<bullet_point_3>"
                    ]
                }},
                ...
            ]
        }}
        ```
        
        7. Return the JSON between triple backticks followed by 'TERMINATE'.
        """,
    )
    assessment_duration = ""
    for assessment in extracted_data.assessments:
        if "SAQ" in assessment.code:
            assessment_duration = assessment.duration

    agent_task=f"""
        Please generate the questions and answers using the following course title: '{extracted_data.course_title}', 
        assessment duration: '{assessment_duration}', and topic contents: {retrieved_content}.
        Ensure suggestive answers are provided as bullet points, concise and practical, covering key aspects of the knowledge statement.
        Phrase questions in alignment with Bloom's Taxonomy Level: {extracted_data.tsc_proficiency_level}.
        If any part of an answer cannot be found in the retrieved content, explicitly state that 'The retrieved content does not include that (information).'
        Bloom's Taxonomy Levels:
            Level 1: Remembering
            Level 2: Understanding
            Level 3: Applying
            Level 4: Analyzing
            Level 5: Evaluating
            Level 6: Creating
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
                    f"Retrieve the most relevant inline segments aligned to Knowledge Statement: {knowledge_statement}\n"
                    f"From the given Topic: {topic_name}"        
                )
                # pprint_response(response, show_source=True)

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