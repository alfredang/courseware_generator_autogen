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
    • retrieve_content_for_knowledge_statement_async(k_topics, index):
         Asynchronously retrieves all module content aligned with the topics for each K statement, 
         formatting the output.
    • generate_saq_for_k(qa_generation_agent, course_title, assessment_duration, k_statement, content):
         Generates a short-answer question and answer pair for a specific Knowledge Statement by crafting 
         a realistic scenario and providing concise bullet-point answers.
    • generate_saq(extracted_data, index, model_client):
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
    - Pydantic: For the FacilitatorGuideExtraction model (from generate_assessment.utils.pydantic_models)
    - Utilities: parse_json_content from utils.helper

Usage:
    - Ensure that all required API keys (e.g., OPENAI_API_KEY) are configured in st.secrets.
    - Prepare an extracted Facilitator Guide data object (of type FacilitatorGuideExtraction) that includes course
      details, learning units, topics, and knowledge statements.
    - Provide a LlamaIndex vector store index (index) and a language model client (model_client) for content retrieval
      and text generation.
    - Invoke the generate_saq() function with the appropriate parameters to obtain
      a structured dictionary containing the course title, assessment duration, and a list of generated SAQ question-answer pairs.
      
Author:
    Derrick Lim
Date:
    3 March 2025
===============================================================================
"""

import asyncio
from llama_index.llms.openai import OpenAI as llama_openai
from generate_assessment.utils.pydantic_models import FacilitatorGuideExtraction
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
import json
from common.common import parse_json_content

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

    print(f"DEBUG SAQ: Extracting K statements from {len(fg_data.get('learning_units', []))} learning units")

    for lu in fg_data["learning_units"]:
        lu_title = lu.get("learning_unit_title", "Unknown LU")
        print(f"DEBUG SAQ: Processing LU: {lu_title}")

        for topic in lu["topics"]:
            topic_name = topic.get("name", "Unknown Topic")
            k_statements = topic.get("tsc_knowledges", [])
            print(f"  Topic: {topic_name} - {len(k_statements)} K statements")

            for k in k_statements:
                k_id = f"{k['id']}: {k['text']}"
                print(f"    Found K: {k['id']} - {k['text'][:50]}...")

                if k_id not in k_to_topics:
                    k_to_topics[k_id] = []
                k_to_topics[k_id].append(topic["name"])

    print(f"DEBUG SAQ: Total unique K statements extracted: {len(k_to_topics)}")
    print(f"DEBUG SAQ: K IDs: {[k.split(':')[0] for k in k_to_topics.keys()]}")

    return k_to_topics

async def retrieve_content_for_knowledge_statement_async(k_topics, index):
    """
    Retrieves course content relevant to each Knowledge Statement (K statement) asynchronously.

    Uses LlamaIndex to fetch all available module content aligned with the topics 
    associated with each K statement.

    Args:
        k_topics (dict): A mapping of "KID: K Text" to topic names.
        index: The LlamaIndex vector store index for content retrieval.

    Returns:
        dict: A dictionary mapping K statements to their retrieved content.
    """
    # Handle case when no slide deck is provided
    if index is not None:
        query_engine = index.as_query_engine(
            similarity_top_k=15,  # Increased for more context
            verbose=True,
            response_mode="compact",
        )
    else:
        query_engine = None

    async def query_index(k_statement, topics):
        """Runs an individual query asynchronously using LlamaIndex's `aquery()`."""
        if not topics or query_engine is None:
            return k_statement, "⚠️ No slide deck content available. Assessment generated from Facilitator Guide only."

        topics_str = ", ".join(topics)
        query = f"""
        Show me all module content aligning with {topics_str} in full detail.
        Retrieve ALL available content as it appears in the source without summarizing or omitting any details.
        """
        response = await query_engine.aquery(query)  

        if not response or not response.source_nodes:
            return k_statement, "⚠️ No relevant information found."

        # Include page metadata for better context (Option 3: Premium mode enhancement)
        markdown_result = "\n\n".join([
            f"### Page {node.metadata.get('page', 'Unknown')}\n{node.text}"
            for node in response.source_nodes
        ])

        return k_statement, markdown_result  

    tasks = [query_index(k, topics) for k, topics in k_topics.items()]
    results = await asyncio.gather(*tasks)  

    return dict(results)  

