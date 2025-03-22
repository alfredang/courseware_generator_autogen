import json
from typing import Dict, List, Any
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from autogen_core.models import ChatCompletionClient
from autogen_agentchat.teams import RoundRobinGroupChat
import os
from dotenv import load_dotenv
from autogen_agentchat.ui import Console
import re

def add_full_citations_to_assessments(assessments, tsc_data):
    """Add the full citation texts to the assessment outputs for audit purposes"""
    
    # For SAQ assessment
    if "questions" in assessments["saq_assessment"]:
        for question in assessments["saq_assessment"]["questions"]:
            k_id = question.get("knowledge_id")
            # Find the LU that contains this knowledge ID
            for lu_id, lu_data in tsc_data.items():
                if k_id in lu_data.get("Knowledge", {}):
                    # Add the full citations from this LU
                    question["full_citations"] = lu_data.get("Citations", [])
                    # Add the full retrieved sources for audit
                    question["retrieved_sources"] = lu_data.get("RetrievedSources", [])
                    break
    
    # For PP assessment
    if "questions" in assessments["pp_assessment"]:
        for question in assessments["pp_assessment"]["questions"]:
            lo_id = question.get("learning_outcome_id")
            # Find the matching LU
            for lu_id, lu_data in tsc_data.items():
                if lu_id.startswith(lo_id):
                    # Add the full citations from this LU
                    if isinstance(question["answer"], dict):
                        question["answer"]["full_citations"] = lu_data.get("Citations", [])
                    else:
                        question["full_citations"] = lu_data.get("Citations", [])
                    # Add the full retrieved sources for audit
                    question["retrieved_sources"] = lu_data.get("RetrievedSources", [])
                    break
    
    return assessments

def debug_model_response(content, qa_result):
    """Print debug information for model responses"""
    print("\n----- DEBUG MODEL RESPONSE -----")
    print(f"Raw content snippet: {content[:200]}...")
    print(f"Parsed result: {qa_result}")
    if not qa_result or "question_statement" not in qa_result:
        print("WARNING: Missing question_statement in parsed result!")
    print("----- END DEBUG -----\n")

def parse_json_content(content):
    """More robust JSON parsing function"""
    # First try to extract JSON from markdown code blocks
    json_pattern = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
    match = json_pattern.search(content)
    
    if match:
        # If code block is present, extract the JSON content
        json_str = match.group(1)
    else:
        # Check if the content itself is JSON (starts with { and ends with })
        if content.strip().startswith('{') and content.strip().endswith('}'):
            json_str = content.strip()
        else:
            # Try to find any JSON object in the content
            json_pattern = re.compile(r'(\{.*\})', re.DOTALL)
            match = json_pattern.search(content)
            if match:
                json_str = match.group(1)
            else:
                print("No JSON content could be found in the response")
                return None
    
    try:
        # Parse the JSON string
        parsed_json = json.loads(json_str)
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"JSON string was: {json_str[:100]}...")
        return None

def load_tsc_json(file_path: str) -> Dict:
    """Load the updated TSC JSON file containing retrieved data."""
    with open(file_path, "r") as file:
        return json.load(file)

def extract_knowledge_statements(tsc_data: Dict) -> Dict[str, Dict]:
    """
    Extract all knowledge statements with their associated citations.
    
    Returns:
        Dict mapping "K1", "K2", etc. to dict with:
            - knowledge_text: The knowledge statement text
            - lu_id: Learning Unit ID
            - citations: List of citations from that LU
            - retrieved_sources: Full retrieved sources
    """
    knowledge_dict = {}
    
    for lu_id, lu_data in tsc_data.items():
        # Extract knowledge statements from this LU
        for k_id, k_text in lu_data.get("Knowledge", {}).items():
            knowledge_dict[k_id] = {
                "knowledge_text": k_text,
                "lu_id": lu_id,
                "citations": lu_data.get("Citations", []),
                "retrieved_sources": lu_data.get("RetrievedSources", [])
            }
    
    return knowledge_dict

