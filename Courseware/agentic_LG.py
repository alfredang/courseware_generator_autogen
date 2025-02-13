# agentic_LG.py
import os
import re
import json
import tempfile
import streamlit as st
import asyncio
from pydantic import BaseModel
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from PIL import Image
from docx.shared import Inches
from docxtpl import DocxTemplate, InlineImage
from jinja2 import Environment

LG_TEMPLATE_DIR = "Courseware/input/Template/LG_TGS-Ref-No_Course-Title_v1.docx"  

async def generate_content(context, model_client):
    """
    Generate a Learning Guide document based on the provided Course Proposal (CP) document.

    Args:
        context (dict): The structured course information.
        name_of_organisation (str): Name of the organisation (used for logos and other settings).

    Returns:
        str: Path to the generated Learning Guide document.
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
        json_content = response.chat_message.content.strip()
        json_pattern = re.compile(r'```json\s*(\{.*?\})\s*```', re.DOTALL)
        json_match = json_pattern.search(json_content)
        if json_match:
            json_str = json_match.group(1)
            context = json.loads(json_str)
        print(f"############ LG CONTENT RESPONSE: {context}")
    except json.JSONDecodeError as e:
        print(f"Error parsing LG content JSON: {e}")
    return context

def generate_learning_guide(context: dict, name_of_organisation: str, model_client) -> str:

    content_response = asyncio.run(generate_content(context, model_client))
    context["Course_Overview"] = content_response.get("Course_Overview") 
    context["LO_Description"] = content_response.get("LO_Description") 

    doc = DocxTemplate(LG_TEMPLATE_DIR)
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

    doc.render(context, autoescape=True)
    # Use a temporary file to save the document
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        doc.save(tmp_file.name)
        output_path = tmp_file.name  # Get the path to the temporary file

    return output_path  # Return the path to the temporary file