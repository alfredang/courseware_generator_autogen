from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
import json
import asyncio
import os
from dotenv import load_dotenv
from CourseProposal.model_configs import get_model_config
from autogen_agentchat.ui import Console

def course_task():
    overview_task = f"""
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
      "course_overview": {{
        "course_description": "..."
      }}
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    1. Based on the provided data, generate your justifications.
    2. Ensure your responses are structured in JSON format.
    3. Return a full JSON object with all your answers according to the schema.
    """
    return overview_task

def ka_task():
    overview_task = f"""
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
      "KA_Analysis": {{
        "K1": "...",
        "A1": "..."
      }}
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    1. Based on the provided data, generate your justifications, ensure that ALL the A and K factors are addressed.
    2. Ensure your responses are structured in JSON format.
    3. Return a full JSON object with all your answers according to the schema.
    """
    return overview_task

def im_task():
    im_task = f"""
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
    - If the instructional or assessment method is Case Study, output as 'Others: Case Study' (not 'Others: [Please elaborate]').
    - Add 'Others: Case Study' to the dropdown options and use this format for Case Study.

    CORRECT EXAMPLE:
    {{
      "Instructional_Methods": {{
        "Lecture": "...",
        "Didactic Questioning": "..."
      }}
    }}

    INCORRECT EXAMPLES (do NOT do this):
    ```json
    {{ ... }}
    ```
    Here is your JSON: {{ ... }}
    Any output with extra text, markdown, or missing/extra keys is invalid.

    1. Based on the provided data, generate your justifications, ensure that the instructional methods are addressed.
    2. Ensure your responses are structured in JSON format.
    3. Return a full JSON object with all your answers according to the schema.
    """
    return im_task

