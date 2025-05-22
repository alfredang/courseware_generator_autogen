from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
import json
import asyncio
import os
from dotenv import load_dotenv
from CourseProposal.model_configs import get_model_config

# performance gaps sometimes does not meet the learning outcomes
# no mention of specific industry in background information
# add in filler text in background information
# does not conflict with other sequencing

def research_task(ensemble_output):
    research_task = f"""
    IMPORTANT:
    - Your output MUST be a valid JSON object, matching the schema below EXACTLY.
    - Do NOT add any extra text, explanations, or markdown code blocks.
    - Do NOT change, add, or remove any keys or structure.
    - Do NOT include any comments or headings.
    - Before outputting, simulate running a JSON linter (e.g., json.loads()) to ensure validity.
    - If you do not follow these instructions, the process will fail.

    CORRECT EXAMPLE:
    {{
      "Background Analysis": {{ ... }},
      "Performance Analysis": {{ ... }},
      "Sequencing Analysis": {{ ... }}
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    1. Based on the extracted data from {ensemble_output}, generate your justifications.
    2. Ensure your responses are structured in JSON format.
    3. Return a full JSON object with all your answers according to the schema.
    """
    return research_task

def create_research_team(ensemble_output, model_choice: str) -> RoundRobinGroupChat:

    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)

    # insert research analysts
    background_message = f"""
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
      "Background Analysis": {{ ... }},
      "Performance Analysis": {{ ... }},
      "Sequencing Analysis": {{ ... }}
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    As a training consultant focusing on analyzing performance gaps and training needs based on course learning outcomes,
    your task is to assess the targeted sector(s) background and needs for the training. Your analysis should be structured
    clearly and based on the provided course title and industry.
    Do not use any control characters such as newlines.
    Do not mention the course name in your answer.
    Do not mention the specific industry as well, give a general answer like simply "the industry" or "the sector".

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
      "Performance Gaps": [

      ],
      "Attributes Gained": [

      ],
      "Post-Training Benefits to Learners": [

      ]
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    You are responsible for identifying the performance gaps and post-training benefits to learners that the course will address.
    Based on the extracted data, answer the following question:
    (ii) Performance gaps that the course will address for the given course title and learning outcomes: {ensemble_output.get('Course Information', {}).get('Course Title', [])}, {ensemble_output.get('Learning Outcomes', {}).get('Learning Outcomes', [])}, and proficiency level: {ensemble_output.get('Course Information', {}).get('Proficiency Level', [])}
    Do not use any control characters such as newlines.

    Your task is to perform the following:
    1. For each Learning Outcome (LO), provide one unique performance gap, one corresponding attribute gained, and one post-training benefit to learners. Do not repeat performance gaps or attributes across different LOs.
    2. However, in the event that there are only 2 Learning Outcomes, you are to provide 3 unique performance gaps and corresponding attributes gained.
    3. However, in the event that there are more than 5 Learning Outcomes, your answers are to be limited to 5 unique performance gaps and corresponding attributes gained.

    Format your response in the given JSON structure under "Performance Gaps".
    Your answer for (ii.) is to be given in a point format with three distinct sections, appended together as one list element with new line separators, this is an example with only 3 Learning Outcomes, hence 3 points each:
    {{

    Performance gaps:
    Learners are unclear with [specific skill or knowledge gap].
    (perform this analysis for the LOs)

    Attributes gained:
    Ability/Proficiency to [specific skill or knowledge learned].
    (perform this analysis for the LOs)

    Post training benefits:
    (perform this analysis for the LOs)

    }}

    An example output is as follows, you must follow the key names and structure:
    {{
    "Performance Gaps": [
      "Learners are unclear with establishing high-level structures and frameworks for Kubernetes solutions.",
      "Learners struggle to align technical, functional, and service requirements within Kubernetes-based solution architectures.",
      "Learners lack the ability to coordinate multiple Kubernetes solution components effectively.",
      "Learners find it challenging to articulate the value of Kubernetes solutions, particularly regarding coding standards and scalability.",
      "Learners do not have robust processes for monitoring and testing Kubernetes architectures against business requirements."
    ],
    "Attributes Gained": [
      "Ability to establish high-level structures and frameworks to guide the development of Kubernetes solutions.",
      "Proficiency in aligning various stakeholder requirements within a Kubernetes architecture.",
      "Skill in coordinating multiple solution components to ensure compatibility and meet design goals.",
      "Capability to articulate the value added by Kubernetes solutions to business needs.",
      "Competence in establishing processes to monitor and validate Kubernetes architectures."
    ],
    "Post-Training Benefits to Learners": [
      "Enhanced ability to design and implement effective Kubernetes solutions that meet organizational needs.",
      "Improved communication and collaboration among teams due to aligned requirements.",
      "Increased efficiency in managing Kubernetes components, leading to better application performance.",
      "Greater understanding of the importance of coding standards and scalability in Kubernetes implementations.",
      "Reduced risk of application performance issues through established monitoring and testing processes."
    ]
  }}

    """

    #sequences_intro = "For this course, the step-by-step sequencing helps learners build from foundational concepts to advanced applications relevant to the course topic."

    sequencing_rationale_message = f"""
    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - Do NOT change, add, or remove any keys or alter the structure from the schema.
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.
    - The sequencing explanation MUST start with a generic introduction sentence (e.g., 'For this course, the step-by-step sequencing helps learners acquire the necessary knowledge and skills in [course subject or skill area].').
    - Immediately after, you MUST insert a detailed, logically structured sequencing explanation (3-5 sentences) that describes:
        1. The overall framework and logic of the sequencing.
        2. How foundational knowledge is established.
        3. How each subsequent unit builds on prior knowledge.
        4. How the sequence supports mastery and real-world application.
        5. How the structure ensures alignment with the course's learning outcomes.
    - This explanation must reference the course's actual learning outcomes, units, or topics, and should demonstrate depth and breadth. Avoid shallow or formulaic summaries.
    - Then, continue with the generic follow-up sentence: 'Each learning unit (LU) is carefully positioned to lay the groundwork for the next, ensuring that learners gain the necessary knowledge and applied skills at each stage before advancing further.'
    - For each LU:
        - The LU title MUST exactly match the corresponding Learning Unit title as provided in the course JSON (e.g., from the 'Learning Units' list in 'TSC and Topics'). Do not paraphrase, abbreviate, or invent new titles. Use the exact text as the key.
        - The LU description MUST NOT repeat the LU title or include the K/A factors in the description body. Only use the title as the key.
        - Provide a detailed, multi-sentence description that:
            * References the relevant learning outcome(s), topic(s), or skill(s) addressed.
            * Explains how the unit builds on previous knowledge or prepares for subsequent units.
            * Details the real-world or pedagogical significance of the unit.
        - The description should be logically structured, rich, and similar in style to the user's provided example, but should NOT include the LU title or K/A factors in the description itself.
    - The conclusion must be multi-sentence, summarizing how the sequence supports mastery, real-world application, and alignment with learning outcomes.
    - Do NOT remove or omit the LU1, LU2, LU3, (LU4 if present), and Conclusion sections.
    - You may rephrase the LU and Conclusion sections, but always keep the required introductory and follow-up sentences at the start.
    - Do NOT add any extra text, explanations, or markdown code blocks.
    - Before outputting, simulate running a JSON linter (e.g., json.loads()) to ensure validity.
    - If you do not follow these instructions, the process will fail.

    TEMPLATE:
    {{
        "Sequencing Explanation": "For this course, the step-by-step sequencing helps learners acquire the necessary knowledge and skills in [course subject or skill area]. [Insert here: 3-5 sentence, logically structured explanation describing the overall framework, how foundational knowledge is established, how each unit builds on the previous, how the sequence supports mastery and real-world application, and how the structure ensures alignment with learning outcomes. Reference the course's actual learning outcomes, units, or topics.] Each learning unit (LU) is carefully positioned to lay the groundwork for the next, ensuring that learners gain the necessary knowledge and applied skills at each stage before advancing further.",
        "LU1": {{
            "Title": "[Exact title of LU1 from the course JSON]",
            "Description": "LU1 directly supports [LO1 or relevant outcome] by [establishing/introducing] [key concepts, skills, or frameworks]. The topics in this unit cover [briefly list or describe topics/skills], which are essential before [next stage or application]. Applied components such as [practical activities, frameworks, or tools] equip learners with [capabilities or understanding]. This unit ensures that learners develop a complete baseline, which is critical for progressing to subsequent units."
        }},
        "LU2": {{
            "Title": "[Exact title of LU2 from the course JSON]",
            "Description": "LU2 builds on the foundation of LU1 and addresses [LO2 or relevant outcome] by guiding learners through [frameworks, requirements, or skills]. With foundational knowledge already established, learners are now equipped to [explore/apply] [new topics, skills, or challenges]. This step is essential before [next stage or application]. The progression into [advanced topics or skills] allows learners to develop practical skills in [area]. This stage ensures learners can [apply/interpet] [knowledge/skills] while considering broader goals."
        }},
        "LU3": {{
            "Title": "[Exact title of LU3 from the course JSON]",
            "Description": "LU3 builds on the grounding in LU2 and supports [LO3 or relevant outcome]. At this stage, learners are prepared to [apply/operationalise] [key skills or concepts] by first understanding [critical concepts or systems]. This logical next step ensures the learner can [contextualise/apply] [knowledge/skills] in [real-world or advanced context]. The unit progresses to [advanced methodologies or applications], which are critical before [final stage or application]. These steps are sequenced deliberately to ensure that [outcomes/strategies] are based on [accurate, system-wide understanding], reinforcing sound planning and mastery."
        }},
        "[Repeat for LU4, LU5, etc. as needed, following the same structure as LU1, LU2, LU3, ensuring the key is like \"LU4\", \"LU5\", etc.]": {{
            "Title": "[Exact title of the LU from the course JSON]",
            "Description": "[Detailed description for this LU, similar to others]"
        }},
        "Conclusion": "The structured sequencing of these learning units ensures that learners develop a coherent and comprehensive understanding of [course subject or skill area]. By progressing from foundational principles to advanced applications, each unit builds on the previous, supporting mastery, real-world application, and alignment with the course's learning outcomes and industry or professional standards."
    }}

    CORRECT EXAMPLE:
    {{
        "Sequencing Explanation": "For this course, the step-by-step sequencing helps learners acquire the necessary knowledge and skills in data analytics and decision-making. The framework begins with essential knowledge of data structures and methodically builds toward advanced application in predictive modeling, business intelligence, and finally, the formulation of actionable strategies. Each learning unit (LU) is carefully positioned to lay the groundwork for the next, ensuring that learners gain the necessary knowledge and applied skills at each stage before advancing further. This systematic sequencing ensures alignment with the course's learning outcomes and supports mastery at each critical phase of data-driven problem solving.",
        "LU1": {{
            "Title": "Foundations of Data Structures and Management",
            "Description": "LU1 directly supports LO1 by establishing a technical and conceptual foundation for data analytics. The topics in this unit introduce core principles of data types, storage, and retrieval, as well as best practices for data integrity and security. These foundational concepts are necessary before any analysis or modeling can be introduced. Applied components such as database design and data cleaning equip learners with the capability to manage and prepare data for analysis. This unit ensures that learners develop a complete baseline understanding, which is critical for progressing to analytical and modeling aspects."
        }},
        "LU2": {{
            "Title": "Analytical Methods and Business Intelligence",
            "Description": "LU2 builds on the foundation of LU1 and addresses LO2 by guiding learners through analytical frameworks and business intelligence tools. With foundational knowledge already established, learners are now equipped to explore data visualization, reporting, and dashboard creation. This step is essential before predictive modeling or strategic decision-making can be conducted. The progression into interpreting business metrics and identifying trends allows learners to develop practical skills in business intelligence. This stage ensures learners can interpret and apply analytics while considering broader organizational goals."
        }},
        "LU3": {{
            "Title": "Predictive Modeling and Strategic Application",
            "Description": "LU3 builds on the analytical grounding in LU2 and supports LO3. At this stage, learners are prepared to operationalize predictive modeling by first understanding statistical methods and machine learning algorithms. This logical next step ensures the learner can contextualize predictions within business scenarios. The unit progresses to model evaluation and deployment, which are critical before actionable strategies can be formulated. These steps are sequenced deliberately to ensure that strategies are based on accurate, data-driven insights, thus reinforcing sound decision-making and planning."
        }},
        "Conclusion": "The structured sequencing of these learning units ensures that learners develop a coherent and comprehensive understanding of data analytics and decision-making. By progressing from foundational principles to advanced applications, each unit builds on the previous, supporting mastery, real-world application, and alignment with the course's learning outcomes and industry standards."
    }}
    """

    editor_message = f"""
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
        "Background Analysis": {{ ... }},
        "Performance Analysis": {{ ... }},
        "Sequencing Analysis": {{ ... }}
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

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

    background_analyst = AssistantAgent(
        name="background_analyst",
        model_client=model_client,
        system_message=background_message,
    )

    performance_gap_analyst = AssistantAgent(
        name="performance_gap_analyst",
        model_client=model_client,
        system_message=performance_gap_message
    )

    sequencing_rationale_agent = AssistantAgent(
        name="sequencing_rationale_agent",
        model_client=model_client,
        system_message=sequencing_rationale_message,
    )

    editor = AssistantAgent(
        name="editor",
        model_client=model_client,
        system_message=editor_message,
    )

    research_group_chat = RoundRobinGroupChat([background_analyst, performance_gap_analyst, sequencing_rationale_agent, editor], max_turns=4)

    return research_group_chat