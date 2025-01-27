import autogen
import dotenv
import json
import streamlit as st
import os
from autogen import UserProxyAgent, AssistantAgent
from pprint import pprint
import subprocess
import sys
import re

def main():
    # Load API key from environment
    # OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]


    # Manually create the config list with JSON response format
    config_list = [
        {
            "model": "gpt-4o",
            "api_key": OPENAI_API_KEY,
            "response_format": {"type": "json_object"},
        }
    ]

    llm_config = {
        "temperature": 0.5,
        "config_list": config_list,
        "timeout": 120,  # in seconds
    }

    assessment_justification_agent = AssistantAgent(
        name="assessment_justification_agent",
        llm_config=llm_config,
        system_message="""
        You are an instructional designer tasked with helping to develop assessments for courses. Your main focus is to guide in designing appropriate assessment methods aligned with a course's learning outcomes and topics.
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


    with open('ensemble_output.json', 'r', encoding='utf-8') as file:
        ensemble_output = json.load(file)

    if isinstance(ensemble_output, str):
        ensemble_output = json.loads(ensemble_output)

    assessment_justification_agent_message = f"""
    Based on the following course details, you are to provide justification for the appropriate Assessment Method followng a defined structure.
    The course details are as follows:
    Course Title: {ensemble_output.get('Course Information', {}).get('Course Title', [])} 
    Learning Outcomes: {ensemble_output.get('Learning Outcomes', {}).get('Learning Outcomes', [])}
    Topics Covered: {ensemble_output.get('Assessment Methods', {}).get('Course Outline', [])}
    Assessment Methods: {ensemble_output.get('Assessment Methods', {}).get('Assessment Methods', [])}

    The Written Assessment or WA-SAQ will always be present in Assessment Methods, you may ignore that. Your focus is on justifying either the Case Study, Practical Performance, Oral Questioning, or Role Play, whichever is applicable.
    Your justification must only be for one method at a time, do not mix up both.

    Provide justifications for why the assessment method aligns with the course learning outcomes and topics.
    For each assessment method, you will provide a breakdown that includes:

    1) Type of Evidence: What candidates will submit to demonstrate their understanding or skills.
    2) Manner of Submission: How the candidates will submit their work to assessors.
    3) Marking Process: How assessors will evaluate the work, including rubrics or specific evaluation criteria.
    4) Retention Period: How long the submitted work will be stored for auditing or compliance purposes.

    Rules:
    Replace "students" with "candidates."
    Replace "instructors" with "assessors."
    You are to return your output in a JSON structure as seen in the examples below.
    Ensure that all LOs are addressed.
    Limit word length for all bulleted points to one sentence, not more than 30 words.
    The Marking Process should consist of 3 different evaluations, keep it concise with not more than 6 words.

    Practical Performance (PP) Example:
    A practical Performance (PP) assessment will provide direct evidence of whether candidates have acquired the competency for the ability statements by solving a scenario-based problem. 

    The Practical Performance (PP) assessment focuses on providing authentic "Show Me Application" evidence of candidates' ability to apply Microsoft 365 Office tools and Copilot features to enhance productivity in realistic workplace tasks. Candidates will complete a series of practical tasks that demonstrate their ability to use the advanced functionalities of Microsoft Excel, Word, and PowerPoint, integrating Copilot to optimize performance.
    Type of Evidence:
    •	For LO1: Candidates will create an Excel workbook using formulas, functions, and Copilot's automation to demonstrate how Microsoft 365 tools can enhance workplace efficiency.
    •	For LO2: Candidates will use Microsoft Word to create and modify tables, automate formatting and review processes with Copilot, and submit the final document.
    •	For LO3: Candidates will develop a multimedia PowerPoint presentation with design and content enhancements assisted by Copilot.
    Manner of Submission:
    •	Candidates will submit their Excel workbooks, Word documents, and PowerPoint presentations, as well as any additional supporting documentation that details how they utilized Microsoft 365 tools and Copilot features to enhance productivity. This includes annotated screenshots or documentation showing Copilot's contributions to task completion.
    Marking Process:
    •	Effectiveness in Using Copilot.
    •	Quality of Outputs.
    •	Efficiency and Customization.
    Retention Period:
    •	All submitted evidence, including Excel workbooks, Word documents, PowerPoint presentations, and assessment records, will be retained for 3 years to ensure compliance with institutional policies and for auditing purposes.

    Case Study (CS) example:
    A case study (Written Assessment) consists of scenarios that allow an assessment of the candidate's mastery of abilities. The assessor can collect process evidence to assess the candidate's competencies against the learning outcomes. It allows consistent interpretation of evidence and reliable assessment outcomes.

    This case study assessment focuses on providing authentic "Show Me Application" evidence of candidates' ability to apply Agile design thinking and Generative AI to foster innovation in an organizational context.
    Type of Evidence: 
    •	For LO1: Candidates will submit a report demonstrating how they integrated design thinking methodologies and agile principles.
    •	For LO2: Candidates will conduct a problem-framing exercise using stakeholder inputs, create a persona mapping based on user insights, and submit a report.
    •	For LO3: Candidates will lead an innovation project using Agile and design thinking approaches.
    •	For LO4: Candidates will submit a strategic plan detailing how they developed and scaled design thinking methodologies across the organization.
    Manner of Submission: 
    •	Candidates will submit their case study reports and any additional supporting documents to the assessors electronically via the designated learning management system.
    Marking Process:
    •	Integration of Methodologies.
    •	Stakeholder Analysis.
    •	Project Leadership and Tools.
    Retention Period: All submitted case study reports and accompanying documentation will be retained for 3 years to ensure compliance with institutional policies and for auditing purposes.

    Role Play (RP) example:
    Role Play assessments allow learners to demonstrate their ability to apply learned concepts in simulated real-world interactions, focusing on the practical application of sales closure skills.

    Type of Evidence: Role Play
    Manner of Submission: 
    •	Assessor will evaluate the candidate using an observation checklist for the role play.
    Marking Process:
    •	Effectiveness of sales recommendations.
    •	Application of sales techniques.
    •	Presentation of follow-up steps and metrics.
    Retention Period: 3 years.
    No. of Role Play Scripts: To ensure fairness among learners, a minimum of two distinct role-play scripts or scenarios will be prepared for this assessment


    **Your response must be ONLY the JSON structure, formatted exactly as per the example below, enclosed in a code block (i.e., triple backticks ```). Do not include any additional text or explanations outside the JSON code block. Do not include any headings or introductions. Just output the JSON code block.**
    "assessment_methods": {{
        "practical_performance": {{
        "name": "Practical Performance (PP)",
        "description": "A practical Performance (PP) assessment will provide direct evidence of whether candidates have acquired the competency for the ability statements by solving a scenario-based problem.",
        "focus": "The Practical Performance (PP) assessment focuses on providing authentic \"Show Me Application\" evidence of candidates' ability to apply Microsoft 365 Office tools and Copilot features to enhance productivity in realistic workplace tasks.",
        "tasks": [
            "Candidates will complete a series of practical tasks that demonstrate their ability to use the advanced functionalities of Microsoft Excel, Word, and PowerPoint, integrating Copilot to optimize performance."
        ],
        "evidence": {{
            "LO1": "Candidates will create an Excel workbook using formulas, functions, and Copilot's automation to demonstrate how Microsoft 365 tools can enhance workplace efficiency.",
            "LO2": "Candidates will use Microsoft Word to create and modify tables, automate formatting and review processes with Copilot, and submit the final document.",
            "LO3": "Candidates will develop a multimedia PowerPoint presentation with design and content enhancements assisted by Copilot."
        }},
        "submission": [
            "Candidates will submit their Excel workbooks, Word documents, and PowerPoint presentations, as well as any additional supporting documentation that details how they utilized Microsoft 365 tools and Copilot features to enhance productivity.",
            "This includes annotated screenshots or documentation showing Copilot's contributions to task completion."
        ],
        "marking_process": [
            "Effectiveness in Using Copilot.",
            "Quality of Outputs.",
            "Efficiency and Customization."
        ],
        "retention_period": "All submitted evidence, including Excel workbooks, Word documents, PowerPoint presentations, and assessment records, will be retained for 3 years to ensure compliance with institutional policies and for auditing purposes."
        }}
    }}

    However, in the case of Role Play assessment, you are to format it as follows:
    "assessment_methods": {{
        "role_play": {{
        "name": "Role Play (RP)",
        "description": "Role Play assessments allow learners to demonstrate their ability to apply learned concepts in simulated real-world interactions, focusing on the practical application of sales closure skills.",
        "focus": "Role Play assessments allow learners to demonstrate their ability to apply learned concepts in simulated real-world interactions, focusing on the practical application of sales closure skills.",
        "evidence": "Role play",
        "submission": "Assessor will evaluate the candidate using an observation checklist for the role play.",
        "marking_process": [
            "Effectiveness of sales recommendations.",
            "Application of sales techniques.",
            "Presentation of follow-up steps and metrics."
        ],
        "retention_period": "3 years",
        "no_of_scripts": "To ensure fairness among learners, a minimum of two distinct role-play scripts or scenarios will be pre-pared for this assessment"
        }}
    }}

    However, in the case of Oral Questioning assessment, you are to format it as follows:
    "assessment_methods": {{
        "oral_questioning": {{
        "name": "Oral Questioning (OQ)",
        "description": "Role Play assessments allow learners to demonstrate their ability to apply learned concepts in simulated real-world interactions, focusing on the practical application of sales closure skills.",
        "focus": "Role Play assessments allow learners to demonstrate their ability to apply learned concepts in simulated real-world interactions, focusing on the practical application of sales closure skills.",
        "evidence": {{
            "LO1": "Candidates will discuss methods for maintaining accurate records and monitoring client satisfaction.",
            "LO2": "For LO1: Candidates will respond to questions demonstrating their understanding of customer communication techniques and preferences.",
        }},
        "submission": "Candidates will verbally respond to assessors during a structured questioning session.",
        "marking_process": [
            "Effectiveness of sales recommendations.",
            "Application of sales techniques.",
            "Presentation of follow-up steps and metrics."
        ],
        "retention_period": "All oral questioning recordings and assessment notes will be retained for 2 years for compliance and auditing.",
        }}
    }}    

    """

    assessment_justification_agent_chat = user_proxy.initiate_chat(
        assessment_justification_agent,
        message=assessment_justification_agent_message,
        summary_method="last_msg",
        max_turns=2  # Define the maximum turns you want the chat to last
    )

    assessment_justification_agent_response = assessment_justification_agent.last_message()["content"]

    # print(assessment_justification_agent_chat)
    print(assessment_justification_agent_response)

    def recreate_assessment_phrasing_dynamic(json_data):
        phrasing_list = []
        
        # Check for which assessment method is present in the JSON data
        for method_key, method_data in json_data['assessment_methods'].items():
            if method_data:
                # Header with method name and description
                phrasing = f"{method_data['name']}:\n{method_data['description']}\n\n"
                phrasing += f"{method_data['focus']}\n{method_data['tasks'][0]}\n\n" if 'tasks' in method_data else ""
                
                # Type of Evidence
                phrasing += "Type of Evidence:\n"
                if isinstance(method_data['evidence'], dict):
                    for lo, evidence in method_data['evidence'].items():
                        phrasing += f"•\tFor {lo}: {evidence}\n"
                else:
                    phrasing += f"•\t{method_data['evidence']}\n"
                
                # Manner of Submission
                phrasing += "Manner of Submission:\n"
                if isinstance(method_data['submission'], list):
                    for submission in method_data['submission']:
                        phrasing += f"•\t{submission}\n"
                else:
                    phrasing += f"{method_data['submission']}\n"
                
                # Marking Process
                phrasing += "Marking Process: \n"
                for criteria in method_data['marking_process']:
                    phrasing += f"•\t{criteria}\n"
                
                # Retention Period
                phrasing += f"Retention Period:\n•\t{method_data['retention_period']}\n"
                
                # No. of Role Play Scripts (specific to Role Play)
                if method_key == "role_play" and "no_of_scripts" in method_data:
                    phrasing += f"No. of Role Play Scripts:\n•\t{method_data['no_of_scripts']}\n"
                
                phrasing_list.append(phrasing)
                break  # Exit after finding the first present method since only one will be there

        return "\n".join(phrasing_list)

    # Check if the response is a string or dictionary
    response = assessment_justification_agent_response

    # If it's a string, parse it as JSON
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            print("Error: Response is not a valid JSON string.")

    # Now you can safely call the function with the parsed response
    output_phrasing = recreate_assessment_phrasing_dynamic(response)

    # Print the output phrasing
    print(output_phrasing)  

    # Load the existing research_output.json
    with open('research_output.json', 'r', encoding='utf-8') as f:
        research_output = json.load(f)

    # Append the new output phrasing to the research_output
    # You can choose to store it under a new key, such as "Assessment Phrasing"
    if "Assessment Phrasing" not in research_output:
        research_output["Assessment Phrasing"] = []

    # Append the new result
    research_output["Assessment Phrasing"].append(output_phrasing)

    # Save the updated research_output.json
    with open('research_output.json', 'w', encoding='utf-8') as f:
        json.dump(research_output, f, indent=4)


if __name__ == "__main__":
    main()


