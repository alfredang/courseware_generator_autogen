# agentic_AP.py
import os
import re
import tempfile
import pandas as pd
import streamlit as st
import json
import asyncio
from pydantic import BaseModel
from typing import List, Union, Optional
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken
from PIL import Image
from docx.shared import Inches
from docxtpl import DocxTemplate, InlineImage
from Courseware.utils.helper import retrieve_excel_data

class AssessmentMethod(BaseModel):
    evidence: Union[str, List[str]]
    submission: Union[str, List[str]]
    marking_process: Union[str, List[str]]
    retention_period: str
    no_of_scripts: Union[str, None] = None  # Optional field for "RP"

class AssessmentMethods(BaseModel):
    PP: Optional[AssessmentMethod] = None
    CS: Optional[AssessmentMethod] = None
    RP: Optional[AssessmentMethod] = None
    OQ: Optional[AssessmentMethod] = None

class EvidenceGatheringPlan(BaseModel):
    assessment_methods: AssessmentMethods


async def extract_assessment_evidence(structured_data, model_client):   
    """
    Extract structured data from the raw JSON input using an interpreter agent.

    Args:
        raw_data (dict): The raw unstructured data to be processed.
        llm_config (dict): Configuration for the language model.

    Returns:
        dict: Structured data extracted from the raw input.
    """
        # Build extracted content inline
    lines = []
    learning_units = structured_data.get("Learning_Units", [])

    for lu in learning_units:
        # LU Title
        lines.append(lu.get("LU_Title", ""))
        for topic in lu.get("Topics", []):
            # Topic Title
            lines.append(topic.get("Topic_Title", ""))
            # Bullet Points
            for bullet in topic.get("Bullet_Points", []):
                lines.append(bullet)
        lines.append("")  # Blank line after each LU block

    extracted_content = "\n".join(lines).strip()

    # 2. Interpreter Agent
    evidence_assistant = AssistantAgent(
        name="Evidence_Assistant",
        model_client=model_client,
        system_message=f"""
        Based on the following course details, you are to provide structured justifications for the selected Assessment Methods, aligning them with Learning Outcomes (LOs) and Topics.

        **Course Details:**
        - **Course Title:** {structured_data.get("Course_Title")}
        - **Learning Outcomes:**  
        {" ".join([lu['LO'] for lu in structured_data.get('Learning_Units', [])])}
        - **Topics Covered:** {extracted_content}
        - **Assessment Methods:** {", ".join([method['Method_Abbreviation'] for method in structured_data.get('Assessment_Methods_Details', [])])}

        ---

        **Your Task:**
        - Generate structured justifications for these applicable assessment methods:
        - **CS (Case Study)**
        - **PP (Practical Performance)**
        - **OQ (Oral Questioning)**
        - **RP (Role Play)**

        - For each assessment method, extract the following:
        1. **Type of Evidence**: The specific evidence candidates will submit.
        2. **Manner of Submission**: How candidates submit their work.
        3. **Marking Process**: The evaluation criteria used by assessors.
        4. **Retention Period**: The storage duration for submitted evidence.

        ---

        **Rules:**
        - Replace "students" with "candidates."
        - Replace "instructors" with "assessors."
        - Ensure all **LOs** are addressed.
        - **Limit word length**:
        - Bullet points: Max 30 words.
        - Marking Process: Max 6 words per evaluation.
        - **Format must be consistent**:
        - **PP, CS and OQ:** Evidence must be in a list of LOs.
        - **RP:** Special handling with "No. of Role Play Scripts."

        ---

        **One-Shot Example:**

        ```json
        {{
            "assessment_methods": {{
                "PP": {{
                "evidence": [
                    "LO1: Candidates will create an Excel workbook using formulas, functions, and Copilot's automation to demonstrate how Microsoft 365 tools can enhance workplace efficiency.",
                    "LO2: Candidates will use Microsoft Word to create and modify tables, automate formatting and review processes with Copilot, and submit the final document.",
                    "LO3: Candidates will develop a multimedia PowerPoint presentation with design and content enhancements assisted by Copilot.",
                    "LOx: Candidates will ..."
                ],
                "submission": [
                    "Candidates will submit their Excel workbooks, Word documents, and PowerPoint presentations.",
                    "Annotated screenshots or documentation showing Copilot’s contributions will be included."
                ],
                "marking_process": [
                    "Effectiveness in Using Copilot.",
                    "Quality of Outputs.",
                    "Efficiency and Customization."
                ],
                "retention_period": "All submitted evidence will be retained for 3 years."
                }},
                "CS": {{
                "evidence": [
                    "LO1: Candidates will submit a report demonstrating how they integrated design thinking methodologies and agile principles.",
                    "LO2: Candidates will conduct a problem-framing exercise using stakeholder inputs, create a persona mapping based on user insights, and submit a report.",
                    "LO3: Candidates will lead an innovation project using Agile and design thinking approaches.",
                    "LOx: Candidates will ..."
                ],
                "submission": [
                    "Candidates will submit their case study reports electronically via the learning management system."
                ],
                "marking_process": [
                    "Integration of Methodologies.",
                    "Stakeholder Analysis.",
                    "Project Leadership and Tools."
                ],
                "retention_period": "All submitted case study reports will be retained for 3 years."
                }},
                "OQ": {{
                "evidence": [
                    "LO1: Candidates will ...",
                    "LOx: Candidates will ..."
                ],
                "submission": [
                    "Candidates will verbally respond to assessors during a structured questioning session."
                ],
                "marking_process": [
                    "...",
                    "...",
                    "..."
                ],
                "retention_period": "All oral questioning recordings and assessment notes will be retained for 2 years for compliance and auditing."
                }}, 
                "RP": {{
                "evidence": "Role Play",
                "submission": [
                    "Assessor will evaluate the candidate using an observation checklist."
                ],
                "marking_process": [
                    "Effectiveness of sales recommendations.",
                    "Application of sales techniques.",
                    "Presentation of follow-up steps and metrics."
                ],
                "retention_period": "3 years.",
                "no_of_scripts": "Minimum of two distinct role-play scripts will be prepared."
                }}
            }}
        }}
    """
    )


    evidence_task = f"""
    Your task is to generate the assessment evidence gathering plan.
    Return the data as a structured JSON dictionary string encapsulated in ```json and 'TERMINATE'.
    """

    # Process sample input
    response = await evidence_assistant.on_messages(
        [TextMessage(content=evidence_task, source="user")], CancellationToken()
    )

    evidence_data = json.loads(response.chat_message.content)
    return evidence_data

