"""
File: agentic_CS.py

===============================================================================
Agentic Case Study Generation Module
===============================================================================
Description:
    This module is responsible for generating case study assessments for a course by
    creating a realistic case study scenario and corresponding question-answer pairs
    for each learning outcome. The module leverages asynchronous functions to:
      - Extract learning outcome identifiers from provided texts.
      - Retrieve relevant course content using a query engine based on topics and learning outcomes.
      - Generate a detailed case study scenario aligned with the course’s learning outcomes
        and associated abilities.
      - Generate scenario-based question-answer pairs for each learning outcome using an
        AI assistant agent.
      
    The output is structured in JSON format, ensuring that each case study question-answer
    pair is linked to its respective learning outcome and abilities. This facilitates the
    creation of comprehensive case study assessments that are grounded in real-world
    organizational challenges.

Main Functionalities:
    • extract_learning_outcome_id(lo_text: str):
          Extracts the learning outcome identifier (e.g., "LO4") from a learning outcome string.
    • retrieve_content_for_learning_outcomes(extracted_data, engine):
          Queries a content retrieval engine to obtain relevant course material for each learning
          outcome based on associated topics.
    • generate_cs_scenario(data: FacilitatorGuideExtraction, model_client):
          Generates a realistic case study scenario (at least 250 words) that aligns with the
          course’s learning outcomes and abilities.
    • generate_cs_for_lo(qa_generation_agent, course_title, assessment_duration, scenario, 
          learning_outcome, learning_outcome_id, retrieved_content, ability_ids, ability_texts):
          Generates a case study question-answer pair for a specific learning outcome.
    • generate_cs(extracted_data: FacilitatorGuideExtraction, index, model_client):
          Orchestrates the overall case study generation process by creating a scenario, retrieving
          content for each learning outcome, and generating corresponding question-answer pairs.

Dependencies:
    - Standard Libraries: re, asyncio
    - Streamlit: For accessing st.secrets and logging
    - Pydantic: For the FacilitatorGuideExtraction model from generate_assessment.utils.pydantic_models
    - Autogen Libraries:
         • autogen_agentchat.agents (AssistantAgent)
         • autogen_core (CancellationToken)
         • autogen_agentchat.messages (TextMessage)
    - Llama Index: For integrating OpenAI via llama_index.llms.openai (alias: llama_openai)
    - Utilities: parse_json_content from utils.helper

Usage:
    - Prepare a FacilitatorGuideExtraction data object containing course details, learning units,
      topics, and abilities.
    - Provide a query engine (index) for content retrieval and a language model client (model_client)
      for generating text.
    - Call the generate_cs() function with the appropriate parameters to generate a structured case study assessment.
    - The final output is a dictionary with the course title, assessment duration, generated scenario,
      and a list of question-answer pairs.

Author:
    Derrick Lim
Date:
    3 March 2025
===============================================================================
"""

import re
import asyncio
import streamlit as st
from generate_assessment.utils.pydantic_models import FacilitatorGuideExtraction
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from llama_index.llms.openai import OpenAI as llama_openai
from common.common import parse_json_content  # Ensure this helper is available

def extract_learning_outcome_id(lo_text: str) -> str:
    """
    Extracts the learning outcome ID (e.g., 'LO4') from a learning outcome string.

    This function identifies and extracts an ID from formats like:
    - 'LO4: Description'
    - 'LO4 - Description'

    Args:
        lo_text (str): The full learning outcome text.

    Returns:
        str: The extracted learning outcome ID (e.g., 'LO4'), or an empty string if not found.
    """
    pattern = r"^(LO\d+)(?:[:\s-]+)"
    match = re.match(pattern, lo_text, re.IGNORECASE)
    return match.group(1) if match else ""