def create_course_agent(ensemble_output, model_choice: str) -> RoundRobinGroupChat:

    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)

    # use ensemble output for the new factors
    # insert research analysts
    about_course_message = f"""
    As a digital marketing consultant, your primary role is to assist small business owners in optimizing their websites for SEO and improving their digital marketing strategies to enhance lead generation. You should provide clear, actionable advice tailored to the challenges and opportunities typical for small businesses. Focus on offering strategies that are feasible and effective for smaller budgets and resources. Stay abreast of the latest SEO and digital marketing trends, ensuring your advice is current and practical. When necessary, ask for clarification to understand the specific needs of each business, but also be proactive in filling in general small business scenarios. Personalize your responses to reflect an understanding of the unique dynamics and constraints small businesses face in digital marketing.
    You will do so based on the course title, learning outcomes (LOs), and the Topics found in {ensemble_output}

    YOUR OUTPUT MUST BE DETAILED AND SUBSTANTIAL:
    - Your course description MUST be at least **8 sentences** and at least **2 paragraphs**.
    - You MUST explicitly cover ALL of the following: (1) value and skills gained, (2) industry relevance, (3) career impact, (4) real-world application/examples, (5) both technical and soft/strategic skills.
    - If your output is under 8 sentences, or lacks any of these details, it will be rejected and you will be asked to try again.
    - Each paragraph should be at least 4 sentences. Avoid short, generic, or repetitive content.
    - Use concrete examples, scenarios, or applications relevant to the course domain.
    - Your language must be persuasive, specific, and tailored to the course context.
    - Do NOT copy the template or example verbatim. Vary your sentence structure, paragraph flow, and adapt your style to the course context. Your output should be natural, engaging, and tailored, not formulaic.

    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - Do NOT change, add, or remove any keys or alter the structure from the schema.
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.

    There is no strict word limit. Your description should be as detailed as necessary to fully convey the course's value, industry relevance, and career impact. Your course description should be detailed and persuasive, typically between 6 and 12 sentences. Focus on substance and clarity, not unnecessary length.
    Go beyond a basic summary:
        - Highlight the specific skills, competencies, and needs the course addresses.
        - Clearly explain how the course is relevant to current industry trends, standards, and challenges.
        - Discuss how the course can impact a learner's career, including opportunities for employment, job upgrading, or specialization.
        - Provide concrete examples or scenarios of how the skills will be applied in real-world contexts.
        - Address both technical and strategic/soft skills developed in the course.
    Avoid repeating phrases or ideas. Vary your sentence structure and ensure each paragraph adds new information or perspective.
    Your output should be natural, engaging, and tailored to the course context, not formulaic.

    - Your course description must begin with the phrase: "This course equips learners with the [proficiency level] competencies required to..." (e.g., "This course equips learners with the basic competencies required to design and implement effective data visualizations using Tableau Desktop.")
    - The final sentence of your description must clearly state the course level, using the value from the input JSON, in the format: "This course is at a [course level] level, designed for [target audience/sector]." (e.g., "This course is at a beginner level, designed for professionals seeking to enhance their data presentation skills in the Infocomm Technology sector.")
    - Your course description should be detailed and persuasive, typically between 6 and 12 sentences. Focus on substance and clarity, not unnecessary length.
    - The course level (e.g., Beginner, Intermediate, Advanced, Beginner to Intermediate, Intermediate to Advanced) MUST be clearly stated in the course description, using the value from the input JSON (ensemble_output['Course Information']['Course Level']).
    - The proficiency level (e.g., Basic, Intermediate, Advanced) MUST be clearly stated in the course description, using the value from the input JSON (ensemble_output['Course Information']['Proficiency Level']).
    - Do NOT guess or default the course level or proficiency level; always use the provided values.
    - Your output MUST be a valid JSON object, matching the schema below EXACTLY.
    - Do NOT add any extra text, explanations, or markdown code blocks.
    - Do NOT change, add, or remove any keys or structure.
    - Do NOT include any comments or headings.
    - Before outputting, simulate running a JSON linter (e.g., json.loads()) to ensure validity.
    - If you do not follow these instructions, the process will fail.

    You must start your answer with "This course"
    You must take into consideration the learning outcomes and topics for the Course Description.
    Do not mention the course name in your answer.
    Do not mention the LOs in your answer.
    Do not add quotation marks in your answer.

    As a consultant, your primary goal is to articulate the value proposition of this course. Your language should be clear, engaging, and professional, avoiding unnecessary jargon. The description needs to be easily digestible, persuasive, and tailored to the target audience, reflecting a good Flesch Reading Ease score.

    Emphasize and clearly address these key aspects in the body of your description:
    1.  **Value & Skills:** Clearly detail the tangible benefits, new skills, and core competencies learners will acquire. Explain what specific needs this course fulfills for them.
    2.  **Industry & Career:** Explain the course's relevance to the current industry landscape. Specifically, discuss how it can impact a learner's career, including employment prospects and opportunities for job upgrading or specialization.
    3.  **Audience & Level:** Clearly state the course level (e.g. Beginner to Intermediate, Intermediate to Advanced) using the provided input. The proficiency level (e.g., Basic, Intermediate, Advanced) from the input JSON MUST be stated at the beginning of the course description.

    Your course description must be at least 8 sentences long, multi-paragraph, and as detailed as the example provided. It must adapt terminology, standards, frameworks, and real-world applications to the actual course subject area (e.g., technology, healthcare, finance, engineering, etc.).

    Use the following TEMPLATE as a *guideline* to structure your response, infusing your consultant expertise to make it dynamic and compelling. Ensure all placeholders are adapted to the specific course domain and details.

    TEMPLATE (ADAPT TO THE COURSE DOMAIN):
    This course equips learners with the [proficiency level] competencies required to design and implement robust [domain/subject] systems in alignment with [relevant standard or framework, e.g., ISO 14064-1:2018, HIPAA, IFRS, etc.]. Participants will explore foundational principles of [subject] and its alignment with [science-based targets, industry standards, or global reporting requirements]. By engaging with real-world scenarios and case studies, learners will gain a practical understanding of how these principles are applied in leading organizations. Through practical engagement with [risk-informed planning, data analysis, compliance strategies, or other key activities], learners will develop the ability to ensure [regulatory compliance, operational excellence, or other domain-relevant goals] and integrate efforts into broader [organizational, industry, or societal] frameworks. The curriculum is designed to foster both technical expertise and strategic thinking, preparing participants to address complex challenges in their field.
    A key focus of the course is operationalizing [core skill or process, e.g., emissions reduction, patient care, financial reporting] across [systems, supply chains, teams, etc.] using [lifecycle methodologies, data analysis, baseline assessments, etc.]. Learners will also gain critical skills in [specialized area, e.g., offset planning, clinical decision-making, risk management], including how to [define scopes, apply key metrics, formulate strategies] that are [economically viable, evidence-based, or optimized for the domain]. Interactive workshops and collaborative projects will enable participants to apply new knowledge in simulated professional contexts. The course delivers real-world applications that prepare participants to drive measurable impact within their organizations.

    With [global regulatory and investor scrutiny, or industry trends] intensifying around [key challenge, e.g., climate accountability, data privacy, patient safety], this course provides essential upskilling for professionals engaged in [relevant roles or sectors]. The program addresses both current and emerging issues, ensuring that graduates remain adaptable in a rapidly evolving landscape. Proficiency in [relevant standard or practice] significantly enhances employability across diverse industries by equipping learners with the tools to [quantify, report, improve, or comply]. Graduates of this course will be well-positioned to pursue career advancement,
    transition into specialized roles, or support companies in meeting [industry or regulatory] goals. Alumni often find themselves at the forefront of innovation, leading initiatives that shape the future of their professions.

    This course is at a(n) [course level] level, designed for [target audience, e.g., professionals, managers, practitioners] who have a foundational understanding of [relevant background] and are seeking to deepen their expertise in [subject area or skill]. Participants are encouraged to bring their own professional experiences into the learning environment, enriching discussions and fostering a vibrant community of practice.

    EXAMPLE (HEALTHCARE DOMAIN):
    This course equips learners with the advanced competencies required to design and implement robust patient data management systems in alignment with HIPAA and global healthcare data standards. Participants will explore foundational principles of healthcare informatics and its alignment with patient safety, privacy regulations, and international reporting requirements. Through a blend of lectures and hands-on labs, students will see how informatics principles are applied in hospitals and clinics worldwide. Through practical engagement with risk-informed planning, clinical data analysis, and compliance strategies, learners will develop the ability to ensure regulatory compliance and integrate data management efforts into broader hospital and healthcare system frameworks. The curriculum emphasizes both the technical and ethical dimensions of healthcare data, preparing participants to navigate complex regulatory environments.
    A key focus of the course is operationalizing secure patient data handling across clinical departments and care teams using lifecycle methodologies, data analysis, and baseline assessments. Learners will also gain critical skills in clinical decision support, including how to define data scopes, apply key healthcare metrics, and formulate strategies that are evidence-based and optimized for patient outcomes. Group projects and scenario-based exercises will help participants translate theory into practice, simulating the challenges faced by healthcare professionals. The course delivers real-world applications that prepare participants to drive measurable improvements in patient care and data security within their organizations.

    With global regulatory and public scrutiny intensifying around patient privacy and healthcare data security, this course provides essential upskilling for professionals engaged in healthcare management,
    clinical informatics, and digital health transformation. The program is regularly updated to reflect the latest trends and compliance requirements, ensuring its ongoing relevance. Proficiency in HIPAA and related standards significantly enhances employability across diverse healthcare settings by equipping learners with the tools to quantify, report, and improve patient data practices. Graduates of this course will be well-positioned to pursue career advancement, transition into informatics-focused roles, or support organizations in meeting compliance and patient safety goals. Many alumni have gone on to lead digital transformation projects or serve as data governance champions in their institutions.

    This course is at an intermediate level, designed for healthcare professionals who have a foundational understanding of clinical systems or patient care and are seeking to deepen their expertise in healthcare informatics and data strategy. Learners from a variety of backgrounds are welcomed, and peer-to-peer learning is encouraged to maximize the value of diverse perspectives.

    ---
    Your output must match this level of detail, specificity, and structure, using the actual course data provided. If the course is in a different domain, adapt the terminology and details to that domain, referencing relevant standards, frameworks, and real-world applications.


    Format your response in the given JSON structure under "course_overview".
    Your output MUST be as follows, with course_description being the only key-value pair under "course_overview":
    "course_overview": {{
        course_description: "Your course description here",
        }}
    """

    validation_message = f"""
    Your only purpose is to ensure that the output from the previous agent STRICTLY matches the json schema provided below.
    It must not have any other keys other than the ones specified in the below example.
    Your output must take the content of the previous agent and ensure that it is structured in the given JSON format.

    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - Do NOT change, add, or remove any keys or alter the structure from the schema.
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.

    Do not have more than 1 key value pair under "course_overview", and that key value pair must be "course_description".


    Format your response in the given JSON structure under "course_overview".
    Your output MUST be as follows, with course_description being the only key-value pair under "course_overview":
    "course_overview": {{
        course_description: "Generated content from previous agent",
        }}
    """

    course_agent = AssistantAgent(
        name="course_agent",
        model_client=model_client,
        system_message=about_course_message,
    )

    course_agent_validator = AssistantAgent(
    name="course_agent_validator",
    model_client=model_client,
    system_message=validation_message,
    )

    course_agent_chat = RoundRobinGroupChat([course_agent, course_agent_validator], max_turns=2)

    return course_agent_chat