async def group_similar_k_statements(k_topics, model_client):
    """
    Groups similar K statements together when there are more than 8 K statements.

    Args:
        k_topics (dict): Dictionary mapping K statements to their topics
        model_client: The model client for grouping

    Returns:
        list: List of grouped K statements, where each group is a dict with:
            - "k_statements": list of K IDs
            - "combined_text": combined text of all K statements in group
            - "topics": combined list of all topics
    """
    k_count = len(k_topics)

    # If 8 or fewer K statements, no grouping needed
    if k_count <= 8:
        return [{"k_statements": [k], "combined_text": k, "topics": topics}
                for k, topics in k_topics.items()]

    # Group similar K statements using LLM
    grouping_agent = AssistantAgent(
        name="k_grouping_agent",
        model_client=model_client,
        system_message="""
        You are an expert at analyzing and grouping similar knowledge statements.
        Given a list of knowledge statements, group similar ones together to reduce the total to around 6-8 groups.

        Guidelines:
        1. Group K statements that cover similar concepts or topics
        2. Each group should have a clear thematic connection
        3. Try to create 6-8 groups total
        4. Return the grouping as valid JSON

        Output format:
        ```json
        {
            "groups": [
                {
                    "k_ids": ["K1", "K3", "K5"],
                    "theme": "Brief description of common theme"
                },
                {
                    "k_ids": ["K2", "K4"],
                    "theme": "Brief description of common theme"
                }
            ]
        }
        ```
        Return only the JSON between triple backticks followed by 'TERMINATE'.
        """
    )

    # Prepare K statements for grouping
    k_list = list(k_topics.keys())
    k_summary = "\n".join([f"{i+1}. {k}" for i, k in enumerate(k_list)])

    task = f"""
    I have {k_count} knowledge statements. Please group similar ones together to create 6-8 groups:

    {k_summary}

    Group these K statements by similarity and return the grouping in JSON format.
    """

    response = await grouping_agent.on_messages(
        [TextMessage(content=task, source="user")], CancellationToken()
    )

    if not response or not response.chat_message:
        # Fallback: return individual K statements if grouping fails
        return [{"k_statements": [k], "combined_text": k, "topics": topics}
                for k, topics in k_topics.items()]

    try:
        grouping_result = parse_json_content(response.chat_message.content)
        groups = grouping_result.get("groups", [])

        # Build grouped K statements
        grouped_k = []
        for group in groups:
            k_ids = group.get("k_ids", [])
            # Match k_ids with actual K statements
            matched_ks = []
            combined_topics = []

            for k_statement in k_list:
                k_id = k_statement.split(":")[0].strip()
                if k_id in k_ids:
                    matched_ks.append(k_statement)
                    combined_topics.extend(k_topics[k_statement])

            if matched_ks:
                grouped_k.append({
                    "k_statements": matched_ks,
                    "combined_text": " | ".join(matched_ks),
                    "topics": list(set(combined_topics))  # Remove duplicates
                })

        return grouped_k if grouped_k else [{"k_statements": [k], "combined_text": k, "topics": topics}
                                             for k, topics in k_topics.items()]

    except Exception as e:
        # Fallback: return individual K statements if parsing fails
        return [{"k_statements": [k], "combined_text": k, "topics": topics}
                for k, topics in k_topics.items()]


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

    # Validate the parsed result
    if qa_result is None or not isinstance(qa_result, dict):
        response_content = response.chat_message.content
        raise ValueError(
            f"Failed to parse SAQ response for {k_statement}. "
            f"Response length: {len(response_content)} chars. "
            f"Starts with: {response_content[:100]}... "
            f"Ends with: ...{response_content[-100:]}"
        )

    # Directly extract keys from the parsed JSON object:
    return {
        "scenario": qa_result.get("scenario", "Scenario not provided."),
        "question_statement": qa_result.get("question_statement", "Question not provided."),
        "knowledge_id": k_statement.split(":")[0],
        "answer": qa_result.get("answer", ["Answer not available."])
    }

async def generate_saq(extracted_data: FacilitatorGuideExtraction, index, model_client):
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

    Returns:
        dict: A structured dictionary containing:
            - "course_title" (str): The course title.
            - "duration" (str): The assessment duration.
            - "questions" (list[dict]): A list of generated SAQ questions with answers.
    """
    extracted_data = dict(extracted_data)
    k_topics = get_topics_for_all_k_statements(extracted_data)
    k_content_dict = await retrieve_content_for_knowledge_statement_async(k_topics, index)

    # print(json.dumps(k_content_dict, indent=4))  

    qa_generation_agent = AssistantAgent(
        name="question_answer_generator",
        model_client=model_client,
        system_message=f"""
        You are an expert at creating simple, clear short-answer questions.

        Guidelines:
        1. Keep questions SIMPLE and DIRECT - avoid complex scenarios
        2. Create a brief 1-2 sentence scenario that relates to the knowledge statement
        3. Ask ONE clear question that can be answered in 3-5 bullet points
        4. Answers should be short, practical bullet points (5-10 words each)
        5. Base your answer on the retrieved content, but keep it simple and easy to understand
        6. Do not mention sources or references in the scenario or question

        Output format (valid JSON):
        ```json
        {{
            "scenario": "<simple 1-2 sentence scenario>",
            "question_statement": "<simple, direct question>",
            "knowledge_id": "<knowledge_id>",
            "answer": [
                "<short bullet point 1>",
                "<short bullet point 2>",
                "<short bullet point 3>"
            ]
        }}
        ```

        Return the JSON between triple backticks followed by 'TERMINATE'.
        """,
    )

    assessment_duration = next(
        (assessment.get("duration", "") for assessment in extracted_data.get("assessments", []) if "SAQ" in assessment.get("code", "")),
        ""
    )
    # print(f"############# ASSESSMENT DURATION\n{assessment_duration}\n#############")

    # Create one question per K statement (no grouping)
    tasks = [
        generate_saq_for_k(qa_generation_agent, extracted_data["course_title"], assessment_duration, k, content)
        for k, content in k_content_dict.items()
    ]

    print(f"DEBUG SAQ: Generating {len(tasks)} questions...")
    results = await asyncio.gather(*tasks)
    questions = [q for q in results if q is not None]

    print(f"DEBUG SAQ: Successfully generated {len(questions)} questions")
    print(f"DEBUG SAQ: Failed questions: {len(results) - len(questions)}")

    # Return the output with the same structure as before
    return {
        "course_title": extracted_data["course_title"],
        "duration": assessment_duration,
        "questions": questions
    }