def combine_assessment_methods(structured_data, evidence_data):
    """
    Combine evidence data into structured_data under Assessment_Methods_Details.

    Args:
        structured_data (dict): The original structured data.
        evidence_data (dict): The detailed evidence data to combine.

    Returns:
        dict: Updated structured data with evidence details merged into Assessment_Methods_Details.
    """
    # Extract evidence data for assessment methods
    evidence_methods = evidence_data.get("assessment_methods", {})

    # Iterate over Assessment_Methods_Details to integrate evidence data
    for method in structured_data.get("Assessment_Methods_Details", []):
        method_abbr = method.get("Method_Abbreviation")

        # Match the evidence data based on the abbreviation
        if method_abbr in evidence_methods:
            evidence_details = evidence_methods[method_abbr]
            
            
            if "WA-SAQ" in method_abbr:
            # Update the method with detailed evidence data
                method.update({
                    "Evidence": evidence_details.get("evidence", ""),
                    "Submission": evidence_details.get("submission", ""),
                    "Marking_Process": evidence_details.get("marking_process", ""),
                    "Retention_Period": evidence_details.get("retention_period", "")
                })

            if "PP" in method_abbr or "CS" in method_abbr or "OQ" in method_abbr:
            # Update the method with detailed evidence data
                method.update({
                    "Evidence": evidence_details.get("evidence", []),
                    "Submission": evidence_details.get("submission", []),
                    "Marking_Process": evidence_details.get("marking_process", []),
                    "Retention_Period": evidence_details.get("retention_period", "")
                })

            # Include no_of_scripts for Role Play (RP) assessment
            if method_abbr == "RP":
                method.update({
                    "Evidence": evidence_details.get("evidence", ""),
                    "Submission": evidence_details.get("submission", ""),
                    "Marking_Process": evidence_details.get("marking_process", []),
                    "Retention_Period": evidence_details.get("retention_period", "")
                })
                method["No_of_Scripts"] = evidence_details.get("no_of_scripts", "Not specified")

    return structured_data