def extract_ability_statements(tsc_data: Dict) -> Dict[str, List[Dict]]:
    """
    Extract all ability statements grouped by learning objective.
    
    Returns:
        Dict mapping LU ID to list of dicts with:
            - ability_id: The ability ID (A1, A2, etc.)
            - ability_text: The ability statement
            - citations: List of citations from that LU
            - retrieved_sources: Full retrieved sources  
    """
    lo_abilities_dict = {}
    
    for lu_id, lu_data in tsc_data.items():
        learning_objective = lu_data.get("LO", "")
        abilities = []
        
        for ability_id, ability_text in lu_data.get("Abilities", {}).items():
            abilities.append({
                "ability_id": ability_id,
                "ability_text": ability_text,
                "citations": lu_data.get("Citations", []),
                "retrieved_sources": lu_data.get("RetrievedSources", [])
            })
        
        if abilities:  # Only add if there are abilities
            lo_abilities_dict[lu_id] = {
                "learning_objective": learning_objective,
                "abilities": abilities
            }
    
    return lo_abilities_dict

async def generate_saq_from_tsc(tsc_data: Dict, model_client) -> Dict:
    """
    Generate SAQ questions and answers based on TSC data.

    Args:
        tsc_data: The loaded TSC JSON data
        model_client: The model client for question generation

    Returns:
        Dictionary with course_title, duration, and questions
    """
    
    # Extract all knowledge statements with citations
    knowledge_statements = extract_knowledge_statements(tsc_data)
    
    # Create QA generation agent
    qa_generation_agent = AssistantAgent(
        name="question_answer_generator",
        model_client=model_client,
        system_message="""
        You are an expert question-answer crafter with deep domain expertise. Your task is to generate a theory-based question and answer pair for a given knowledge statement using the provided citations. Your response must be grounded in the provided citations.

        Guidelines:
        1. Create a scenario-based question that assesses the knowledge statement.
        2. The question should be theory-based and test conceptual understanding.
        3. Use the citations to inform both the question and answer.
        4. Provide bullet-point answers that directly address the question.
        5. Include the citations used in your answer.
        6. Structure your response in valid JSON format with scenario, question_statement, knowledge_id, answer, and citations fields.
        
        Return the JSON between triple backticks followed by 'TERMINATE'.
        """
    )
    
    # Generate questions for each knowledge statement
    questions = []
    for k_id, k_data in knowledge_statements.items():
        # Skip knowledge statements with no citations
        if not k_data.get("citations"):
            continue
        
        agent_task = f"""
        Please generate one theory-based question-answer pair using the following:
        - Knowledge Statement ID: {k_id}
        - Knowledge Statement: '{k_data["knowledge_text"]}'
        - Citations:
        {json.dumps(k_data["citations"], indent=2)}

        Instructions:
        1. Craft a realistic scenario in 2-3 sentences that provides context related to the knowledge statement.
        2. Formulate a single, straightforward short-answer question that tests theoretical understanding of the knowledge statement.
        3. Provide concise, practical bullet points as the answer.
        4. IMPORTANT: Use the EXACT citation references provided above. Do not create new citation references.
        5. The question and answers must be complete and of a sufficient complexity for adult learners.
        6. Return the question and answer as a JSON object directly.

        Your JSON output should have this structure:
        {{
        "scenario": "Your scenario here",
        "question_statement": "Your question here",
        "answer": ["Bullet point 1", "Bullet point 2", "Bullet point 3"],
        "citations_used": ["Source 1", "Source 2"]  // List only the citation references you actually used
        }}
        """
        
        response = await qa_generation_agent.on_messages(
            [TextMessage(content=agent_task, source="user")], CancellationToken()
        )
        
        if not response or not response.chat_message:
            continue
            
        qa_result = parse_json_content(response.chat_message.content)
        debug_model_response(response.chat_message.content, qa_result)
        
        questions.append({
        "scenario": qa_result.get("scenario", "Scenario not provided."),
        "question_statement": qa_result.get("question_statement", "Question not provided."),
        "knowledge_id": k_id,
        "answer": qa_result.get("answer", ["Answer not available."]),
        "citations": k_data.get("citations", [])  # Use the ORIGINAL citations from TSC, not LLM-generated ones
        })
    
    return {
        "questions": questions
    }

