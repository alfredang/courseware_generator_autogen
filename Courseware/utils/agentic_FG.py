# agentic_FG.py
import os
import re
import tempfile
import streamlit as st
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.base import TaskResult
import pandas as pd
import json
from PIL import Image
from docx.shared import Inches
from docxtpl import DocxTemplate, InlineImage

FG_TEMPLATE_DIR = "Courseware/input/Template/FG_TGS-Ref-No_Course-Title_v1.docx"  

def retrieve_excel_data(context: dict, sfw_dataset_dir: str) -> dict:
    # Load the Excel file
    excel_data = pd.ExcelFile(sfw_dataset_dir)
    
    # Load the specific sheet named 'TSC_K&A'
    df = excel_data.parse('TSC_K&A')
    
    tsc_code = context.get("TSC_Code")
    # Filter the DataFrame based on the TSC Code
    filtered_df = df[df['TSC Code'] == tsc_code]
    
    if not filtered_df.empty:
        row = filtered_df.iloc[0]
        
        context["TSC_Sector"] = str(row['Sector'])
        context["TSC_Sector_Abbr"] = str(tsc_code.split('-')[0])
        context["TSC_Category"] = str(row['Category'])
        context["Proficiency_Level"] = str(row['Proficiency Level'])
        context["Proficiency_Description"] = str(row['Proficiency Description'])

    # Return the retrieved data as a dictionary
    return context
    
def generate_facilitators_guide(context: dict, name_of_organisation: str, sfw_dataset_dir=None) -> str:
    # Use the provided template directory or default
    if sfw_dataset_dir is None:
        sfw_dataset_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"

    sfw_dataset_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"
    context = retrieve_excel_data(context, sfw_dataset_dir)

    doc = DocxTemplate(FG_TEMPLATE_DIR)
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