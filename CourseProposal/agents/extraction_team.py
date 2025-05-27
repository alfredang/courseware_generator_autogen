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
    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - Do NOT change, add, or remove any keys or alter the structure from the schema.
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.

    CORRECT EXAMPLE:
    {{
    "Course Information": {{
        "Course Title": "",
        ...
    }},
    ...
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    You are to extract the following variables from {data}:
            1) Course Title
            2) Name of Organisation
            3) Course Level (e.g. Beginners, Beginner, Beginner to Intermediate, Intermediate, Intermediate to Advanced, Advanced)
            4) Proficiency Level (e.g., Basic, Intermediate, Advanced, or a number from 1 to 6)
            5) Classroom Hours (can be found under Instructional Duration: xxxx)
            6) Practical Hours (IMPORTANT: should match the Number of Assessment Hours exactly)
            7) Number of Assessment Hours (can be found under Assessment Duration: xxxx)
            8) Course Duration (Number of Hours)
            9) Industry

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
                'CST': 'Carbon Services and Trading'



            }}
            Format the extracted data in JSON format, with this structure, do NOT change the key names or add unnecessary spaces:
                "Course Information": {{
                "Course Title": "",
                "Course Level": "",  # Accept values like 'Beginners', 'Beginner', 'Beginner to Intermediate', etc. 'Beginners' will be normalized to 'Beginner' in the Excel pipeline.
                "Proficiency Level": "",  # Accept values 1-6 or text labels as found. Do not convert numbers to labels.
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
    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - The output JSON object MUST have a single top-level key: `"Learning Outcomes"`.
    - Under the `"Learning Outcomes"` key, there MUST be exactly three sub-keys: `"Learning Outcomes"` (a list of strings), `"Knowledge"` (a list of strings), and `"Ability"` (a list of strings).
    - These three sub-keys (`"Learning Outcomes"`, `"Knowledge"`, `"Ability"`) MUST ALWAYS be present, even if their corresponding lists are empty (e.g., if no relevant knowledge points are found, you MUST output `"Knowledge": []`).
    - Do NOT add any other keys at the top level, or under the main `"Learning Outcomes"` object, other than the three specified sub-keys.
    - Do NOT change, add, or remove any keys or alter the structure from the schema (other than populating the lists).
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.

    CORRECT EXAMPLE:
    {{
    "Learning Outcomes": {{
        "Learning Outcomes": [

        ],
        "Knowledge": [

        ],
        "Ability": [
        ]
    }},
    ...
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    You are to extract the following variables from {data}:
            1) Learning Outcomes, include the terms LO(x): in front of each learning outcome
            2) Knowledge
            3) Ability

            Text Blocks which start with K or A and include a semicolon should be mapped under Knowledge (for K) and Ability (for A).

            An example output is as follows:
            "Learning Outcomes":  ["LO1: Calculate profitability ratios to assess an organization's financial health.", "LO2: Calculate performance ratios to evaluate an organization's overall financial performance."], 
            "Knowledge": ["K1: Ratios for profitability\nK2: Ratios for performance"], 
            "Ability": ["A1: Calculate ratios for assessing organisation's profitability\nA2: Calculate ratios for assessing organisation's financial performance"], 


            Format the extracted data in JSON format, with this structure. The top-level `"Learning Outcomes"` key IS REQUIRED. 
            Under this, the sub-keys `"Learning Outcomes"` (list), `"Knowledge"` (list), and `"Ability"` (list) MUST ALWAYS be present, even if empty:
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
    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - Do NOT change, add, or remove any keys or alter the structure from the schema.
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.

    CORRECT EXAMPLE:
    {{
    "TSC and Topics": {{
        "TSC Title": [

        ],
        "TSC Code": [

        ],
        "Topics": [

        ],
        "Learning Units": [

        ]
    }},
    ...
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    You are to extract the following variables from {data}:
            1) TSC Title
            2) TSC Code
            3) Topic (include the FULL string, including any K's and A's, only include items starting with "Topic" and not "LU" for this particular point)
            4) Learning Units (IMPORTANT: extract the EXACT original LU names as they appear in the data, do NOT paraphrase or modify them in any way. Include the full LU string with any brackets/K&A mappings)

        An example output is as follows:
        "TSC Title": "Financial Analysis",
        "TSC Code": "ACC-MAC-3004-1.1",
        "Topic": ["Topic 1 Assessing Organization's Profitability (K1, A1)", "Topic 2 Evaluating an Organization's Performance Using Ratio Analysis (K2, A2)"],
        "Learning Units": ["LU1: Storytelling with Generative AI", "LU2: Storyboarding with Generative AI"]

        Format the extracted data in JSON format, with this structure:
            "TSC and Topics": {{
            "TSC Title": [
                
            ],
            "TSC Code": [
                
            ],
            "Topic": [

            ],
            "Learning Units": [

            ]
        }}
    """

    assessment_methods_extractor_message = f"""
    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - Do NOT change, add, or remove any keys or alter the structure from the schema.
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.
    - For instructional methods, output the method names EXACTLY as they appear in the input. Do NOT paraphrase, modify, or wrap them in 'Others: ...'. The mapping to dropdown or 'Others: [value]' will be handled downstream in the pipeline. Do NOT change 'practice' to 'practical' or vice versa. Use the exact term as extracted from the source.
    - For assessment methods, if the method is not in the dropdown list, output as 'Others: [method]'. If the method is in the dropdown, use the dropdown value exactly. This ensures unknown methods are handled robustly and the JSON output will not break the Excel pipeline.

    CORRECT EXAMPLE:
    {{
    "Assessment Methods": {{
        "Assessment Methods": [
            "",
            ""
        ],
        "Amount of Practice Hours": Insert the exact same number as the Number of Assessment Hours,
        "Course Outline": {{
            "Learning Units": {{
                "LU1": {{
                    "Description": [
                        {{
                            "Topic": "Topic 1: Empathize and Define (K1, A1)",
                            "Details": [
                                "Techniques for understanding user needs",
                                "Methods for defining clear problem statements",
                                "Exercises: Empathy mapping and problem definition",
                                "Case studies of successful user-centered design",
                                "Tools and frameworks for identifying user pain points"
                            ]
                        }},
                        {{
                            "Topic": "Topic 2: Ideate and Prototype (K2, A2)",
                            "Details": [
                                "Strategies for brainstorming and generating creative solutions",
                                "Steps to create and refine prototypes",
                                "Activities: Brainstorming sessions and prototyping workshops",
                                "Evaluation methods for prototype testing",
                                "Digital and physical prototyping techniques"
                            ]
                        }},
                        {{
                            "Topic": "Topic 3: Test and Iterate (K3, A3)",
                            "Details": [
                                "Importance of gathering user feedback",
                                "Methods for testing and iterating solutions",
                                "Workshops: Testing prototypes and iterative improvements",
                                "Metrics for measuring solution effectiveness",
                                "Strategies for continuous improvement cycles"
                            ]
                        }}                    
                        ]
                    }}
                }}
            }}
        Instructional Methods: ""
        }}
    }}

    You are to extract the following variables from {data}:
            1) Assessment Methods (remove the brackets and time values at the end of each string)
            2) Instructional Methods
            3) Amount of Practice Hours - IMPORTANT: this should EXACTLY match the Number of Assessment Hours from the data
            4) Course Outline, which consists of Learning Units (LUs), Topics under that Learning Unit and their descriptions. A Learning Unit may have more than 1 topic, so nest that topic and its relevant descriptions under that as well.

            Include the full topic names in Course Outline, including any bracketed K and A factors.
            
            IMPORTANT: For each topic, auto-generate 3-5 detailed bullet points as "Details" that would likely be covered in that topic based on the topic name and K/A factors. These details should be specific, practical, and relevant to the course content.

            Format the extracted data in JSON format, with this structure:
                "Assessment Methods": {{
                "Assessment Methods": [
                    "",
                    ""
                ],
                "Amount of Practice Hours": Insert the exact same number as the Number of Assessment Hours,
                "Course Outline": {{
                    "Learning Units": {{
                        "LU1": {{
                            "Description": [
                                {{
                                    "Topic": "Topic 1: Empathize and Define (K1, A1)",
                                    "Details": [
                                        "Techniques for understanding user needs",
                                        "Methods for defining clear problem statements",
                                        "Exercises: Empathy mapping and problem definition",
                                        "Case studies of successful user-centered design",
                                        "Tools and frameworks for identifying user pain points"
                                    ]
                                }},
                                {{
                                    "Topic": "Topic 2: Ideate and Prototype (K2, A2)",
                                    "Details": [
                                        "Strategies for brainstorming and generating creative solutions",
                                        "Steps to create and refine prototypes",
                                        "Activities: Brainstorming sessions and prototyping workshops",
                                        "Evaluation methods for prototype testing",
                                        "Digital and physical prototyping techniques"
                                    ]
                                }},
                                {{
                                    "Topic": "Topic 3: Test and Iterate (K3, A3)",
                                    "Details": [
                                        "Importance of gathering user feedback",
                                        "Methods for testing and iterating solutions",
                                        "Workshops: Testing prototypes and iterative improvements",
                                        "Metrics for measuring solution effectiveness",
                                        "Strategies for continuous improvement cycles"
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
    
    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - Do NOT change, add, or remove any keys or alter the structure from the schema.
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.

    Return the combined output into a single JSON file, do not alter the keys in any way, do not add or nest any keys. Ensure that the following is adhered to:
    1. **Strict JSON Formatting:**  
    - The output must be a valid JSON object with proper syntax (keys in double quotes, commas separating elements, arrays enclosed in square brackets, objects enclosed in curly braces).
    
    2. **Schema Compliance:**  
    The JSON must include the following top-level keys:  
    - `"Course Information"`  
    - `"Learning Outcomes"`  
    - `"TSC and Topics"`  
    - `"Assessment Methods"` 
     
    If data for a section (e.g., from `learning_outcomes_extractor`) is missing or invalid, you MUST still include its corresponding top-level key (e.g., `"Learning Outcomes"`) in your output. For such cases, use a default empty structure for that key (e.g., `"Learning Outcomes": {{"Learning Outcomes": [], "Knowledge": [], "Ability": []}}` or an empty object `{{}}` if the detailed structure is unknown or too complex to default).
    
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