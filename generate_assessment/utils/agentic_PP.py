"""
File: agentic_PP.py

===============================================================================
Agentic Practical Performance Generation Module
===============================================================================
Description:
    This module generates practical performance assessments for a course by creating a concise,
    realistic, and action-oriented scenario along with corresponding question-answer pairs for
    each learning outcome. The module leverages asynchronous operations to:
      - Clean markdown formatting from text.
      - Extract learning outcome identifiers from provided strings.
      - Retrieve relevant course content based on topics associated with each learning outcome.
      - Generate a practical performance scenario that provides real-world context for hands-on assessments.
      - Create task-based question-answer pairs for each learning outcome using an AI assistant agent.

    The final output is structured in JSON format, ensuring that each question-answer pair is linked to
    its respective learning outcome and abilities. This facilitates the creation of comprehensive practical
    performance assessments that simulate real-world challenges.

Main Functionalities:
    • clean_markdown(text: str):
          Removes markdown formatting (e.g., bold, underline, inline code) from input text.
    • extract_learning_outcome_id(lo_text: str):
          Extracts the learning outcome identifier (e.g., "LO4") from a learning outcome string.
    • retrieve_content_for_learning_outcomes(extracted_data, engine):
          Retrieves relevant course content for each learning outcome based on its topics.
    • generate_pp_scenario(data, model_client):
          Generates a concise and realistic practical performance scenario based on course details.
    • generate_pp_for_lo(qa_generation_agent, course_title, assessment_duration, scenario, 
          learning_outcome, learning_outcome_id, retrieved_content, ability_ids, ability_texts):
          Generates a hands-on, task-based question-answer pair for a specific learning outcome.
    • generate_pp(extracted_data, index, model_client):
          Orchestrates the full practical performance assessment generation process by creating a scenario,
          retrieving content, and generating question-answer pairs for each learning outcome.

Dependencies:
    - Standard Libraries: re, asyncio
    - Streamlit: For accessing st.secrets and logging.
    - Autogen Libraries:
         • autogen_agentchat.agents (AssistantAgent)
         • autogen_core (CancellationToken)
         • autogen_agentchat.messages (TextMessage)
    - Llama Index: For integrating OpenAI via llama_index.llms.openai (alias: llama_openai)
    - Utilities: parse_json_content from utils.helper

Usage:
    - Prepare an extracted_data object containing course details, learning units, topics, and abilities.
    - Provide a knowledge retrieval index (index) and a language model client (model_client) for text generation.
    - Call the generate_pp() function with the appropriate parameters to generate a
      structured practical performance assessment.
    - The output is a dictionary with the course title, assessment duration, generated scenario, and a list of question-answer
      pairs in JSON format.

Author:
    Derrick Lim
Date:
    3 March 2025
===============================================================================
"""

import re
import asyncio
import streamlit as st
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from llama_index.llms.openai import OpenAI as llama_openai
from common.common import parse_json_content

def clean_markdown(text: str) -> str:
    """
    Removes markdown formatting, such as bold (**text**) and other special characters.

    Args:
        text (str): The input string with markdown formatting.

    Returns:
        str: The cleaned text without markdown symbols.
    """
    if not text:
        return text
    cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold (**text**)
    cleaned_text = re.sub(r'__([^_]+)__', r'\1', cleaned_text)  # Remove underlined text
    cleaned_text = re.sub(r'[*_`]', '', cleaned_text)  # Remove *, _, ` (italic, inline code)
    return cleaned_text.strip()

def extract_learning_outcome_id(lo_text: str) -> str:
    """
    Extracts the learning outcome ID (e.g., 'LO4') from a given learning outcome string.

    Supports formats such as:
    - 'LO4: Description'
    - 'LO4 - Description'

    Args:
        lo_text (str): The full learning outcome text.

    Returns:
        str: The extracted learning outcome ID (e.g., 'LO4') or an empty string if not found.
    """
    pattern = r"^(LO\d+)(?:[:\s-]+)"
    match = re.match(pattern, lo_text, re.IGNORECASE)
    return match.group(1) if match else ""

