import autogen
import dotenv
import json
import os
import streamlit as st
from autogen import UserProxyAgent, AssistantAgent
from pprint import pprint
import subprocess
import sys
import re
from e_validate import validate_knowledge_and_ability
import shutil

def execute_document_parser(input_docx, output_json):
    subprocess.run([sys.executable, "document_parser.py", input_docx, output_json], check=True)
    print("document_parser.py executed successfully.")

def execute_justification_agent():
    subprocess.run([sys.executable, "justification_agent.py"], check=True)
    print("justification_agent.py executed successfully.")

def execute_json_docu_replace(input_json, input_docx, output_docx):
    subprocess.run([sys.executable, "json_docu_replace.py", input_json, input_docx, output_docx], check=True)
    print("json_docu_replace.py executed successfully.")

def execute_json_mapping():
    subprocess.run([sys.executable, "json_mapping.py"], check=True)
    print("json_mapping.py executed successfully.")

def execute_jinja_docu_replace(input_json, input_docx, output_docx):
    subprocess.run([sys.executable, "jinja_docu_replace.py", input_json, input_docx, output_docx], check=True)
    print("jinja_docu_replace.py executed successfully.")

dotenv.load_dotenv()
# Check for correct number of arguments
if len(sys.argv) != 5:
    print("Usage: python main.py <input_docx> <output_json> <word_template> <output_docx>")
    sys.exit(1)

# Extract command-line arguments
input_docx = sys.argv[1]
output_json = sys.argv[2]
word_template = sys.argv[3]
output_docx = sys.argv[4]

# Step 1: Execute document_parser.py
execute_document_parser(input_docx, output_json)

# Load the JSON file into a Python variable
with open(output_json, 'r', encoding='utf-8') as file:
    data = json.load(file)

def check_and_save_json(response, output_filename, agent_name):
    """
    This function checks the chat history in the response object,
    attempts to find and parse JSON content, and saves it to a file.
    The function is dynamic and works with any agent by specifying the agent's name.
    """
    if response and hasattr(response, 'chat_history') and response.chat_history:
        # Loop through the chat history to find the correct entry
        for entry in response.chat_history:
            if entry['role'] == 'user' and entry['name'] == agent_name:
                generated_json_content = entry.get('content', '').strip()

                if generated_json_content:
                    try:
                        # Attempt to parse the JSON content
                        parsed_content = json.loads(generated_json_content)
                        
                        # Save the parsed JSON content to a file
                        with open(output_filename, 'w') as json_file:
                            json.dump(parsed_content, json_file, indent=4)
                        print(f"Generated JSON content from '{agent_name}' has been saved to '{output_filename}'.")
                    except json.JSONDecodeError as e:
                        print(f"Failed to decode JSON from '{agent_name}': {e}")
                else:
                    print(f"No content found in the relevant chat history entry from '{agent_name}'.")
    else:
        print(f"Unexpected response structure or empty chat history for agent '{agent_name}'.")


# Load API key from environment
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Manually create the config list with JSON response format
config_list = [
    {
        "model": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
        "response_format": {"type": "json_object"},
    }
]

more_compute_config_list = [
    {
        "model": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
        "response_format": {"type": "json_object"},
    }
]

llm_config = {
    "temperature": 0.5,
    "config_list": config_list,
    "timeout": 120,  # in seconds
    "cache_seed": None,
}

more_compute_llm_config = {
    "temperature": 0.5,
    "config_list": more_compute_config_list,
    "timeout": 120,  # in seconds
    "cache_seed": None,
}

course_info_extractor = AssistantAgent(
    name="course_info_extractor",
    llm_config=llm_config,
    system_message="""
    You are an assistant tasked with extracting specific information from the provided data. 
    You must return the information in a JSON structure.
    """,
)

learning_outcomes_extractor = AssistantAgent(
    name="learning_outcomes_extractor",
    llm_config=llm_config,
    system_message="""
    You are an assistant tasked with extracting specific information from the provided data. 
    You must return the information in a JSON structure.
    """,
)

tsc_and_topics_extractor = AssistantAgent(
    name="tsc_and_topics_extractor",
    llm_config=llm_config,
    system_message="""
    You are an assistant tasked with extracting specific information from the provided data. 
    You must return the information in a JSON structure.
    """,
)