def create_ka_analysis_agent(ensemble_output, instructional_methods_data, model_choice: str) -> RoundRobinGroupChat:

    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)

    # instructional_methods_data = create_instructional_dataframe()
    ka_analysis_message = f"""
    You are responsible for elaborating on the appropriateness of the assessment methods in relation to the K and A statements. For each LO-MoA (Learning Outcome - Method of Assessment) pair, input rationale for each on why this MoA was chosen, and specify which K&As it
    pair, input rationale for each on why this MoA was chosen, and specify which K&As it will assess.

    The data provided which contains the ensemble of K and A statements, and the Learning Outcomes and Methods of Assessment, is in this dataframe: {instructional_methods_data}
    For each explanation, you are to provide no more than 50 words. Do so for each A and K factor present.
    Your response should be structured in the given JSON format under "KA_Analysis".
    Full list of K factors: {ensemble_output.get('Learning Outcomes', {}).get('Knowledge', [])}
    Full list of A factors: {ensemble_output.get('Learning Outcomes', {}).get('Ability', [])}
    Ensure that ALL of the A and K factors are addressed.
    Only use the first 2 characters as the key names for your JSON output, like K1 for example. Do not use the full A and K factor description as the key name.
    
    IMPORTANT: Use the exact assessment method terminology:
    - "Written Exam" (not "Written Assessment")  
    - "Practical Exam" (not "Practical Performance")

    Do not mention any of the Instructional Methods directly.
    K factors must address theory and knowledge, while A factors must address practical application and skills, you must reflect this in your analysis.

    Follow the suggested answer structure shown below, respective to A and K factors.
    For example:
    KA_Analysis: {{
    K1: "The candidate will respond to a series of [possibly scenario based] short answer questions related to: ",
    A1: "The candidate will perform [some form of practical exercise] on this [topic] and submit [materials done] for: ",
    K2: "explanation",
    A2: "explanation",
    ...
    (and so on for however many A and K factors)
    }}

    """

    ka_analysis_agent = AssistantAgent(
        name="ka_analysis_agent",
        model_client=model_client,
        system_message=ka_analysis_message,
    )

    ka_analysis_chat = RoundRobinGroupChat([ka_analysis_agent], max_turns=1)

    return ka_analysis_chat

