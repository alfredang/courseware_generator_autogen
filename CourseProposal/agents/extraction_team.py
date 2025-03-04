from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv
from CourseProposal.model_configs import get_model_config

load_dotenv()


def extraction_task(data):
    extraction_task = f"""
    1. Extract data from the following JSON file: {data}
    2. Map the extracted data according to the schemas.
    3. Return a full JSON object with all the extracted data according to the schema.
    """
    return extraction_task

def create_extraction_team(data, model_choice: str) -> RoundRobinGroupChat:
    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)
    course_info_extractor_message = f"""
    You are to extract the following variables from {data}:
        1) Course Title
        2) Name of Organisation
        3) Classroom Hours
        4) Practical Hours (if none found, insert 0)
        5) Number of Assessment Hours
        6) Course Duration (Number of Hours)
        7) Industry

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
            "Practical Hours": ,
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
    """

    tsc_and_topics_extractor_message = f"""
    You are to extract the following variables from {data}:
        1) TSC Title
        2) TSC Code
        3) Topic (include the FULL string, including any K's and A's, only include items starting with "Topic" and not "LU" for this particular point)
        4) Learning Units (do NOT include Topics under this point, do NOT include any brackets consisting of A's or K's), only include items starting with "LU".

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
    Return the combined output into a single JSON file, do not alter the keys in any way, do not add or nest any keys. Ensure that the following is adhered to:
    1. **Strict JSON Formatting:**  
    - The output must be a valid JSON object with proper syntax (keys in double quotes, commas separating elements, arrays enclosed in square brackets, objects enclosed in curly braces).
    
    2. **Schema Compliance:**  
    The JSON must include the following top-level keys:  
    - `"Course Information"`  
    - `"Learning Outcomes"`  
    - `"TSC and Topics"`  
    - `"Assessment Methods"`  
    
    3. **No Trailing Commas or Missing Brackets:**  
    - Ensure that each array (`[...]`) and object (`{{...}}`) is closed properly.  
    - Do not leave trailing commas.  

    4. **Consistent Key Names:**  
    - Use consistent and properly spelled keys as specified.  

    5. **Always Validate Before Output:**  
    - Run a JSON lint check (or a `json.loads()` equivalent if you are simulating code) before returning the final JSON.  
    
    6. **Error Handling:**  
    If you detect an issue in the JSON (e.g., missing commas, brackets, or improper formatting), correct it immediately before providing the output.

    7. **Output Format:**  
    Return only the JSON object and no additional commentary.
    """

    course_info_extractor = AssistantAgent(
        name="course_info_extractor",
        model_client=model_client,
        system_message=course_info_extractor_message,
    )

    learning_outcomes_extractor = AssistantAgent(
        name="learning_outcomes_extractor",
        model_client=model_client,
        system_message=learning_outcomes_extractor_message,
    )

    tsc_and_topics_extractor = AssistantAgent(
        name="tsc_and_topics_extractor",
        model_client=model_client,
        system_message=tsc_and_topics_extractor_message,
    )

    assessment_methods_extractor = AssistantAgent(
        name="assessment_methods_extractor",
        model_client=model_client,
        system_message=assessment_methods_extractor_message,
    )

    aggregator = AssistantAgent(
        name="aggregator",
        model_client=model_client,
        system_message=aggregator_message,
    )

    extraction_group_chat = RoundRobinGroupChat([course_info_extractor, learning_outcomes_extractor, tsc_and_topics_extractor, assessment_methods_extractor, aggregator], max_turns=5)

    return extraction_group_chat