assessment_methods_extractor = AssistantAgent(
    name="assessment_methods_extractor",
    llm_config=llm_config,
    system_message="""
    You are an assistant tasked with extracting specific information from the provided data. 
    You must return the information in a JSON structure.
    """,
)

aggregator = AssistantAgent(
    name="aggregator",
    llm_config=llm_config,
    system_message="""
    You are an assistant tasked with extracting specific information from the provided data. 
    You must return the information in a JSON structure.
    """,
)

user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    code_execution_config={
        "work_dir": "cwgen_output",
        "use_docker": False
    },
)

editor = AssistantAgent(
    name="Editor",
    llm_config=llm_config,
    system_message=f"""
    You are a json editor intended to edit content from one json file to another. You are to follow all instructions to the letter, and not to change the format of the json files in any way. 
    """
)

# Define the agents
background_analyst = AssistantAgent(
    name="Background_Analyst",
    llm_config=llm_config,
    system_message="""You are responsible for analyzing the targeted sector(s) background and needs for the training. 
    Your task is to generate a structured response based on industry trends, challenges, and roles.""",
)

performance_gap_analyst = AssistantAgent(
    name="Performance_Gap_Analyst",
    llm_config=llm_config,
    system_message="""You are responsible for identifying the performance gaps that the course will address.
    Elaborate on how these gaps were identified and describe the job roles that would benefit from the training.""",
)

sequencing_rationale_agent = AssistantAgent(
    name="Sequencing_Rationale_Agent",
    llm_config=llm_config,
    system_message="""You are an experienced course developer. Your task is to justify the rationale of sequencing 
    using a step-by-step curriculum framework for the given course.""",
)

validator = AssistantAgent(
    name="Validator",
    llm_config=llm_config,
    system_message="""You are responsible for validating the outputs of all agents to ensure they adhere to the guidelines.
    Check for legibility, correct formatting, and proper execution of instructions.
    If it is satisfactory, return the received message as your output.
    If unsatisfactory, return your comments and further instructions, along with the originally received message.
    Ensure that your instructions are carried out, and not included in the final message for the receiving agent.
    """,
)

final_editor = AssistantAgent(
    name="Final_Editor",
    llm_config=llm_config,
    system_message=f"""
    You are a json editor intended to edit content from one json file to another. You are to follow all instructions to the letter, and not to change the format of the json files in any way. 
    """
)

def reflection_message(recipient, messages, sender, config):
    print("Reflecting...")
    return f"""
    Validate and ensure that the following message follows guidelines and the context of the providing agent.
    Guidelines are: Message is legible and makes sense contextually, and the replies are in JSON format. Do not pass forward your comments to the next agent.
    \n\n {recipient.chat_messages_for_summary(sender)[-1]['content']}
    """

def formatting_validation_message(recipient, messages, sender, config):
    print("Reflecting...")
    return f"""Validate and ensure that the following message 
    follows guidelines and the context of the providing agent.
    Guidelines are: Replies are in JSON format, Validator Inputs are not included, Editor's final reply MUST have an aggregation of all research agents' outputs.
    \n\n {recipient.chat_messages_for_summary(sender)[-1]['content']}"""

user_proxy.register_nested_chats(
    [
        {
            "recipient": validator,
            "message": reflection_message,
            "max_turns": 1,
            "summary_method": "last_msg",
        }
    ],
    trigger=background_analyst,  # condition=my_condition,
)

user_proxy.register_nested_chats(
    [
        {
            "recipient": validator,
            "message": reflection_message,
            "max_turns": 1,
            "summary_method": "last_msg",
        }
    ],
    trigger=performance_gap_analyst,  # condition=my_condition,
)

user_proxy.register_nested_chats(
    [
        {
            "recipient": validator,
            "message": formatting_validation_message,
            "max_turns": 1,
            "summary_method": "last_msg",
        }
    ],
    trigger=editor,  # condition=my_condition,
)

