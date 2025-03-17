# agentic_LG.py

import json
import tempfile
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from docxtpl import DocxTemplate
from utils.helper import parse_json_content
from Courseware.utils.helper import process_logo_image

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
        # print(f"#############LG CONTEXT###########\n\n{context}")
        context = parse_json_content(response.chat_message.content)

    except json.JSONDecodeError as e:
        print(f"Error parsing LG content JSON: {e}")
    return context

def generate_learning_guide(context: dict, name_of_organisation: str, model_client) -> str:

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