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

async def generate_facilitators_guide(context, name_of_organisation, model_client, sfw_dataset_dir=None):
    """
    Generate a Facilitator's Guide document based on the provided Course Proposal (CP) document.

    Args:
        context (dict): The structured course information.
        name_of_organisation (str): Name of the organisation (used for logos and other settings).
        sfw_dataset_dir (str, optional): Path to the SFW Excel dataset.
            If None, a default template path will be used.

    Returns:
        str: Path to the generated Facilitataor's Guide document.
    """

    def retrieve_excel_data(tsc_code: str) -> dict:
        # Load the Excel file
        excel_data = pd.ExcelFile(sfw_dataset_dir)

        # Load the specific sheet named 'TSC_K&A'
        df = excel_data.parse('TSC_K&A')

        # Filter the DataFrame based on the TSC Code
        filtered_df = df[df['TSC Code'] == tsc_code]

        if not filtered_df.empty:
            row = filtered_df.iloc[0]

            # Return the retrieved data as a dictionary
            return {
                "TSC_Sector": str(row['Sector']),
                "TSC_Sector_Abbr": str(tsc_code.split('-')[0]),
                "TSC_Category": str(row['Category']),
                "Proficiency_Level": str(row['Proficiency Level']),
                "Proficiency_Description": str(row['Proficiency Description'])
            }
        else:
            return {"Excel_Data_Error": f"No data found for TSC Code: {tsc_code}"}
        
    def generate_document(context: dict) -> str:
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

        doc.render(context)
        # Use a temporary file to save the document
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
            doc.save(tmp_file.name)
            output_path = tmp_file.name  # Get the path to the temporary file

        return output_path  # Return the path to the temporary file
    

    FG_TEMPLATE_DIR = "Courseware/input/Template/FG_TGS-Ref-No_Course-Title_v1.docx"  

    # Ensure 'lesson_plan' exists in context
    if 'lesson_plan' not in context:
        raise ValueError("Lesson plan not found in context. Ensure it is generated before calling this function.")

    # Use the provided template directory or default
    if sfw_dataset_dir is None:
        sfw_dataset_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"

    sfw_dataset_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"

    # Excel Data Retrieval Agent
    excel_data_retriever = AssistantAgent(
        name="Excel_Data_Retriever",
        model_client=model_client,
        tools=[retrieve_excel_data],
        system_message="""
        You are an expert in data retrieval from Excel files. Your task is to:
        1. Extract the TSC_Code from the provided course information JSON dictionary.
        2. Call the `retrieve_excel_data` function with only the TSC_Code to get the relevant data.
        3. Add the retrieved data (TSC_Sector, TSC_Sector_Abbr, TSC_Category, Proficiency_Level, Proficiency_Description) to the original JSON dictionary.
        4. **Return the updated dictionary with all original information plus the new Excel data. Do not truncate or omit any parts of the data. Include all fields and data in full. Do not replace any content with '...' or '[ ... ]'.**
        Include the word 'json' in your response.
        """
    )
    
    # FG Template Agent
    fg_assistant = AssistantAgent(
        name="FG_Assistant",
        model_client=model_client,
        tools=[generate_document],
        system_message="""
            You are responsible for generating the FG document using the collected data.
            
            **Key Responsibilities:**
            1. **Document Generation:**
                - **Receive the updated dictionary containing all the course information.**
                - **Receive the timetable dictionary (lesson_plan).**
                - **Combine the course information dictionary and the timetable dictionary into one final context dictionary.**
                - **Include the timetable dictionary under the key 'lesson_plan' within the context dictionary.**
                - **Ensure that the 'lesson_plan' is included inside the 'context' dictionary as a key.**
                - **Call the `generate_document` function using only the `context` arguments. Do not pass any additional arguments.**
                - **Verify the document was actually generated successfully.**
                - **If generation fails, retry once with corrected parameters.**

            **Important Notes:**
            - **When combining dictionaries, make sure all necessary data is included in the `context` dictionary.**
            - **Do not pass 'lesson_plan' or any other data as separate keyword arguments to `generate_document`.**

            **Example function call:**
            ```python
            generate_document(context=context_dict)
            ```

            **Do not proceed until you have confirmed successful document generation.**
        """,
    )

    agent_tasks = f"""
        ## Instructions for Excel Data Retriever agent:
        1. Take the complete JSON dictionary provided: {context}
        2. Extract the TSC_Code from the provided course information JSON dictionary.
        3. Call the `retrieve_excel_data` function with only the TSC_Code to get the relevant data.
        4. Add the retrieved data (TSC_Sector, TSC_Sector_Abbr, TSC_Category, Proficiency_Level, Proficiency_Description) to the original JSON dictionary.
        5. **Return the updated dictionary with all original information plus the new Excel data. Do not truncate or omit any parts of the data. Include all fields and data in full. Do not replace any content with '...' or '[ ... ]'.**

        ## Instructions for FG Assistant agent
        1. You have received the course information JSON dictionary and the timetable JSON dictionary.
        2. Call the `generate_document` function with the arguments: context=final_context_dictionary.
        **Example function call:**
        ```python
        generate_document(context=json context)
        ```
        3. Ensure that you only pass 'context' as arguments.
        """

    text_termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)

    # Create a team with the primary and critic agents.
    team = RoundRobinGroupChat([excel_data_retriever, fg_assistant], termination_condition=text_termination)
    result = await team.run(task=agent_tasks)

    for message in result.messages:
        if isinstance(message, TaskResult):
            print("Stop Reason:", message.stop_reason)
        else:
            print(f"############## Message : {message}\n\n")

        if message.source == "FG_Assistant" and message.type == "ToolCallSummaryMessage":
            return message.content  # Extract the file path 