async def retrieve_content_for_learning_outcomes(extracted_data, engine):
    """
    Retrieves relevant course content for each learning outcome based on its topics.

    Queries a content retrieval engine to extract relevant material associated with 
    each learning unit's topics.

    Args:
        extracted_data (dict): The extracted course data with learning units and topics.
        engine: Query engine instance for retrieving content.

    Returns:
        list: A list of dictionaries, each containing:
            - "learning_outcome" (str): The learning outcome text.
            - "learning_outcome_id" (str): The extracted learning outcome ID.
            - "abilities" (list): List of ability IDs linked to the learning outcome.
            - "ability_texts" (list): List of ability descriptions.
            - "retrieved_content" (str): The retrieved course content.
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
            # Include page metadata for better context (Option 3: Premium mode enhancement)
            content = "\n\n".join([
                f"### Page {node.metadata.get('page', 'Unknown')}\n{node.text}"
                for node in response.source_nodes
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

async def group_similar_abilities(extracted_data, model_client, min_questions=3):
    """
    Creates one question per unique ability (no grouping).

    Args:
        extracted_data (dict): Extracted facilitator guide data
        model_client: The model client (not used but kept for compatibility)
        min_questions (int): Not used (kept for compatibility)

    Returns:
        list: List of abilities, each is a dict with:
            - "learning_outcome": learning outcome text
            - "learning_outcome_id": LO ID
            - "abilities": list with single ability ID
            - "ability_texts": list with single ability text
            - "topics": list of related topics
    """
    # Extract all abilities and deduplicate by ID
    unique_abilities = {}

    print(f"DEBUG PP: Extracting abilities from {len(extracted_data.get('learning_units', []))} learning units")

    for lu in extracted_data["learning_units"]:
        lo = lu.get("learning_outcome", "")
        if not lo:
            print(f"⚠️ WARNING: Learning unit missing learning_outcome field, skipping LU")
            continue
        lo_id = extract_learning_outcome_id(lo)
        lu_title = lu.get("learning_unit_title", "Unknown LU")
        print(f"DEBUG PP: Processing LU: {lu_title}")

        for topic in lu["topics"]:
            topic_name = topic.get("name", "Unknown Topic")
            abilities_in_topic = topic.get("tsc_abilities", [])
            print(f"  Topic: {topic_name} - {len(abilities_in_topic)} abilities")

            for ability in abilities_in_topic:
                ability_id = ability["id"]
                print(f"    Found ability: {ability_id} - {ability['text'][:50]}...")

                # If ability already exists, just add the topic
                if ability_id in unique_abilities:
                    if topic["name"] not in unique_abilities[ability_id]["topics"]:
                        unique_abilities[ability_id]["topics"].append(topic["name"])
                        print(f"    -> Added topic to existing ability {ability_id}")
                else:
                    # New ability - create entry
                    unique_abilities[ability_id] = {
                        "id": ability_id,
                        "text": ability["text"],
                        "learning_outcome": lo,
                        "learning_outcome_id": lo_id,
                        "topics": [topic["name"]]
                    }
                    print(f"    -> Created new ability entry: {ability_id}")

    print(f"DEBUG PP: Total unique abilities extracted: {len(unique_abilities)}")
    print(f"DEBUG PP: Ability IDs: {list(unique_abilities.keys())}")

    # Create one question per unique ability (no grouping)
    result = []
    for ability_id, ability_data in unique_abilities.items():
        result.append({
            "learning_outcome": ability_data["learning_outcome"],
            "learning_outcome_id": ability_data["learning_outcome_id"],
            "abilities": [ability_id],  # Single ability per question
            "ability_texts": [ability_data["text"]],
            "topics": ability_data["topics"]
        })

    print(f"DEBUG PP: Returning {len(result)} question groups")
    return result


async def generate_pp_scenario(data, model_client) -> str:
    """
    Generates a practical performance assessment scenario based on course details.

    The scenario provides a real-world context for a hands-on assessment aligned 
    with the learning outcomes and abilities.

    Args:
        data (dict): The extracted course data.
        model_client: The model client used for text generation.

    Returns:
        str: A generated practical performance scenario.
    """
    course_title = data["course_title"]

    learning_outcomes = [lu["learning_outcome"] for lu in data["learning_units"]]
    abilities = [ability["text"] for lu in data["learning_units"] for topic in lu["topics"] for ability in topic["tsc_abilities"]]
    
    outcomes_text = "\n".join([f"- {lo}" for lo in learning_outcomes])
    abilities_text = "\n".join([f"- {ability}" for ability in abilities])
    
    agent_task = f"""
    You are tasked with designing a realistic practical performance assessment scenario for the course '{course_title}'.
    
    The scenario should align with the following:
    
    Learning Outcomes:
    {outcomes_text}
    
    Abilities:
    {abilities_text}
    
    The scenario should describe a company or organization facing practical challenges and provide background context aligning to the Learning Outcomes and abilities.
    End the scenario by stating the learner's role in the company.
    Ensure the scenario is concise (1 paragraph), realistic, and action-oriented.
    """
    
    # Instantiate the autogen agent for scenario generation
    scenario_agent = AssistantAgent(
        name="scenario_generator",
        model_client=model_client,
        system_message="You are an expert in instructional design. Create a concise, realistic scenario based on the provided course details."
    )
    
    response = await scenario_agent.on_messages(
        [TextMessage(content=agent_task, source="user")],
        CancellationToken()
    )
    
    scenario = response.chat_message.content.strip()
    return scenario

async def generate_pp_for_lo(qa_generation_agent, course_title, assessment_duration, scenario, learning_outcome, learning_outcome_id, retrieved_content, ability_ids, ability_texts):
    """
    Generates a question-answer pair for a specific Learning Outcome.

    This function creates a hands-on, practical performance assessment question
    that requires learners to complete a task and capture snapshots of their steps.

    Args:
        qa_generation_agent: The Autogen AssistantAgent for generating questions.
        course_title (str): The course title.
        assessment_duration (str): The total duration for the practical assessment.
        scenario (str): The case study scenario used for context.
        learning_outcome (str): The learning outcome text.
        learning_outcome_id (str): The identifier for the learning outcome (e.g., 'LO1').
        retrieved_content (str): Relevant course content for this learning outcome.
        ability_ids (list): List of ability identifiers.
        ability_texts (list): List of ability statements.

    Returns:
        dict: A structured dictionary containing:
            - "learning_outcome_id" (str): The ID of the learning outcome.
            - "question_statement" (str): The practical performance question.
            - "answer" (list[str]): A list containing the expected outcome statement.
            - "ability_id" (list): The ability IDs linked to this question.
    """
    agent_task = f"""
        Generate one practical performance assessment question-answer pair using the following details:
        - Course Title: '{course_title}'
        - Assessment Duration: '{assessment_duration}'
        - Scenario: '{scenario}'
        - Learning Outcome: '{learning_outcome}'
        - Learning Outcome ID: '{learning_outcome_id}'
        - REQUIRED Ability IDs: {ability_ids}
        - Ability Statements: {', '.join(ability_texts)}
        - Retrieved Content: {retrieved_content}

        Instructions:
        1. Formulate a direct, hands-on task question in 2 sentences maximum without any prefatory phrases.
        2. The question must end with "Take snapshots of your commands at each step and paste them below."
        4. The answer must start with "The snapshot should include: " followed solely by the final output or solution; do not include any written explanation or narrative.
        5. Include the learning outcome id in your response as "learning_outcome_id".
        6. CRITICAL: You MUST use EXACTLY these ability IDs in your response: {ability_ids}
           Do NOT modify, add, or remove any ability IDs. Return them exactly as provided.
        7. Return your output in valid JSON.
    """

    response = await qa_generation_agent.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )

    if not response or not response.chat_message:
        return None

    qa_result = parse_json_content(response.chat_message.content)

    # Validate the parsed result
    if qa_result is None or not isinstance(qa_result, dict):
        response_content = response.chat_message.content
        raise ValueError(
            f"Failed to parse PP response for {learning_outcome_id}. "
            f"Response length: {len(response_content)} chars. "
            f"Starts with: {response_content[:100]}... "
            f"Ends with: ...{response_content[-100:]}"
        )

    # Debug: Check if LLM returned wrong ability IDs
    llm_returned_abilities = qa_result.get("ability_id", [])
    if llm_returned_abilities != ability_ids:
        print(f"⚠️ LLM returned wrong abilities! Expected {ability_ids}, got {llm_returned_abilities}. Using expected.")

    return {
        "learning_outcome_id": qa_result.get("learning_outcome_id", learning_outcome_id),
        "question_statement": qa_result.get("question_statement", "Question not provided."),
        "answer": qa_result.get("answer", ["Answer not available."]),
        "ability_id": ability_ids  # ALWAYS use the exact ability_ids we passed in, ignore LLM output
    }

async def generate_pp(extracted_data, index, model_client):
    """
    Generates a full practical performance assessment, including a scenario and multiple questions.

    This function:
    - Creates a practical performance scenario based on the course content.
    - Retrieves relevant material for each learning outcome.
    - Generates hands-on, task-based questions with required snapshots.

    Args:
        extracted_data (dict): Extracted facilitator guide data containing learning outcomes.
        index: The knowledge retrieval index used for retrieving course content.
        model_client: The language model client used for generation.

    Returns:
        dict: A structured dictionary containing:
            - "course_title" (str): The course title.
            - "duration" (str): The assessment duration.
            - "scenario" (str): The generated practical scenario.
            - "questions" (list[dict]): A list of generated questions with answers.
    """
    from settings.api_manager import load_api_keys
    api_keys = load_api_keys()
    openai_api_key = api_keys.get("OPENAI_API_KEY", "")
    extracted_data = dict(extracted_data)
    
    scenario = await generate_pp_scenario(extracted_data, model_client)

    # Create a query engine for retrieving content related to learning outcomes
    lo_retriever_llm = llama_openai(
        model="gpt-4o-mini", 
        api_key=openai_api_key, 
        system_prompt="You are a content retrieval assistant. Retrieve inline segments that align strictly with the specified topics."
    )
    # Handle case when no slide deck is provided
    if index is not None:
        qa_generation_query_engine = index.as_query_engine(
            similarity_top_k=15,  # Increased for more context
            llm=lo_retriever_llm,
            response_mode="compact",
        )
        lo_content_dict = await retrieve_content_for_learning_outcomes(extracted_data, qa_generation_query_engine)
    else:
        # Use empty content when no slide deck available
        lo_content_dict = {lo["Learning_Outcome"]: "" for lo in extracted_data.get("Learning_Outcomes", [])}

    # Autogen setup for generating question-answer pairs per Learning Outcome
    qa_generation_agent = AssistantAgent(
        name="question_answer_generator",
        model_client=model_client,
        system_message=f"""
        You are an expert at creating simple, practical performance tasks.

        Guidelines:
        1. Keep tasks SIMPLE and PRACTICAL - focus on one clear action
        2. Write the task in 1-2 simple sentences
        3. MUST end with: "Take snapshots of your commands at each step and paste them below."
        4. Answer MUST start with: "The snapshot should include: " followed by the expected output
        5. Keep the expected output short and clear

        Output format (valid JSON):
        ```json
        {{
            "learning_outcome_id": "<learning_outcome_id>",
            "question_statement": "<simple task>. Take snapshots of your commands at each step and paste them below.",
            "answer": ["The snapshot should include: <expected output>"],
            "ability_id": ["<list_of_ability_ids>"]
        }}
        ```

        Return the JSON between triple backticks followed by 'TERMINATE'.
        """
    )
    
    assessment_duration = ""
    for assessment in extracted_data["assessments"]:
        if "PP" in assessment["code"]:
            assessment_duration = assessment["duration"]
            break

    # Create one question per unique ability (no grouping)
    grouped_abilities = await group_similar_abilities(extracted_data, model_client)

    # Create async tasks for generating a Q&A pair for each ability group
    tasks = []
    for group in grouped_abilities:
        # Get combined retrieved content for all topics in this group
        combined_content = []
        for item in lo_content_dict:
            # Check if any topic from this group is in the learning outcome's topics
            if any(topic in item.get("retrieved_content", "") for topic in group["topics"]):
                combined_content.append(item["retrieved_content"])

        # If no specific content found, use all content
        if not combined_content:
            combined_content = [item["retrieved_content"] for item in lo_content_dict]

        retrieved_content = "\n\n".join(combined_content)

        tasks.append(generate_pp_for_lo(
            qa_generation_agent,
            extracted_data["course_title"],
            assessment_duration,
            scenario,
            group["learning_outcome"],
            group["learning_outcome_id"],
            retrieved_content,
            group["abilities"],
            group["ability_texts"]
        ))

    print(f"DEBUG PP: Generating {len(tasks)} questions...")
    results = await asyncio.gather(*tasks)
    questions = [q for q in results if q is not None]

    print(f"DEBUG PP: Successfully generated {len(questions)} questions")
    print(f"DEBUG PP: Failed questions: {len(results) - len(questions)}")

    # Return the final structured output
    return {
        "course_title": extracted_data["course_title"],
        "duration": assessment_duration,
        "scenario": scenario,
        "questions": questions
    }