# insert extraction pipeline here
course_info_extractor_message = f"""
You are to extract the following variables from {data}:
    1) Course Title
    2) Name of Organisation
    3) Classroom Hours
    4) Number of Assessment Hours
    5) Course Duration (Number of Hours)
    6) Industry

    Use the term_library below for "Industry", based on the front 3 letters of the TSC code:
    term_library = {{
        'ACC': 'Accountancy',
        'RET': 'Retail',
        'MED': 'Media',
        'ICT': 'Infocomm Technology',
        'BEV': 'Built Environment',
        'DSN': 'Design',
        'DNS': 'Design',
        'AGR': 'Agriculture',
        'ELE': 'Electronics',
        'LOG': 'Logistics',
        'STP': 'Sea Transport',
        'TOU': 'Tourism",
        'AER': 'Aerospace',
        'ATP': 'Air Transport',
        'BEV': 'Built Environment',
        'BPM': 'BioPharmaceuticals Manufacturing',
        'ECM': 'Energy and Chemicals',
        'EGS': 'Engineering Services',
        'EPW': 'Energy and Power',
        'EVS': 'Environmental Services',
        'FMF': 'Food Manufacturing',
        'FSE': 'Financial Services',
        'FSS': 'Food Services',
        'HAS': 'Hotel and Accommodation Services',
        'HCE': 'Healthcare',
        'HRS': 'Human Resource',
        'INP': 'Intellectual Property',
        'LNS': 'Landscape',
        'MAR': 'Marine and Offshore',
        'PRE': 'Precision Engineering',
        'PTP': 'Public Transport',
        'SEC': 'Security',
        'SSC': 'Social Service',
        'TAE': 'Training and Adult Education'
        'WPH': 'Workplace Safety and Health'
        'WST': 'Wholesale Trade'
        'STP': 'Sea Transport',
        'TOU': 'Tourism",
        'ECC': 'Early Childhood Care and Education',
        'ART': 'Arts'



    }}
    Format the extracted data in JSON format, with this structure, do NOT change the key names or add unnecessary spaces:
        "Course Information": {{
        "Course Title": "",
        "Name of Organisation": "",
        "Classroom Hours": ,
        "Number of Assessment Hours": ,
        "Course Duration (Number of Hours)": ,
        "Industry": ""
    }}
    Extra emphasis on following the JSON format provided, do NOT change the names of the keys, never use "course_info" as the key name.
"""

learning_outcomes_extractor_message = f"""
You are to extract the following variables from {data}:
    1) Learning Outcomes, include the terms LO(x): in front of each learning outcome
    2) Knowledge
    3) Ability

    Text Blocks which start with K or A and include a semicolon should be mapped under Knowledge (for K) and Ability (for A).

    An example output is as follows:
    "Learning Outcomes":  ["LO1: Calculate profitability ratios to assess an organization's financial health.", "LO2: Calculate performance ratios to evaluate an organization's overall financial performance."], 
    "Knowledge": ["K1: Ratios for profitability\nK2: Ratios for performance"], 
    "Ability": ["A1: Calculate ratios for assessing organisation's profitability\nA2: Calculate ratios for assessing organisation's financial performance"], 


    Format the extracted data in JSON format, with this structure:
        "Learning Outcomes": {{
        "Learning Outcomes": [

        ],
        "Knowledge": [

        ],
        "Ability": [
        ]
        }}
    }}
"""

tsc_and_topics_extractor_message = f"""
You are to extract the following variables from {data}:
    1) TSC Title
    2) TSC Code
    3) Topic (include the FULL string, including any K's and A's, only include items starting with "Topic" and not "LU" for this particular point)
    4) Learning Units (do NOT include Topics under this point, do NOT include any brackets consisting of A's or K's), if there are no Learning Units (LUs) found, summarize a LU from each Topics and name them sequentially. The LUs should NOT have the same name as the topics.

    An example output is as follows:
    "TSC Title": "Financial Analysis",
    "TSC Code": "ACC-MAC-3004-1.1",
    "Topic": ["Topic 1 Assessing Organization’s Profitability (K1, A1)", "Topic 2 Evaluating an Organization’s Performance Using Ratio Analysis (K2, A2)"],
    "Learning Units": ["LU1: Data Preparation for Machine Learning (ML)", "LU2: ML Model Development"]

    Format the extracted data in JSON format, with this structure:
        "TSC and Topics": {{
        "TSC Title": [
            
        ],
        "TSC Code": [
            
        ],
        "Topics": [

        ],
        "Learning Units": [

        ]
    }}
"""