async def retrieve_content_for_learning_outcomes(extracted_data, engine):
    """
    Retrieves relevant content for each learning outcome based on its associated topics.

    Queries a content retrieval engine to extract all available course material that aligns 
    with the topics under each learning unit.

    Args:
        extracted_data (dict): Extracted data containing learning units and topics.
        engine: Query engine instance for retrieving content.

    Returns:
        list: A list of dictionaries, each containing:
            - "learning_outcome" (str): The learning outcome text.
            - "learning_outcome_id" (str): The extracted learning outcome ID.
            - "abilities" (list): List of ability IDs associated with the learning outcome.
            - "ability_texts" (list): List of ability descriptions.
            - "retrieved_content" (str): The retrieved content from the engine.
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

    print(f"DEBUG CS: Extracting abilities from {len(extracted_data.get('learning_units', []))} learning units")

    for lu in extracted_data["learning_units"]:
        lo = lu.get("learning_outcome", "")
        if not lo:
            print(f"⚠️ WARNING: Learning unit missing learning_outcome field, skipping LU")
            continue
        lo_id = extract_learning_outcome_id(lo)
        lu_title = lu.get("learning_unit_title", "Unknown LU")
        print(f"DEBUG CS: Processing LU: {lu_title}")

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

    print(f"DEBUG CS: Total unique abilities extracted: {len(unique_abilities)}")
    print(f"DEBUG CS: Ability IDs: {list(unique_abilities.keys())}")

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

    print(f"DEBUG CS: Returning {len(result)} question groups")
    return result

    # OLD CODE BELOW - KEEPING FOR REFERENCE BUT NOT USED
    if False:
        # Group abilities to ensure minimum number of questions
        groups_needed = max(min_questions, ability_count)
        abilities_per_group = max(1, ability_count // groups_needed)

        grouped_abilities = []
        for i in range(0, ability_count, abilities_per_group):
            group_abilities = all_abilities[i:i+abilities_per_group]
            if group_abilities:
                # Deduplicate abilities by ID
                unique_abilities = {}
                for a in group_abilities:
                    if a["id"] not in unique_abilities:
                        unique_abilities[a["id"]] = a

                grouped_abilities.append({
                    "learning_outcome": " | ".join(set([a["learning_outcome"] for a in group_abilities])),
                    "learning_outcome_id": ", ".join(set([a["learning_outcome_id"] for a in group_abilities])),
                    "abilities": list(unique_abilities.keys()),
                    "ability_texts": [unique_abilities[id]["text"] for id in unique_abilities.keys()],
                    "topics": list(set([a["topic"] for a in group_abilities]))
                })

        return grouped_abilities[:groups_needed]  # Ensure we don't exceed needed groups

    # Group similar abilities using LLM
    grouping_agent = AssistantAgent(
        name="ability_grouping_agent",
        model_client=model_client,
        system_message=f"""
        You are an expert at analyzing and grouping similar ability statements.
        Given a list of abilities, group similar ones together to create {min_questions}-8 groups.

        Guidelines:
        1. Group abilities that cover similar skills or tasks
        2. Each group should have a clear thematic connection
        3. Create at least {min_questions} groups (minimum requirement)
        4. Try to keep groups relatively balanced in size
        5. Return the grouping as valid JSON

        Output format:
        ```json
        {{
            "groups": [
                {{
                    "ability_ids": ["A1", "A3"],
                    "theme": "Brief description of common theme"
                }},
                {{
                    "ability_ids": ["A2", "A5"],
                    "theme": "Brief description of common theme"
                }}
            ]
        }}
        ```
        Return only the JSON between triple backticks followed by 'TERMINATE'.
        """
    )

    # Prepare abilities for grouping
    ability_summary = "\n".join([f"{i+1}. {a['id']}: {a['text']}" for i, a in enumerate(all_abilities)])

    task = f"""
    I have {ability_count} ability statements. Please group similar ones together to create {min_questions}-8 groups
    (minimum {min_questions} groups required):

    {ability_summary}

    Group these abilities by similarity and return the grouping in JSON format.
    """

    response = await grouping_agent.on_messages(
        [TextMessage(content=task, source="user")], CancellationToken()
    )

    if not response or not response.chat_message:
        # Fallback: create simple groups
        groups_needed = max(min_questions, min(8, ability_count))
        abilities_per_group = max(1, ability_count // groups_needed)

        grouped_abilities = []
        for i in range(0, ability_count, abilities_per_group):
            group_abilities = all_abilities[i:i+abilities_per_group]
            if group_abilities and len(grouped_abilities) < groups_needed:
                # Deduplicate abilities by ID
                unique_abilities = {}
                for a in group_abilities:
                    if a["id"] not in unique_abilities:
                        unique_abilities[a["id"]] = a

                grouped_abilities.append({
                    "learning_outcome": " | ".join(set([a["learning_outcome"] for a in group_abilities])),
                    "learning_outcome_id": ", ".join(set([a["learning_outcome_id"] for a in group_abilities])),
                    "abilities": list(unique_abilities.keys()),
                    "ability_texts": [unique_abilities[id]["text"] for id in unique_abilities.keys()],
                    "topics": list(set([a["topic"] for a in group_abilities]))
                })

        return grouped_abilities

    try:
        grouping_result = parse_json_content(response.chat_message.content)
        groups = grouping_result.get("groups", [])

        # Build grouped abilities
        grouped_abilities = []
        for group in groups:
            ability_ids = group.get("ability_ids", [])
            # Match ability_ids with actual abilities
            matched_abilities = []

            for ability in all_abilities:
                if ability["id"] in ability_ids:
                    matched_abilities.append(ability)

            if matched_abilities:
                # Deduplicate abilities by ID
                unique_abilities = {}
                for a in matched_abilities:
                    if a["id"] not in unique_abilities:
                        unique_abilities[a["id"]] = a

                grouped_abilities.append({
                    "learning_outcome": " | ".join(set([a["learning_outcome"] for a in matched_abilities])),
                    "learning_outcome_id": ", ".join(set([a["learning_outcome_id"] for a in matched_abilities])),
                    "abilities": list(unique_abilities.keys()),
                    "ability_texts": [unique_abilities[id]["text"] for id in unique_abilities.keys()],
                    "topics": list(set([a["topic"] for a in matched_abilities]))
                })

        # Ensure minimum number of groups
        if len(grouped_abilities) < min_questions:
            # Add remaining abilities as separate groups
            used_ids = set()
            for group in grouped_abilities:
                used_ids.update(group["abilities"])

            for ability in all_abilities:
                if ability["id"] not in used_ids and len(grouped_abilities) < min_questions:
                    grouped_abilities.append({
                        "learning_outcome": ability["learning_outcome"],
                        "learning_outcome_id": ability["learning_outcome_id"],
                        "abilities": [ability["id"]],
                        "ability_texts": [ability["text"]],
                        "topics": [ability["topic"]]
                    })

        return grouped_abilities if grouped_abilities else [{
            "learning_outcome": a["learning_outcome"],
            "learning_outcome_id": a["learning_outcome_id"],
            "abilities": [a["id"]],
            "ability_texts": [a["text"]],
            "topics": [a["topic"]]
        } for a in all_abilities[:min_questions]]

    except Exception as e:
        # Fallback: create simple groups
        groups_needed = max(min_questions, min(8, ability_count))
        abilities_per_group = max(1, ability_count // groups_needed)

        grouped_abilities = []
        for i in range(0, ability_count, abilities_per_group):
            group_abilities = all_abilities[i:i+abilities_per_group]
            if group_abilities and len(grouped_abilities) < groups_needed:
                # Deduplicate abilities by ID
                unique_abilities = {}
                for a in group_abilities:
                    if a["id"] not in unique_abilities:
                        unique_abilities[a["id"]] = a

                grouped_abilities.append({
                    "learning_outcome": " | ".join(set([a["learning_outcome"] for a in group_abilities])),
                    "learning_outcome_id": ", ".join(set([a["learning_outcome_id"] for a in group_abilities])),
                    "abilities": list(unique_abilities.keys()),
                    "ability_texts": [unique_abilities[id]["text"] for id in unique_abilities.keys()],
                    "topics": list(set([a["topic"] for a in group_abilities]))
                })

        return grouped_abilities


async def generate_cs_scenario(data: FacilitatorGuideExtraction, model_client) -> str:
    """
    Generates a realistic case study scenario for a given course.

    The scenario aligns with the learning outcomes and required abilities. It is at least 
    250 words long and presents a real-world organizational challenge relevant to the course.

    Args:
        data (FacilitatorGuideExtraction): Extracted course data containing learning outcomes and abilities.
        model_client: Language model client used to generate the scenario.

    Returns:
        str: A case study scenario description.
    """
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
    Generates a case study question-answer pair for a specific learning outcome.

    The generated question and answer are based on the provided case study scenario, 
    relevant learning outcome, and retrieved course content.

    Args:
        qa_generation_agent: The Autogen AssistantAgent for generating questions and answers.
        course_title (str): The course title.
        assessment_duration (str): The duration of the assessment.
        scenario (str): The shared case study scenario.
        learning_outcome (str): The learning outcome text.
        learning_outcome_id (str): The identifier for the learning outcome (e.g., 'LO1').
        retrieved_content (str): The retrieved content for this learning outcome.
        ability_ids (list): List of ability identifiers.
        ability_texts (list): List of ability statements.

    Returns:
        dict: A structured dictionary containing:
            - "learning_outcome_id" (str): The ID of the learning outcome.
            - "question_statement" (str): The generated case study question.
            - "answer" (list[str]): The detailed case study solution.
            - "ability_id" (list): The associated ability IDs.
    """

    agent_task = f"""
    Generate one scenario-based case study question-answer pair using the following details:
    - Course Title: '{course_title}'
    - Assessment Duration: '{assessment_duration}'
    - Scenario: '{scenario}'
    - Learning Outcome: '{learning_outcome}'
    - Learning Outcome ID: '{learning_outcome_id}'
    - REQUIRED Ability IDs: {ability_ids}
    - Ability Statements: {', '.join(ability_texts)}
    - Retrieved Content: {retrieved_content}

    Instructions:
    1. Use the provided scenario and retrieved content to generate one question-answer pair aligned with the Learning Outcome.
    2. The question should be directly aligned with the Learning Outcome and the associated abilities, and must be in a case study style.
    3. The answer must be a detailed case study solution that explains what to do, why it matters, and includes a short rationale for each recommended action.
    4. If any part of the answer is missing from the retrieved content, state: 'The retrieved content does not include that (information).'
    5. Include the learning outcome id in your response as "learning_outcome_id".
    6. CRITICAL: You MUST use EXACTLY these ability IDs in your response: {ability_ids}
       Do NOT modify, add, or remove any ability IDs. Return them exactly as provided.
    7. Return your output in valid JSON.
    """

    response = await qa_generation_agent.on_messages(
        [TextMessage(content=agent_task, source="user")],
        CancellationToken()
    )

    if not response or not response.chat_message:
        return None

    qa_result = parse_json_content(response.chat_message.content)

    # Validate the parsed result
    if qa_result is None or not isinstance(qa_result, dict):
        response_content = response.chat_message.content
        raise ValueError(
            f"Failed to parse CS response for {learning_outcome_id}. "
            f"Response length: {len(response_content)} chars. "
            f"Starts with: {response_content[:100]}... "
            f"Ends with: ...{response_content[-100:]}"
        )

    # Debug: Check if LLM returned wrong ability IDs
    llm_returned_abilities = qa_result.get("ability_id", [])
    if llm_returned_abilities != ability_ids:
        print(f"⚠️ CS: LLM returned wrong abilities! Expected {ability_ids}, got {llm_returned_abilities}. Using expected.")

    return {
        "learning_outcome_id": qa_result.get("learning_outcome_id", learning_outcome_id),
        "question_statement": qa_result.get("question_statement", "Question not provided."),
        "answer": qa_result.get("answer", ["Answer not available."]),
        "ability_id": ability_ids  # ALWAYS use the exact ability_ids we passed in, ignore LLM output
    }

