"""
File: agentic_SAQ.py

===============================================================================
Agentic Short-Answer Question (SAQ) Generation Module
===============================================================================
Description:
    This module generates a comprehensive set of short-answer questions (SAQs) and corresponding
    answers for a course by focusing on Knowledge Statements (K statements) extracted from a Facilitator Guide.
    The module operates by:
      - Extracting topics associated with each Knowledge Statement.
      - Asynchronously retrieving relevant module content using a LlamaIndex-based query engine.
      - Generating scenario-based SAQ question-answer pairs for each Knowledge Statement via an AI assistant agent.
      
Main Functionalities:
    • get_topics_for_all_k_statements(fg_data):
         Maps each Knowledge Statement to the topics under which it appears in the Facilitator Guide.
    • retrieve_content_for_knowledge_statement_async(k_topics, index, premium_mode):
         Asynchronously retrieves all module content aligned with the topics for each K statement, 
         formatting the output based on the premium_mode flag.
    • generate_saq_for_k(qa_generation_agent, course_title, assessment_duration, k_statement, content):
         Generates a short-answer question and answer pair for a specific Knowledge Statement by crafting 
         a realistic scenario and providing concise bullet-point answers.
    • generate_saq(extracted_data, index, model_client, premium_mode):
         Coordinates the overall SAQ generation process by extracting K statement topics, retrieving content,
         and generating corresponding question-answer pairs for all knowledge statements.

Dependencies:
    - Standard Libraries: re, asyncio, json
    - Autogen Libraries:
         • autogen_agentchat.agents (AssistantAgent)
         • autogen_core (CancellationToken)
         • autogen_agentchat.messages (TextMessage)
    - Llama Index: For content retrieval (llama_index.llms.openai)
    - Streamlit: For accessing API keys via st.secrets and logging
    - Pydantic: For the FacilitatorGuideExtraction model (from Assessment.utils.pydantic_models)
    - Utilities: parse_json_content from utils.helper

Usage:
    - Ensure that all required API keys (e.g., OPENAI_API_KEY) are configured in st.secrets.
    - Prepare an extracted Facilitator Guide data object (of type FacilitatorGuideExtraction) that includes course
      details, learning units, topics, and knowledge statements.
    - Provide a LlamaIndex vector store index (index) and a language model client (model_client) for content retrieval
      and text generation.
    - Invoke the generate_saq() function with the appropriate parameters (including the premium_mode flag) to obtain
      a structured dictionary containing the course title, assessment duration, and a list of generated SAQ question-answer pairs.
      
Author:
    Derrick Lim
Date:
    3 March 2025
===============================================================================
"""

import asyncio
from llama_index.llms.openai import OpenAI as llama_openai
from Assessment.utils.pydantic_models import FacilitatorGuideExtraction
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
import json
from utils.helper import parse_json_content

def get_topics_for_all_k_statements(fg_data):
    """
    Retrieves all topics associated with each Knowledge Statement (K statement).

    This function extracts the relationships between knowledge statements (K statements)
    and the topics they appear under in the Facilitator Guide.

    Args:
        fg_data (dict): Parsed Facilitator Guide data.

    Returns:
        dict: A dictionary where:
            - Keys are "KID: K Text" (e.g., "K1: Understanding XYZ").
            - Values are lists of associated topic names.
    """
    k_to_topics = {}

    for lu in fg_data["learning_units"]:  
        for topic in lu["topics"]:  
            for k in topic["tsc_knowledges"]:  
                k_id = f"{k['id']}: {k['text']}"  
                if k_id not in k_to_topics:
                    k_to_topics[k_id] = []
                k_to_topics[k_id].append(topic["name"])

    return k_to_topics

async def retrieve_content_for_knowledge_statement_async(k_topics, index, premium_mode):
    """
    Retrieves course content relevant to each Knowledge Statement (K statement) asynchronously.

    Uses LlamaIndex to fetch all available module content aligned with the topics 
    associated with each K statement.

    Args:
        k_topics (dict): A mapping of "KID: K Text" to topic names.
        index: The LlamaIndex vector store index for content retrieval.
        premium_mode (bool): If True, formats retrieved content with additional metadata.

    Returns:
        dict: A dictionary mapping K statements to their retrieved content.
    """
    query_engine = index.as_query_engine(
        similarity_top_k=10,
        verbose=True,
        response_mode="compact",
    )

    async def query_index(k_statement, topics):
        """Runs an individual query asynchronously using LlamaIndex's `aquery()`."""
        if not topics:
            return k_statement, "⚠️ No relevant information found."

        topics_str = ", ".join(topics)
        query = f"""
        Show me all module content aligning with {topics_str} in full detail.
        Retrieve ALL available content as it appears in the source without summarizing or omitting any details.
        """
        response = await query_engine.aquery(query)  

        if not response or not response.source_nodes:
            return k_statement, "⚠️ No relevant information found."

        if premium_mode:
            markdown_result = "\n\n".join([
                f"### Page {node.metadata.get('page', 'Unknown')}\n{node.text}"
                for node in response.source_nodes
            ])
        else:
            markdown_result = "\n\n".join([
                f"### {node.text}" for node in response.source_nodes
            ])

        return k_statement, markdown_result  

    tasks = [query_index(k, topics) for k, topics in k_topics.items()]
    results = await asyncio.gather(*tasks)  

    return dict(results)  