def create_instructional_methods_agent(ensemble_output, instructional_methods_json, model_choice: str) -> RoundRobinGroupChat:

    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)

    # instructional_methods_data = create_instructional_dataframe()
    im_analysis_message = f"""
    You are responsible for contextualising the explanations of the chosen instructional methods to fit the context of the course. 
    You will take the template explanations and provide a customised explanation for each instructional method.
    Your response must be structured in the given JSON format under "Instructional_Methods".
    Focus on explaining why each of the IM is appropriate and not just on what will be done using the particular IM.
    Do not mention any A and K factors directly.
    Do not mention any topics directly.
    Do not mention the course name directly.

    IMPORTANT:
    - Your ENTIRE output MUST be a single, raw JSON object.
    - Do NOT enclose it in markdown ```json ... ``` blocks.
    - Do NOT add any introductory text, explanations, or concluding remarks before or after the JSON.
    - The JSON object MUST strictly match the schema and examples provided.
    - Do NOT change, add, or remove any keys or alter the structure from the schema.
    - Do NOT include any comments or headings within the JSON.
    - CRITICAL: Before outputting, rigorously check your response to ensure it is a perfectly valid JSON object. Imagine it will be directly parsed by a `json.loads()` function.
    - Failure to adhere to these strict JSON formatting rules will cause the entire process to fail. Accuracy is paramount.

    Your response should be structured in the given JSON format under "Instructional_Methods".
    The following JSON output details the course, and the full list of chosen instructional methods can be found under the Instructional Methods key: {ensemble_output}
    Full list of template answers for the chosen instructional methods: {instructional_methods_json}

    Do not miss out on any of the chosen instructional methods.
    The key names must be the exact name of the instructional method, and the value must be the explanation.

    For example:
    Instructional_Methods: {{
    Lecture: "",
    Didactic Questioning: "",
    ...
    }}

    """

    instructional_methods_agent = AssistantAgent(
        name="instructional_methods_agent",
        model_client=model_client,
        system_message=im_analysis_message,
    )

    im_analysis_chat = RoundRobinGroupChat([instructional_methods_agent], max_turns=1)

    return im_analysis_chat