async def generate_cs(extracted_data: FacilitatorGuideExtraction, index, model_client):
    """
    Generates a full case study assessment, including a scenario and multiple questions.

    This function:
    - Creates a case study scenario based on the course's learning outcomes and abilities.
    - Retrieves relevant content for each learning outcome.
    - Generates scenario-based questions and answers for each learning outcome.

    Args:
        extracted_data (FacilitatorGuideExtraction): Extracted course data with learning units.
        index: The knowledge retrieval index used for retrieving course content.
        model_client: The language model client used for generation.

    Returns:
        dict: A structured dictionary containing:
            - "course_title" (str): The course title.
            - "duration" (str): The assessment duration.
            - "scenario" (str): The generated case study scenario.
            - "questions" (list[dict]): A list of generated questions with answers.
    """
    from settings.api_manager import load_api_keys
    api_keys = load_api_keys()
    openai_api_key = api_keys.get("OPENAI_API_KEY", "")
    extracted_data = dict(extracted_data)
    
    scenario = await generate_cs_scenario(extracted_data, model_client)
    print(f"#################### SCENARIO ###################\n\n{scenario}")

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
            response_mode="compact"
        )
        lo_content_dict = await retrieve_content_for_learning_outcomes(extracted_data, qa_generation_query_engine)
    else:
        # Use empty content when no slide deck available
        lo_content_dict = {lo["Learning_Outcome"]: "" for lo in extracted_data.get("Learning_Outcomes", [])}

    qa_generation_agent = AssistantAgent(
        name="question_answer_generator",
        model_client=model_client,
        system_message=f"""
        You are an expert at creating simple, clear case study questions.

        Guidelines:
        1. Keep questions SIMPLE - ask ONE clear question about the scenario
        2. Write the question in 1-2 simple sentences
        3. Answer should be in PARAGRAPH form (NO bullet points, NO numbered lists)
        4. Write answer in simple, clear sentences
        5. Keep answer concise (3-5 sentences total)
        6. Use plain text - no markdown formatting

        Output format (valid JSON):
        ```json
        {{
            "learning_outcome_id": "<learning_outcome_id>",
            "question_statement": "<simple, clear question>",
            "answer": ["<answer in simple paragraph form, 3-5 sentences>"],
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

        tasks.append(generate_cs_for_lo(
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

    print(f"DEBUG CS: Generating {len(tasks)} questions...")
    results = await asyncio.gather(*tasks)
    questions = [q for q in results if q is not None]

    print(f"DEBUG CS: Successfully generated {len(questions)} questions")
    print(f"DEBUG CS: Failed questions: {len(results) - len(questions)}")

    return {
        "course_title": extracted_data["course_title"],
        "duration": assessment_duration,
        "scenario": scenario,
        "questions": questions
    }
