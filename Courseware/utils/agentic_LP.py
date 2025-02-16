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

LP_TEMPLATE_DIR = "Courseware/input/Template/LP_TGS-Ref-No_Course-Title_v1.docx" 

def generate_lesson_plan(context: dict, name_of_organisation) -> str:
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

    doc.render(context, autoescape=True)
    # Use a temporary file to save the document
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        doc.save(tmp_file.name)
        output_path = tmp_file.name  # Get the path to the temporary file

    return output_path  # Return the path to the temporary file