# async def run_excel_agents():
#     # Load the existing research_output.json
#     with open('json_output/research_output.json', 'r', encoding='utf-8') as f:
#         research_output = json.load(f)

#     course_agent = create_course_agent(research_output, model_choice=model_choice)
#     stream = course_agent.run_stream(task=overview_task)
#     await Console(stream)

#     course_agent_state = await course_agent.save_state()
#     with open("json_output/course_agent_state.json", "w") as f:
#         json.dump(course_agent_state, f)
#     course_agent_data = extract_final_agent_json("json_output/course_agent_state.json")  
#     with open("json_output/excel_data.json", "w", encoding="utf-8") as f:
#         json.dump(course_agent_data, f)  

#     # K and A analysis pipeline
#     instructional_methods_data = create_instructional_dataframe()
#     ka_agent = create_ka_analysis_agent(instructional_methods_data, model_choice=model_choice)
#     stream = ka_agent.run_stream(task=overview_task)
#     await Console(stream)
#     #TSC JSON management
#     state = await ka_agent.save_state()
#     with open("json_output/ka_agent_state.json", "w") as f:
#         json.dump(state, f)
#     ka_agent_data = extract_final_agent_json("json_output/ka_agent_state.json")
#     with open("json_output/excel_data.json", "w", encoding="utf-8") as out:
#         json.dump(ka_agent_data, out, indent=2)

# if __name__ == "__main__":
    # # Load the existing research_output.json
    # with open('json_output/research_output.json', 'r', encoding='utf-8') as f:
    #     research_output = json.load(f)

    # course_agent = create_course_agent(research_output, model_choice=model_choice)
    # stream = course_agent.run_stream(task=overview_task)
    # await Console(stream)

    # course_agent_state = await course_agent.save_state()
    # with open("json_output/course_agent_state.json", "w") as f:
    #     json.dump(course_agent_state, f)
    # course_agent_data = extract_final_agent_json("json_output/course_agent_state.json")  
    # with open("json_output/excel_data.json", "w", encoding="utf-8") as f:
    #     json.dump(course_agent_data, f)  

    # # K and A analysis pipeline
    # instructional_methods_data = create_instructional_dataframe()
    # ka_agent = create_ka_analysis_agent(instructional_methods_data, model_choice=model_choice)
    # stream = ka_agent.run_stream(task=overview_task)
    # await Console(stream)
    # #TSC JSON management
    # state = await ka_agent.save_state()
    # with open("json_output/ka_agent_state.json", "w") as f:
    #     json.dump(state, f)
    # ka_agent_data = extract_final_agent_json("json_output/ka_agent_state.json")
    # with open("json_output/excel_data.json", "w", encoding="utf-8") as out:
    #     json.dump(ka_agent_data, out, indent=2)