assessment_methods_extractor_message = f"""
You are to extract the following variables from {data}:
    1) Assessment Methods (remove the brackets and time values at the end of each string)
    2) Instructional Methods
    3) Amount of Practice Hours
    4) Course Outline, which consists of Learning Units (LUs), Topics under that Learning Unit and their descriptions. A Learning Unit may have more than 1 topic, so nest that topic and its relevant descriptions under that as well.

    Include the full topic names in Course Outline, including any bracketed K and A factors.

    Format the extracted data in JSON format, with this structure:
        "Assessment Methods": {{
        "Assessment Methods": [
            "",
            ""
        ],
        "Amount of Practice Hours": Insert "N.A." if not found or not specified,
        "Course Outline": {{
            "Learning Units": {{
                "LU1": {{
                    "Description": [
                        ""
                    ]
                }},
                "LU2": {{
                    "Description": [
                        {{
                            "Topic": "Topic 1: Empathize and Define (K1, A1)",
                            "Details": [
                                "Techniques for understanding user needs",
                                "Methods for defining clear problem statements",
                                "Exercises: Empathy mapping and problem definition"
                            ]
                        }},
                        {{
                            "Topic": "Topic 2: Ideate and Prototype (K2, A2)",
                            "Details": [
                                "Strategies for brainstorming and generating creative solutions",
                                "Steps to create and refine prototypes",
                                "Activities: Brainstorming sessions and prototyping workshops"
                            ]
                        }},
                        {{
                            "Topic": "Topic 3: Test and Iterate (K3, A3)",
                            "Details": [
                                "Importance of gathering user feedback",
                                "Methods for testing and iterating solutions",
                                "Workshops: Testing prototypes and iterative improvements"
                            ]
                        }}                    
                        ]
                }}
                }}
            }}
        Instructional Methods: ""
            }}
    
"""

aggregator_message = f"""
You are to combine the outputs from the following agents into a single JSON object, do NOT aggregate output from the validator agent:
    1) course_info_extractor
    2) learning_outcomes_extractor
    3) tsc_and_topics_extractor
    4) assessment_methods_extractor
Return the combined output into a single JSON file, do not alter the keys in any way, do not add or nest any keys.
"""

extraction_results = user_proxy.initiate_chats(  # noqa: F704
    [
        {
            "chat_id": 1,
            "recipient": course_info_extractor,
            "message": course_info_extractor_message,
            "silent": False,
            "max_turns":1,
            "summary_method": "last_msg",
        },
        {
            "chat_id": 2,
            # "prerequisites": [1],
            "recipient": learning_outcomes_extractor,
            "message": learning_outcomes_extractor_message,
            "silent": False,
            "max_turns":1,
            "summary_method": "last_msg",
        },
        {
            "chat_id": 3,
            # "prerequisites": [1],
            "recipient": tsc_and_topics_extractor,
            "message": tsc_and_topics_extractor_message,
            "silent": False,
            "max_turns":1,
            "summary_method": "last_msg",
        },
        {
            "chat_id": 4,
            # "prerequisites": [1],
            "recipient": assessment_methods_extractor,
            "message": assessment_methods_extractor_message,
            "silent": False,
            "max_turns":1,
            "summary_method": "last_msg",
        },
        {"chat_id": 5, "prerequisites": [1, 2, 3, 4], "recipient": aggregator, "silent": False, "message": aggregator_message, "max_turns":1},
    ]
)

aggregator_response = aggregator.last_message()["content"]

# Step 2: Extract the JSON portion from the response
# Find the first occurrence of '{' and the last occurrence of '}'
start_index = aggregator_response.find('{')
end_index = aggregator_response.rfind('}')

if start_index != -1 and end_index != -1:
    # Extract the JSON substring
    json_string = aggregator_response[start_index:end_index + 1]
    print("Extracted JSON String -----------")
    print(json_string)

    # Step 3: Try parsing the JSON
    try:
        parsed_output = json.loads(json_string)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        parsed_output = {}
else:
    print("No valid JSON found in the response.")
    parsed_output = {}

# Step 4: Save the parsed output to a JSON file
output_filename = 'ensemble_output.json'
try:
    with open(output_filename, 'w') as json_file:
        json.dump(parsed_output, json_file, indent=4)
    print(f"Output saved to {output_filename}")
except IOError as e:
    print(f"Error saving JSON to file: {e}")

# Step 2: Execute the second agent (Interpreter) using the generated output
with open('ensemble_output.json', 'r') as file:
    ensemble_output = json.load(file)

# If ensemble_output is a JSON string, parse it first
if isinstance(ensemble_output, str):
    ensemble_output = json.loads(ensemble_output)