async def generate_pp_from_tsc(tsc_data: Dict, model_client) -> Dict:
    """
    Generate practical performance assessment questions based on TSC data.

    Args:
        tsc_data: The loaded TSC JSON data
        model_client: The model client for question generation

    Returns:
        Dictionary with course_title, duration, scenario, and questions
    """
    
    # Extract learning objectives with their abilities
    lo_abilities = extract_ability_statements(tsc_data)
    
    # Generate a scenario for the PP assessment
    scenario = await generate_pp_scenario_from_tsc(tsc_data, model_client)
    
    # Create QA generation agent for practical tasks
    qa_generation_agent = AssistantAgent(
        name="practical_task_generator",
        model_client=model_client,
        system_message="""
        You are an expert in creating practical coding assessments. Your task is to generate hands-on coding tasks that assess specific abilities.

        Guidelines:
        1. Create direct, hands-on coding tasks that require practical implementation.
        2. Each response MUST include both a specific question_statement and an expected_output.
        3. The question_statement should clearly describe a practical task related to the abilities.
        4. The question must end with "Take snapshots of your commands at each step and paste them below."
        5. The answer should be in the format: {"expected_output": "The snapshot should include: [detailed steps]", "citations": [list of citations]}
        6. Structure your response in valid JSON format with both question_statement and answer fields.
        
        Return the JSON between triple backticks followed by 'TERMINATE'.
        """
    )
    
    # Generate questions for each learning objective
    questions = []
    for lu_id, lo_data in lo_abilities.items():
        learning_objective = lo_data["learning_objective"]
        abilities = lo_data["abilities"]
        
        # Skip if no abilities
        if not abilities:
            continue
        
        # Combine the abilities text for context
        ability_ids = [a["ability_id"] for a in abilities]
        ability_texts = [a["ability_text"] for a in abilities]
        
        # Get all citations for this LU
        all_citations = []
        for ability in abilities:
            all_citations.extend(ability["citations"])
        
        agent_task = f"""
        Generate one practical performance assessment question-answer pair using the following details:
        - Learning Objective: '{learning_objective}'
        - Learning Objective ID: '{lu_id}'
        - Associated Ability IDs: {', '.join(ability_ids)}
        - Associated Ability Statements: {', '.join(ability_texts)}
        - Scenario: '{scenario}'
        - Citations: {json.dumps(all_citations, indent=2)}

        Instructions:
        1. Create a SPECIFIC, direct, hands-on task in 2-3 sentences.
        2. The task should require writing, modifying, or executing Git commands or scripts.
        3. The question must end with "Take snapshots of your commands at each step and paste them below."
        4. The answer should start with "The snapshot should include: " followed by the expected output.
        5. IMPORTANT: Do not generate new citations. Your answer will use the original citations provided above.
        6. Return your output in valid JSON format with the following structure:
        ```json
        {{
        "question_statement": "Your specific [topic] task here... Take snapshots of your commands at each step and paste them below.",
        "answer": {{
            "expected_output": "The snapshot should include: [numbered steps with specific Git commands]",
            "citations_used": ["Source X"]  // List only the citation references you actually used
        }}
        }}
        """

        response = await qa_generation_agent.on_messages(
            [TextMessage(content=agent_task, source="user")], CancellationToken()
        )
        
        if not response or not response.chat_message:
            continue
            
        qa_result = parse_json_content(response.chat_message.content)
        debug_model_response(response.chat_message.content, qa_result)
        
        questions.append({
            "learning_outcome_id": lu_id.split(":")[0],
            "question_statement": qa_result.get("question_statement", "Question not provided."),
            "answer": qa_result.get("answer", ["Answer not available."]),
            "ability_id": ability_ids
        })
    
    return {
        "scenario": scenario,
        "questions": questions
    }