AP_TEMPLATE_DIR = "Courseware/input/Template/AP_TGS-Ref-No_Course-Title_v1.docx"  
ASR_TEMPLATE_DIR = "Courseware/input/Template/ASR_TGS-Ref-No_Course-Title_v1.docx"  

# Check if assessment methods already contain necessary details
def is_evidence_extracted(context):
    for method in context.get("Assessment_Methods_Details", []):
        method_abbr = method.get("Method_Abbreviation")
        # Skip checking for WA-SAQ entirely, as it is hardcoded in the template.
        if method_abbr == "WA-SAQ":
            continue
        # For other methods, check the required keys.
        for key in ["Evidence", "Submission", "Marking_Process", "Retention_Period"]:
            # For RP, skip checking "Evidence" and "Submission"
            if method_abbr == "RP" and key in ["Evidence", "Submission"]:
                continue
            if method.get(key) is None:
                return False
    return True

def generate_assessment_plan(context: dict, name_of_organisation, sfw_dataset_dir) -> str:

    if not is_evidence_extracted(context):
        print("Extracting missing assessment evidence...")

        evidence_model_client = OpenAIChatCompletionClient(
            model=st.secrets["REPLACEMENT_MODEL"],
            response_format=EvidenceGatheringPlan,  # Structured output config
            temperature=0,
            api_key=st.secrets["OPENAI_API_KEY"]
        )

        evidence = asyncio.run(extract_assessment_evidence(structured_data=context, model_client=evidence_model_client))
        context = combine_assessment_methods(context, evidence)
    else:
        print("Skipping assessment evidence extraction as all required fields are already present.")

    doc = DocxTemplate(AP_TEMPLATE_DIR)

    context = retrieve_excel_data(context, sfw_dataset_dir)
    logo_filename = name_of_organisation.lower().replace(" ", "_") + ".jpg"
    logo_path = f"Courseware/utils/logo/{logo_filename}"

    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"Logo file not found for organisation: {name_of_organisation}")

    # Open the logo image to get its dimensions
    image = Image.open(logo_path)
    width_px, height_px = image.size  # Get width and height in pixels
    
    # Define maximum dimensions (in inches)
    max_width_inch = 7  # Adjust as needed
    max_height_inch = 2.5  # Adjust as needed

    # Get DPI and calculate current dimensions in inches
    dpi = image.info.get('dpi', (96, 96))  # Default to 96 DPI if not specified
    width_inch = width_px / dpi[0]
    height_inch = height_px / dpi[1]

    # Scale dimensions if they exceed the maximum
    width_ratio = max_width_inch / width_inch if width_inch > max_width_inch else 1
    height_ratio = max_height_inch / height_inch if height_inch > max_height_inch else 1
    scaling_factor = min(width_ratio, height_ratio)

    # Apply scaling
    width_docx = Inches(width_inch * scaling_factor)
    height_docx = Inches(height_inch * scaling_factor)

    # Create an InlineImage object with the desired dimensions
    logo_image = InlineImage(doc, logo_path, width=width_docx, height=height_docx)

    # Add the logo to the context
    context['company_logo'] = logo_image
    context['Name_of_Organisation'] = name_of_organisation
    print(f"##########\n\n{context}\n\n")
    doc.render(context, autoescape=True)

    # Use a temporary file to save the document
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        doc.save(tmp_file.name)
        output_path = tmp_file.name  # Get the path to the temporary file

    return output_path  # Return the path to the temporary file

def generate_asr_document(context: dict, name_of_organisation) -> str:
    doc = DocxTemplate(ASR_TEMPLATE_DIR)
    context['Name_of_Organisation'] = name_of_organisation

    doc.render(context)

    # Use a temporary file to save the document
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        doc.save(tmp_file.name)
        output_path = tmp_file.name  # Get the path to the temporary file

    return output_path  # Return the path to the temporary file

def generate_assessment_documents(context: dict, name_of_organisation, sfw_dataset_dir=None):
    try:
        # Use the provided template directory or default
        if sfw_dataset_dir is None:
            sfw_dataset_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"

        # Generate the Assessment Plan document
        ap_output_path = generate_assessment_plan(context, name_of_organisation, sfw_dataset_dir)
        # Generate the Assessment Summary Report document
        asr_output_path = generate_asr_document(context, name_of_organisation)

        return ap_output_path, asr_output_path
    except Exception as e:
        print(f"An error occurred during document generation: {e}")
        return None, None