# ensure that key names are constant
key_mapping = {
    "course_info": "Course Information",
    "learning_outcomes": "Learning Outcomes",
    "tsc_and_topics": "TSC and Topics",
    "assessment_methods": "Assessment Methods"
}

def rename_keys_in_json_file(filename, key_mapping):
    # Load the JSON data from the file
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Rename keys according to the key_mapping
    for old_key, new_key in key_mapping.items():
        if old_key in data:
            data[new_key] = data.pop(old_key)
    
    # Save the updated JSON data back to the same file
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)
    
    print(f"Updated JSON saved to {filename}")

# Example usage
filename = 'ensemble_output.json'
rename_keys_in_json_file(filename, key_mapping)

def update_knowledge_ability_mapping(tsc_json_path, ensemble_output_json_path):
    # Load the JSON files
    with open(tsc_json_path, 'r', encoding='utf-8') as tsc_file:
        tsc_data = json.load(tsc_file)
    
    with open(ensemble_output_json_path, 'r', encoding='utf-8') as ensemble_file:
        ensemble_data = json.load(ensemble_file)
    
    # Extract the learning units from output_TSC
    course_proposal_form = tsc_data.get("Course_Proposal_Form", {})
    learning_units = {key: value for key, value in course_proposal_form.items() if key.startswith("LU")}
    
    # Prepare the Knowledge and Ability Mapping structure in ensemble_output if it does not exist
    if "Knowledge and Ability Mapping" not in ensemble_data["Learning Outcomes"]:
        ensemble_data["Learning Outcomes"]["Knowledge and Ability Mapping"] = {}

    # Loop through each Learning Unit to extract and map K and A factors
    for index, (lu_key, topics) in enumerate(learning_units.items(), start=1):
        ka_key = f"KA{index}"
        ka_mapping = []

        # Extract K and A factors from each topic within the Learning Unit
        for topic in topics:
            # Match K and A factors in the topic string using regex
            matches = re.findall(r'\b(K\d+|A\d+)\b', topic)
            if matches:
                ka_mapping.extend(matches)

        # Ensure only unique K and A factors are added
        ka_mapping = list(dict.fromkeys(ka_mapping))  # Remove duplicates while preserving order

        # Add the KA mapping to the ensemble_data
        ensemble_data["Learning Outcomes"]["Knowledge and Ability Mapping"][ka_key] = ka_mapping

    # Save the updated JSON to the same file path
    with open(ensemble_output_json_path, 'w', encoding='utf-8') as outfile:
        json.dump(ensemble_data, outfile, indent=4, ensure_ascii=False)

    print(f"Updated Knowledge and Ability Mapping saved to {ensemble_output_json_path}")

# Example usage
update_knowledge_ability_mapping('output_TSC.json', 'ensemble_output.json')

validate_knowledge_and_ability()

# insert research analysts
background_message = f"""
As a training consultant focusing on analyzing performance gaps and training needs based on course learning outcomes,
your task is to assess the targeted sector(s) background and needs for the training. Your analysis should be structured
clearly and based on the provided course title and industry.
Do not use any control characters such as newlines.
Do not mention the course name in your answer.

Answer the following question based on the extracted data from the first agent in {ensemble_output}:
(i) Targeted sector(s) background and needs for the training: Using the Course Title, and the Industry from {ensemble_output.get('Course Information', [])}.

This portion must be at least 600 words long with each point consisting of at least 200 words, and structured into three paragraphs:
1. Challenges and performance gaps in the industry related to the course.
2. Training needs necessary to address these gaps.
3. Job roles that would benefit from the training.

Format your response in the given JSON structure under "Background Information".
 "Background Analysis": {{
        "Challenges and performance gaps in the industry related to the course": "",
        "Training needs necessary to address these gaps": "",
        "Job roles that would benefit from the training": ""
    }}
"""