async def generate_pp_scenario_from_tsc(tsc_data: Dict, model_client) -> str:
    """
    Generate a practical performance scenario from TSC data.
    
    Args:
        tsc_data: The loaded TSC JSON data
        model_client: The model client for text generation
        
    Returns:
        A string containing the scenario
    """
    # Extract learning objectives
    learning_outcomes = []
    abilities = []
    
    for lu_id, lu_data in tsc_data.items():
        learning_outcomes.append(lu_data.get("LO", ""))
        for ability_id, ability_text in lu_data.get("Abilities", {}).items():
            abilities.append(ability_text)
    
    # Format for the prompt
    outcomes_text = "\n".join([f"- {lo}" for lo in learning_outcomes if lo])
    abilities_text = "\n".join([f"- {ability}" for ability in abilities if ability])
    
    agent_task = f"""
    Design a realistic practical performance assessment scenario for a course.
    
    The scenario should align with the following:
    
    Learning Outcomes:
    {outcomes_text}
    
    Abilities:
    {abilities_text}
    
    The scenario should describe a company or organization facing practical challenges with the identified domain.
    Provide background context aligning to the learning outcomes and abilities.
    End the scenario by stating the learner's role in the company.
    Ensure the scenario is concise (1 paragraph), realistic, and requires the learner to perform hands-on topic tasks.
    """
    
    # Instantiate the agent for scenario generation
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

async def generate_assessments_from_tsc(tsc_json_path: str, model_client):
    """
    Generate both SAQ and PP assessments from the TSC JSON file.
    
    Args:
        tsc_json_path: Path to the updated_TSC.json file
        model_client: The model client to use
        
    Returns:
        Dict containing both SAQ and PP assessments
    """
    # Load the TSC JSON data
    tsc_data = load_tsc_json(tsc_json_path)
    
    # Generate SAQ assessment
    saq_assessment = await generate_saq_from_tsc(tsc_data, model_client)
    
    # Generate PP assessment
    pp_assessment = await generate_pp_from_tsc(tsc_data, model_client)
    
    assessments = {
        "saq_assessment": saq_assessment,
        "pp_assessment": pp_assessment
    }
    
    # Add full citations for audit purposes
    assessments = add_full_citations_to_assessments(assessments, tsc_data)
    
    return assessments

async def create_content():
    # # Initialize the model client (replace with your preferred client)
    # model_client = GPTAssistantAgent.create_assistant(
    #     name="Assessment Generator",
    #     model="gpt-4-turbo",
    #     instructions="You are an expert in creating educational assessments."
    # )

    GEMINI_API_KEY = "AIzaSyCmOGao7Q5KcchIcPtlFmXFDRdxjHnPsEA" # currently being used for the front portion of the code, suggest cycling in order to prevent API rate limits
    GEMINI_API_KEY2 = "AIzaSyAG-_wC_snVnx055KpsGrG0_05NHT4puD0"

    gemini_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "gemini-2.0-flash-lite",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": GEMINI_API_KEY2,
        "model_info": {
            "family": "unknown",
            "function_calling": False,
            "json_output": True,
            "vision": False
        }
    }
    }

    model_client = ChatCompletionClient.load_component(gemini_config)
    
    # Generate assessments from TSC data
    tsc_json_path = "output_json/updated_TSC.json"
    assessments = await generate_assessments_from_tsc(tsc_json_path, model_client)
    
    # Save the assessments
    with open("output_json/saq_assessment.json", "w") as f:
        json.dump(assessments["saq_assessment"], f, indent=2)
        
    with open("output_json/pp_assessment.json", "w") as f:
        json.dump(assessments["pp_assessment"], f, indent=2)
    
    print("Assessments generated successfully!")

# if __name__ == "__main__":
#     asyncio.run(create_content())