async def generate_saq_for_k(qa_generation_agent, course_title, assessment_duration, k_statement, content):
    """
    Generates a short-answer question (SAQ) and answer pair for a given Knowledge Statement.

    The function:
    - Creates a contextual scenario relevant to the K statement.
    - Generates a clear, direct short-answer question.
    - Provides concise, practical bullet points as the expected answer.

    Args:
        qa_generation_agent: The Autogen AssistantAgent for question-answer generation.
        course_title (str): The course title.
        assessment_duration (str): Duration of the SAQ assessment.
        k_statement (str): The full K statement (e.g., "K1: Understanding XYZ").
        content (str): Retrieved module content relevant to the K statement.

    Returns:
        dict: A structured dictionary containing:
            - "scenario" (str): The generated scenario.
            - "question_statement" (str): The generated SAQ question.
            - "knowledge_id" (str): Extracted K statement ID.
            - "answer" (list[str]): A list of bullet points as the correct answer.
    """
    agent_task = f"""
        Please generate one question-answer pair using the following:
        - Course Title: '{course_title}'
        - Assessment duration: '{assessment_duration}',
        - Knowledge Statement: '{k_statement}'
        - Retrieved Content: {content}

        Instructions:
        1. Craft a realistic scenario in 2-3 sentences that provides context related to the retrieved content, but also explicitly addresses the knowledge statement.
        2. Even if the retrieved content or course title seems unrelated to the knowledge statement, creatively bridge the gap by inferring or using general knowledge. For example, if the content is about Microsoft 365 Copilot and the knowledge statement is about "Organisation's processes," generate a scenario where a department is reexamining its internal workflows using Copilot as a tool.
        3. Formulate a single, straightforward short-answer question that aligns the knowledge statement with the scenario. The question should prompt discussion on how the elements from the retrieved content could be used to address or improve the area indicated by the knowledge statement.
        4. Provide concise, practical bullet points as the answer.    
        Return the question and answer as a JSON object directly.
    """

    response = await qa_generation_agent.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )

    if not response or not response.chat_message:
        return None

    # Log the raw response for debugging
    # print(f"########### Raw Response for {k_statement}: {response.chat_message.content}\n\n###########")

    qa_result = parse_json_content(response.chat_message.content)

    # Directly extract keys from the parsed JSON object:
    return {
        "scenario": qa_result.get("scenario", "Scenario not provided."),
        "question_statement": qa_result.get("question_statement", "Question not provided."),
        "knowledge_id": k_statement.split(":")[0],
        "answer": qa_result.get("answer", ["Answer not available."])
    }

async def generate_saq(extracted_data: FacilitatorGuideExtraction, index, model_client, premium_mode):
    """
    Generates a full set of short-answer questions (SAQs) and answers for a course.

    This function:
    - Extracts all K statements from the Facilitator Guide.
    - Retrieves relevant module content for each K statement.
    - Generates an SAQ question-answer pair for each K statement.

    Args:
        extracted_data (dict): Parsed Facilitator Guide data.
        index: The LlamaIndex vector store index for content retrieval.
        model_client: The model client for question generation.
        premium_mode (bool): If True, enhances content retrieval with additional metadata.

    Returns:
        dict: A structured dictionary containing:
            - "course_title" (str): The course title.
            - "duration" (str): The assessment duration.
            - "questions" (list[dict]): A list of generated SAQ questions with answers.
    """
    extracted_data = dict(extracted_data)
    k_topics = get_topics_for_all_k_statements(extracted_data)
    k_content_dict = await retrieve_content_for_knowledge_statement_async(k_topics, index, premium_mode)

    # print(json.dumps(k_content_dict, indent=4))  

    qa_generation_agent = AssistantAgent(
        name="question_answer_generator",
        model_client=model_client,
        system_message=f"""
        You are an expert question-answer crafter with deep domain expertise. Your task is to generate a scenario-based question and answer pair for a given knowledge statement while strictly grounding your response in the provided retrieved content. You must not hallucinate or fabricate details.

        Guidelines:
        1. Base your response entirely on the retrieved content. If the content does not directly address the knowledge statement, do not invent new details. Instead, use minimal general context only to bridge gaps, but ensure that every key element of the final question and answer is explicitly supported by the retrieved content.
        2. Craft a realistic scenario in 2-3 sentences that reflects the context from the retrieved content while clearly addressing the given knowledge statement.
        3. Formulate one direct, simple question that ties the scenario to the knowledge statement. The question should be directly answerable using the retrieved content.
        4. Provide concise, practical bullet-point answers that list the key knowledge points explicitly mentioned in the retrieved content.         
        5. Ensure the overall assessment strictly follows the SAQ structure.
        6. Do not mention about the source of the content in the scenario or question.
        7. Structure the final output in **valid JSON** with the format:

        ```json
        {{
            "scenario": "<scenario>",
            "question_statement": "<question>",
            "knowledge_id": "<knowledge_id>",
            "answer": [
                "<bullet_point_1>",
                "<bullet_point_2>",
                "<bullet_point_3>"
            ]
        }}
        ```
        
        7. Return the JSON between triple backticks followed by 'TERMINATE'.
        """,
    )

    assessment_duration = next(
        (assessment.get("duration", "") for assessment in extracted_data.get("assessments", []) if "SAQ" in assessment.get("code", "")),
        ""
    )
    # print(f"############# ASSESSMENT DURATION\n{assessment_duration}\n#############")
    
    # Create async tasks for generating a Q&A pair for each knowledge statement
    tasks = [
        generate_saq_for_k(qa_generation_agent, extracted_data["course_title"], assessment_duration, k, content)
        for k, content in k_content_dict.items()
    ]
    results = await asyncio.gather(*tasks)
    questions = [q for q in results if q is not None]

    # Return the output with the same structure as before
    return {
        "course_title": extracted_data["course_title"],
        "duration": assessment_duration,
        "questions": questions
    }