performance_gap_message = f"""
You are responsible for identifying the performance gaps and post-training benefits to learners that the course will address.
Based on the extracted data, answer the following question:
(ii) Performance gaps that the course will address for the given course title and learning outcomes: {ensemble_output.get('Course Information', {}).get('Course Title', [])}, {ensemble_output.get('Learning Outcomes', {}).get('Learning Outcomes', [])}.
Do not use any control characters such as newlines.

Your task is to perform the following:
1. For each Learning Outcome (LO), provide one unique performance gap, one corresponding attribute gained, and one post-training benefit to learners. Do not repeat performance gaps or attributes across different LOs.
2. However, in the event that there are only 2 Learning Outcomes, you are to provide 3 unique performance gaps and corresponding attributes gained.
3. However, in the event that there are more than 5 Learning Outcomes, your answers are to be limited to 5 unique performance gaps and corresponding attributes gained.

Format your response in the given JSON structure under "Performance Gaps".
Your answer for (ii.) is to be given in a point format with three distinct sections, appended together as one list element with new line separators, this is an example with only 3 Learning Outcomes, hence 3 points each:
{{

Performance gaps:
Learners struggle/are unclear with [specific skill or knowledge gap].
(perform this analysis for the LOs)

Attributes gained:
Ability/Proficiency to [specific skill or knowledge learned].
(perform this analysis for the LOs)

Post training benefits:
(perform this analysis for the LOs)

}}

"""

sequencing_rationale_message = f"""
You are an experienced course developer. Your task is to justify the rationale of sequencing 
using a step-by-step curriculum framework for the course titled: {ensemble_output.get('Course Information', {}).get('Course Title', [])}.
Have one pointer within Performance Gaps and Attributes Gained for each Learning Outcome
Do not use any control characters such as newlines.
Do not mention any course names in your analysis.
Ensure that all Learning Units are accounted for in your analysis.

Reference the following JSON variables in your response:
1. Learning outcomes: {ensemble_output.get('Learning Outcomes', {}).get('Learning Outcomes', [])}
2. Learning units: {ensemble_output.get('TSC and Topics', {}).get('Learning Units', [])}
3. Course outline: {ensemble_output.get('Assessment Methods', {}).get('Course Outline', [])}

Output your response for (iii.) in the following format, for example:
{{
    Sequencing Explanation: For this course, the step-by-step sequencing is employed to scaffold the learners' comprehension and application of video marketing strategies using AI tools. The methodology is crucial as it system-atically breaks down the intricate facets of video marketing, inbound marketing strategies, and AI tools into digestible units. This aids in gradually building the learners' knowledge and skills from fundamental to more complex concepts, ensuring a solid foundation before advancing to the next topic. The progression is designed to foster a deeper understanding and the ability to effectively apply the learned concepts in real-world marketing scenarios.

    LU1: 
        Title: Translating Strategy into Action and Fostering a Customer-Centric Culture
        Description: LU1 lays the foundational knowledge by introducing learners to the organization's inbound marketing strategies and how they align with the overall marketing strategy. The facilitator will guide learners through translating these strategies into actionable plans and understanding the customer decision journey. This unit sets the stage for fostering a customer-centric culture with a particular focus on adhering to organizational policies and guidelines. The integration of AI tools in these processes is introduced, giving learners a glimpse into the technological aspects they will delve deeper into in subsequent units.

    LU2: 
        Title: Improving Inbound Marketing Strategies and Content Management
        Description: Building on the foundational knowledge, LU2 dives into the practical aspects of content creation and curation and how AI tools can be utilized for strategy improvement. Learners will be led through exercises to recommend improvements and manage content across various platforms. The hands-on activities in this unit are designed to enhance learners' ability to manage and optimize video content, crucial skills in video marketing with AI tools.

    LU3: 
        Title: Leading Customer Decision Processes and Monitoring Inbound Marketing Effectiveness
        Description: LU3 escalates to a higher level of complexity where learners delve into lead conversion processes, leading customers through decision processes, and evaluating marketing strategy effectiveness. Under the guidance of the facilitator, learners will engage in monitoring and reviewing inbound marketing strategies, thereby aligning theoretical knowledge with practical skills in a real-world context. The synthesis of previous knowledge with advanced concepts in this unit culminates in a comprehensive understanding of video marketing with AI tools, equipping learners with the requisite skills to excel in the modern marketing landscape.

    Conclusion: "Overall, the structured sequencing of these learning units is designed to address the performance gaps identified in the retail industry while equipping learners with the necessary attributes to excel in their roles as machine learning professionals."
        
}}

"""

