"""
File: agentic_LG.py

===============================================================================
Learning Guide Generation Module
===============================================================================
Description:
    This module is responsible for generating a Learning Guide (LG) document for a course.
    It utilizes an AI assistant to produce structured content, including a Course Overview (90-100 words)
    and a Learning Outcome description (45-50 words), based on the provided course details.
    The generated content is then merged into a DOCX template, along with organization branding such as
    the company logo, to create a comprehensive Learning Guide tailored to potential learners.

Main Functionalities:
    • generate_content(context, model_client):
          Uses an AI assistant agent to generate a detailed Course Overview and a concise Learning Outcome
          description. The output is a JSON dictionary with keys "Course_Overview" and "LO_Description".
    • generate_learning_guide(context, name_of_organisation, model_client):
          Retrieves the AI-generated content, integrates it into a DOCX template, inserts the organization's logo,
          renders the document, and saves it as a temporary file. Returns the file path of the generated Learning Guide.

Dependencies:
    - Standard Libraries: json, tempfile, asyncio
    - External Libraries:
         • autogen_agentchat.agents (AssistantAgent)
         • autogen_core (CancellationToken)
         • autogen_agentchat.messages (TextMessage)
         • docxtpl (DocxTemplate)
    - Custom Utilities:
         • parse_json_content from utils.helper
         • process_logo_image from generate_ap_fg_lg_lp/utils/helper

Usage:
    - Ensure the Learning Guide DOCX template and organization logo are available at the specified paths.
    - Configure the AI model client and prepare a structured course context.
    - Invoke generate_learning_guide(context, name_of_organisation, model_client) to generate the Learning Guide.
    - The function returns the file path of the generated document.

Author:
    Derrick Lim
Date:
    3 March 2025
===============================================================================
"""

import json
import tempfile
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from docxtpl import DocxTemplate
from common.common import parse_json_content
from generate_ap_fg_lg_lp.utils.helper import process_logo_image

LG_TEMPLATE_DIR = "generate_ap_fg_lg_lp/input/Template/LG_TGS-Ref-No_Course-Title_v1.docx"  

async def generate_content(context, model_client):
    """
    Generates a Course Overview and Learning Outcome description for a Learning Guide.

    This function uses an AI assistant to generate structured content for a Learning Guide 
    based on the provided course information. The generated text is strictly formatted 
    according to predefined rules, ensuring precise word counts and appropriate structuring.

    Args:
        context (dict): 
            A dictionary containing structured course information.
        model_client: 
            An AI model client instance used to generate the learning content.

    Returns:
        dict: 
            An updated context dictionary containing:
            - `"Course_Overview"` (str): A detailed introduction to the course.
            - `"LO_Description"` (str): A concise and measurable learning outcome description.

    Raises:
        json.JSONDecodeError: 
            If the AI response does not contain valid JSON content.
        Exception: 
            If the response lacks the required keys `"Course_Overview"` or `"LO_Description"`.
    """

    # 4. Content Generator Agent
    content_generator = AssistantAgent(
        name="Content_Generator",
        model_client=model_client,
        system_message="""
        You are an expert in creating detailed and informative content for course descriptions. Your task is to:

        1. Generate a course overview (Learning Overview) of EXACTLY 90-100 words based on the provided Course Title. The overview MUST:
            - Start with "The `course_  title` course provides..."
            - Provide a comprehensive introduction to the course content
            - Highlight multiple key concepts or skills that will be covered in all the learning units
            - Use clear and detailed language suitable for potential learners
            - Include specific examples of topics or techniques covered

        2. Generate a learning outcome description (Learning Outcome) of EXACTLY 45-50 words based on the provided Course Title. The learning outcome MUST:
            - Start with "By the end of this course, learners will be able to..."
            - Focus on at least three key skills or knowledge areas that participants will gain
            - Use specific action verbs to describe what learners will be able to do
            - Be detailed, specific, and measurable
            - Reflect the depth and complexity of the course content

        3. Return these as a dictionary with keys "Course_Overview" and "LO_Description".
            ```json
            {

                "Course_Overview": "The [Course Title] course provides...",
                "LO_Description": "By the end of this course, learners will be able to..."
            }
            ```
        Ensure that the content is tailored to the specific course title provided, reflects the depth and focus of the course, and STRICTLY adheres to the specified word counts.
        """
    )

    # Example task message that requests JSON output
    agent_task = f"""
        Please:
        1. Take the complete dictionary provided:
        {context}
        2. Generate the Course Overview and Learning Outcome description.
        4. Return the JSON dictionary containing the 'Course_Overview' and 'LO_Description' key.
        """
    
    # Process sample input
    response = await content_generator.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )
    
    try:
        if not response.chat_message.content:
            print("No content found in the agent's last message.")
        # print(f"#############LG CONTEXT###########\n\n{context}")
        context = parse_json_content(response.chat_message.content)

    except json.JSONDecodeError as e:
        print(f"Error parsing LG content JSON: {e}")
    return context

def generate_learning_guide(context: dict, name_of_organisation: str, model_client) -> str:
    """
    Generates a Learning Guide document by populating a DOCX template with course content.

    This function retrieves AI-generated course descriptions, inserts them into a Learning Guide template, 
    and adds the organization's logo before saving the document.

    Args:
        context (dict): 
            A dictionary containing course details to be included in the Learning Guide.
        name_of_organisation (str): 
            The name of the organization, used to retrieve and insert the corresponding logo.
        model_client: 
            An AI model client instance used for content generation.

    Returns:
        str: 
            The file path of the generated Learning Guide document.

    Raises:
        FileNotFoundError: 
            If the template file or the organization's logo file is missing.
        KeyError: 
            If required keys such as `"Course_Overview"` or `"LO_Description"` are missing.
        IOError: 
            If there are issues with reading/writing the document.
    """

    content_response = asyncio.run(generate_content(context, model_client))
    context["Course_Overview"] = content_response.get("Course_Overview") 
    context["LO_Description"] = content_response.get("LO_Description") 

    doc = DocxTemplate(LG_TEMPLATE_DIR)

    # Add the logo to the context
    context['company_logo'] = process_logo_image(doc, name_of_organisation)
    context['Name_of_Organisation'] = name_of_organisation

    doc.render(context, autoescape=True)
    # Use a temporary file to save the document
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        doc.save(tmp_file.name)
        output_path = tmp_file.name  # Get the path to the temporary file

    return output_path  # Return the path to the temporary file