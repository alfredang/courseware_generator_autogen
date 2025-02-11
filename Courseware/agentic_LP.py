# agentic_LP.py
import os
import re
import tempfile
import streamlit as st
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from PIL import Image
from docx.shared import Inches
from docxtpl import DocxTemplate, InlineImage

async def generate_lesson_plan(context, name_of_organisation, model_client):
    """
    Generate a Lesson Plan document based on the provided Course Proposal (CP) document.

    Args:
        context (dict): The structured course information.
        name_of_organisation (str): Name of the organisation.

    Returns:
        str: Path to the generated Lesson Plan document.
    """

    def generate_document(context: dict) -> str:
        doc = DocxTemplate(LP_TEMPLATE_DIR)
        
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

        doc.render(context)
        # Use a temporary file to save the document
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
            doc.save(tmp_file.name)
            output_path = tmp_file.name  # Get the path to the temporary file

        return output_path  # Return the path to the temporary file

    LP_TEMPLATE_DIR = "Courseware/input/Template/LP_TGS-Ref-No_Course-Title_v1.docx" 

    # Ensure 'lesson_plan' exists in context
    if 'lesson_plan' not in context:
        raise ValueError("Lesson plan not found in context. Ensure it is generated before calling this function.")

    # LP Template Agent
    lp_assistant = AssistantAgent(
        name="LP_Template_Agent",
        model_client=model_client,
        tools=[generate_document],
        system_message="""
        You are responsible for generating the LP document using the collected data.
        
        **Key Responsibilities:**
        1. **Document Generation:**
            - **Receive the updated JSON dictionary containing all the course information.**
            - **Call the `generate_document` function using only the `context` arguments. Do not pass any additional arguments.**
            - **Verify the document was actually generated successfully.**
            - **If generation fails, retry once with corrected parameters.**

        **Example function call:**
        ```python
        generate_document(context=json context)
        ```

        **Do not proceed until you have confirmed successful document generation.**
        """,
    )

    agent_task = f"""
        1. Take the complete dictionary provided:
        {context}
        2. You have received the course information JSON dictionary that includes the lesson_plan data.
        3. Call the `generate_document` function with the arguments: context=final_context_dictionary.
        **Example function call:**
        ```python
        generate_document(context=json context)
        ```
        3. Ensure that you only pass 'context' as arguments.
        4. After the function call, include the output path returned by the function in your final message, starting with `Output Path: ` followed by the path.
        5. Return 'TERMINATE' when the task is done.
        """
    
     # Process sample input
    response = await lp_assistant.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )
      # Extract the output path from the last agent
    lp_output_path = None
    
    try:
        lp_output_path = response.chat_message.content
    except Exception as e:
        raise Exception(f"Error: Lesson Plan chat content missing.")
    if lp_output_path:
            return lp_output_path
    else:
        raise Exception("Lesson Plan generation failed.")