editor_message = f"""
You are to consolidate the findings without amending any of the output, mapping each agent's output to these terms accordingly.

Only 3 keys are present, Background Analysis, Performance Analysis, Sequencing Analysis. Do not aggregate any of the Validator's output, only the researching agents. Do not aggregate validator comments, those are not essential.
Your response will only be the consolidated mapped json findings, do not include any additional comments, completion notices such as "Here is the JSON mapping based on the provided context:" is not needed.

The json mapping guideline list is as follows:
{{
    "Background Analysis": {{

    }},
    "Performance Analysis": {{
        "Performance Gaps": [

        ],
        "Attributes Gained": [

        ],
        "Post-Training Benefits to Learners": [

        ]
    }},
    "Sequencing Analysis": {{
    
    "Sequencing Explanation": "",

    "LU1": {{
        "Title": "",
        "Description": ""
    }},

    "LU2": {{
        "Title": "",
        "Description": ""
    }},

    "LU3": {{
        "Title": "",
        "Description": ""
    }},

    "LU4": {{
        "Title": "",
        "Description": ""
    }},

    "Conclusion": "",

    }}
}}
"""

chat_results = user_proxy.initiate_chats(  # noqa: F704
    [
        {
            "chat_id": 1,
            "recipient": background_analyst,
            "message": background_message,
            "silent": False,
            "summary_method": "last_msg",
            "max_turns": 1,
        },
        {
            "chat_id": 2,
            # "prerequisites": [1],
            "recipient": performance_gap_analyst,
            "message": performance_gap_message,
            "silent": False,
            "summary_method": "last_msg",
            "max_turns": 1,
        },
        {
            "chat_id": 3,
            # "prerequisites": [1],
            "recipient": sequencing_rationale_agent,
            "message": sequencing_rationale_message,
            "silent": False,
            "summary_method": "last_msg",
            "max_turns": 1,
        },
        {"chat_id": 4, "prerequisites": [1, 2, 3], "recipient": editor, "silent": False, "message": editor_message, "max_turns":1},
    ]
)

editor_response = editor.last_message()["content"]
print("Printing Editor Response -----------")
print(type(editor_response))
print(editor_response)

# Step 2: Extract the JSON portion from the response
# Find the first occurrence of '{' and the last occurrence of '}'
start_index = editor_response.find('{')
end_index = editor_response.rfind('}')

if start_index != -1 and end_index != -1:
    # Extract the JSON substring
    json_string = editor_response[start_index:end_index + 1]
    print("--------- Extracted JSON String -----------")
    print(json_string)

    # Step 3: Try parsing the JSON
    try:
        parsed_output = json.loads(json_string)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        parsed_output = {}
else:
    print("No valid JSON found in the response.")
    parsed_output = {}

# Step 4: Save the parsed output to a JSON file
output_filename = 'research_output.json'
try:
    with open(output_filename, 'w') as json_file:
        json.dump(parsed_output, json_file, indent=4)
    print(f"Output saved to {output_filename}")
except IOError as e:
    print(f"Error saving JSON to file: {e}")

# Load Generated Content
with open('research_output.json', 'r') as file:
    research_output = json.load(file)

execute_justification_agent()

# Load CP Template with placeholders
with open('output_CP.json', 'r') as file:
    output_CP = json.load(file)

# Load mapping template with key:empty list pair
with open('mapping_source.json', 'r') as file:
    mapping_source = json.load(file)

# At the end, execute json_mapping.py and json_docu_replace.py
execute_json_mapping()

# Function to recursively flatten lists within the JSON structure
def flatten_json(obj):
    if isinstance(obj, dict):
        # Recursively apply to dictionary values
        return {k: flatten_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Flatten the list and apply to each element in the list
        return flatten_list(obj)
    else:
        return obj

# Function to flatten any nested list
def flatten_list(nested_list):
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))  # Recursively flatten any nested lists
        else:
            flat_list.append(item)
    return flat_list

# Load the JSON file
with open('generated_mapping.json', 'r') as file:
    gmap = json.load(file)

# Flatten the JSON
flattened_gmap = flatten_json(gmap)

# Save the flattened JSON back to the file
output_filename = 'generated_mapping.json'
try:
    with open(output_filename, 'w') as json_file:
        json.dump(flattened_gmap, json_file, indent=4)
    print(f"Output saved to {output_filename}")
except IOError as e:
    print(f"Error saving JSON to file: {e}")

execute_jinja_docu_replace('generated_mapping.json', word_template, output_docx)

print(f"All processes completed successfully. Final document saved as: {output_docx}")