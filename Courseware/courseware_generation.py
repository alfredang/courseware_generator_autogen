"""
File: courseware_generation.py

===============================================================================
Courseware Document Generator
===============================================================================
Description:
    This module serves as the main entry point for the Courseware Document Generator
    application. It is designed to parse Course Proposal (CP) documents, extract and
    interpret the course data, and generate multiple courseware documents such as:
      - Learning Guide (LG)
      - Assessment Plan (AP)
      - Lesson Plan (LP)
      - Facilitator's Guide (FG)
      - Timetable (as needed)
      
    The application utilizes both AI-based processing (via OpenAI and autogen agents)
    and conventional document parsing and web scraping methods to ensure that the CP data
    is accurately transformed into a structured format for document generation.

Main Functionalities:
    1. Data Models:
        - Defines several Pydantic models (e.g., Topic, LearningUnit, CourseData, etc.)
          to validate and structure the course proposal and generated document data.
          
    2. Document Parsing:
        - Function: parse_cp_document(uploaded_file)
          Parses a CP document (Word or Excel) into a trimmed Markdown string based on
          regex patterns to capture only the relevant sections of the document.
          
    3. Web Scraping:
        - Function: web_scrape(course_title, name_of_org)
          Automates a headless browser session using Selenium to retrieve TGS Ref No (and UEN)
          from the MySkillsFuture portal based on the provided course title and organization.
          
    4. Data Interpretation:
        - Function: interpret_cp(raw_data, model_client)
          Leverages an AI assistant (via the OpenAIChatCompletionClient) to extract and structure
          the course proposal data into a comprehensive JSON dictionary as defined by the CourseData model.
          
    5. Streamlit Application:
        - Function: app()
          Implements the user interface using Streamlit. This interface guides users through:
            - Uploading a Course Proposal document.
            - Managing organization details (CRUD operations via a modal).
            - Optionally uploading an updated Skills Framework dataset.
            - Selecting which courseware documents to generate.
            - Executing the parsing, data extraction, document generation processes,
              and finally providing a ZIP file download of all generated documents.
              
Dependencies:
    - Custom Courseware Utilities:
        • Courseware.utils.agentic_LG         : For generating the Learning Guide.
        • Courseware.utils.agentic_AP         : For generating Assessment Documents.
        • Courseware.utils.timetable_generator : For generating the course timetable.
        • Courseware.utils.agentic_LP         : For generating the Lesson Plan.
        • Courseware.utils.agentic_FG         : For generating the Facilitator's Guide.
        • Courseware.utils.model_configs       : For model configuration and selection.
        • Courseware.utils.organization_utils  : For managing organization data (CRUD).
    - External Libraries:
        • os, io, zipfile, tempfile, json, time, asyncio, datetime
        • streamlit                        : For building the web UI.
        • selenium & BeautifulSoup         : For web scraping tasks.
        • docx                             : For generating and modifying Word documents.
        • pydantic                         : For data validation and structured models.
        • autogen_agentchat & autogen_core   : For AI-assisted text generation and processing.
        • urllib.parse                     : For URL manipulation.
    
Usage:
    - Configure API keys and endpoints in st.secrets (e.g., LLAMA_CLOUD_API_KEY, BROWSER_TOKEN,
      BROWSER_WEBDRIVER_ENDPOINT, etc.).
    - Run this module using Streamlit, e.g., `streamlit run <this_file.py>`, to launch the web interface.
    - Follow the on-screen instructions to upload your CP document, manage organization data, select
      the desired courseware documents, and generate/download the outputs.

Author: 
    Derrick Lim
Date:
    4 March 2025

Notes:
    - This module uses asynchronous functions and external AI services for data extraction.
    - The Selenium web scraping component is configured to run headlessly with optimized options
      suitable for both local and containerized environments.
    - Organization management is performed using a JSON-based system via utility functions provided
      in the Courseware.utils.organization_utils module.
    - Ensure all dependencies are installed and properly configured before running the application.

===============================================================================
"""


from Courseware.utils.agentic_LG import generate_learning_guide
from Courseware.utils.agentic_AP import generate_assessment_documents
from Courseware.utils.timetable_generator import generate_timetable
from Courseware.utils.agentic_LP import generate_lesson_plan
from Courseware.utils.agentic_FG import generate_facilitators_guide
from Courseware.utils.model_configs import MODEL_CHOICES, get_model_config
import os
import io
import zipfile
import tempfile
import json 
import time
import asyncio
from datetime import datetime
import streamlit as st
import urllib.parse
from selenium import webdriver
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from selenium import webdriver
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List, Optional
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from utils.helper import save_uploaded_file, parse_json_content
# Import organisation CRUD utilities and model
from Courseware.utils.organization_utils import (
    load_organizations,
    save_organizations,
    add_organization,
    update_organization,
    delete_organization,
    Organization
)
from streamlit_modal import Modal

# Initialize session state variables
if 'lg_output' not in st.session_state:
    st.session_state['lg_output'] = None
if 'ap_output' not in st.session_state:
    st.session_state['ap_output'] = None
if 'lp_output' not in st.session_state:
    st.session_state['lp_output'] = None
if 'fg_output' not in st.session_state:
    st.session_state['fg_output'] = None
if 'context' not in st.session_state:
    st.session_state['context'] = None
if 'asr_output' not in st.session_state:
    st.session_state['asr_output'] = None
if 'selected_model' not in st.session_state:
    st.session_state['selected_model'] = "Gemini-Pro-2.5-Exp-03-25"

############################################################
# 1. Pydantic Models
############################################################
class Topic(BaseModel):
    Topic_Title: str
    Bullet_Points: List[str]

class KDescription(BaseModel):
    K_number: str
    Description: str

class ADescription(BaseModel):
    A_number: str
    Description: str

class LearningUnit(BaseModel):
    LU_Title: str
    LU_Duration: str  # <-- Add this field
    Topics: List[Topic]
    LO: str
    K_numbering_description: List[KDescription]
    A_numbering_description: List[ADescription]
    Assessment_Methods: List[str]
    Instructional_Methods: List[str]

class EvidenceDetail(BaseModel):
    LO: str
    Evidence: str

class AssessmentMethodDetail(BaseModel):
    Assessment_Method: str
    Method_Abbreviation: str
    Total_Delivery_Hours: str
    Assessor_to_Candidate_Ratio: List[str]
    Evidence: Optional[List[EvidenceDetail]] = None
    Submission: Optional[List[str]] = None
    Marking_Process: Optional[List[str]] = None
    Retention_Period: Optional[str] = None

class CourseData(BaseModel):
    Date: str 
    Year: str
    Name_of_Organisation: str
    Course_Title: str
    TSC_Title: str
    TSC_Code: str
    Total_Training_Hours: str 
    Total_Assessment_Hours: str 
    Total_Course_Duration_Hours: str 
    Learning_Units: List[LearningUnit]
    Assessment_Methods_Details: List[AssessmentMethodDetail]

class Session(BaseModel):
    Time: str
    instruction_title: str
    bullet_points: List[str]
    Instructional_Methods: str
    Resources: str

class DayLessonPlan(BaseModel):
    Day: str
    Sessions: List[Session]

class LessonPlan(BaseModel):
    lesson_plan: List[DayLessonPlan]

############################################################
# 2. Course Proposal Document Parsing
############################################################
from llama_cloud_services import LlamaParse
from llama_index.core import SimpleDirectoryReader
import os
import re


import re
import json
from collections import deque
import copy
from datetime import datetime, timedelta

def parse_duration(duration_str):
    """Convert 'hr' or 'min' duration strings to minutes."""
    if 'hr' in duration_str:
        hours = float(duration_str.split()[0])
        return int(hours * 60)
    elif 'min' in duration_str:
        return int(duration_str.split()[0])
    return 0

def parse_time(time_str):
    """Extract time from string like '0935hrs'."""
    clean_time = re.sub(r'\s*\(.*?\)', '', time_str)
    start_time_str = clean_time.split('-')[0].strip().replace('hrs', '').strip()
    return datetime.strptime(start_time_str, '%H%M')

def format_time(dt):
    """Format datetime object to 'HHMMhrs'."""
    return dt.strftime('%H%M') + 'hrs'

def schedule_block(day_schedule, session_queue, start_time, end_time):
    """Schedule sessions within the available time block."""
    current_time = start_time
    # Ensure the session queue is not empty and the current time is before the end time
    while current_time < end_time and session_queue:
        # Get the first session from the queue and remaining time
        session = session_queue[0]
        remaining_time = (end_time - current_time).total_seconds() // 60

        # If the session fits within the remaining time, schedule it
        # Otherwise, split the session with remaining time
        if session['duration'] <= remaining_time:
            session = session_queue.popleft()
            end_session = current_time + timedelta(minutes=session['duration'])
        else:
            partial_session = copy.deepcopy(session)
            partial_session['duration'] = int(remaining_time)
            session['duration'] -= int(remaining_time)
            end_session = current_time + timedelta(minutes=remaining_time)
            session = partial_session

        session_entry = {
            'Time': f"{format_time(current_time)} - {format_time(end_session)} ({int((end_session - current_time).total_seconds() // 60)} mins)",
            'instruction_title': session['title'],
            'bullet_points': session['bullets'],
            'Instructional_Methods': session['Instructional_Methods'],
            'Resources': session['Resources'],
            'reference_line': session['reference_line']
        }

        day_schedule['Sessions'].append(session_entry)
        current_time = end_session
    return current_time

def fix_lesson_plan_compat(input_data):
    """
    Compatibility wrapper for fix_lesson_plan function.
    
    Args:
        input_data: Either a dictionary containing context data or JSON string
        
    Returns:
        Processed lesson plan data
    """
    # If input is already a dictionary, pass it directly
    if isinstance(input_data, dict):
        return fix_lesson_plan(input_data)
    
    # If input is a string, let the original function handle it
    elif isinstance(input_data, str):
        return fix_lesson_plan(input_data)
    
    # If it's something else, try to convert to dictionary first
    else:
        try:
            dict_data = dict(input_data)
            return fix_lesson_plan(dict_data)
        except (TypeError, ValueError):
            raise TypeError(f"Cannot convert input of type {type(input_data)} to dictionary")

def fix_lesson_plan(json_input):
    context = json.loads(json_input) if isinstance(json_input, str) else json_input

    session_reference_map = {}

    for day in context.get('lesson_plan', []):
        for session in day.get('Sessions', []):
            title = session.get('instruction_title', '').strip()
            if not title:
                continue
            session_reference_map[title] = {
                'reference_line': session.get('reference_line', 'Refer to some online references in Google Classroom LMS'),
                'Instructional_Methods': session.get('Instructional_Methods', 'Lecture'),
                'Resources': session.get('Resources', 'Slide pages, TV, Whiteboard, Wi-Fi')
            }
    
    # Builds a dictionary mapping topic titles to reference links (or a default message).
    #topic_references = {
    #    topic['Topic_Title']: topic.get('reference_line', 'Refer to some online references in Google Classroom LMS')
    #    for lu in context['Learning_Units'] for topic in lu['Topics']
    #}

    # Parse the LU durations and convert them to minutes
    for lu in context['Learning_Units']:
        lu['duration_mins'] = parse_duration(lu['LU_Duration'])
    
    session_queue = deque()

    for lu in context['Learning_Units']:
        topic_duration = lu['duration_mins'] // 2 // len(lu['Topics'])

        for topic in lu['Topics']:
            # Try to find a matching session from lesson plan
            topic_title = topic['Topic_Title']
            matching_session = next(
                (session_reference_map[s]
                for s in session_reference_map
                if topic_title.lower() in s.lower()),
                {
                    'reference_line': 'Refer to some online references in Google Classroom LMS',
                    'Instructional_Methods': 'Lecture, Didactic Questioning',
                    'Resources': 'Slide pages, TV, Whiteboard, Wi-Fi'
                }
            )

            session_queue.append({
                'type': 'topic',
                'title': topic_title,
                'duration': topic_duration,
                'bullets': topic['Bullet_Points'],
                'Instructional_Methods': matching_session['Instructional_Methods'],
                'Resources': matching_session['Resources'],
                'reference_line': matching_session['reference_line']
            })

        # Add activity block (fallback or match activity titles)
        activity_title = f"Activity:"
        matching_activity = next(
            (session_reference_map[s]
            for s in session_reference_map
            if activity_title.lower() in s.lower()),
            {
                'reference_line': 'Refer to some online practices in Google Classroom LMS',
                'Instructional_Methods': 'Demonstration, Practical Performance Practice',
                'Resources': 'Slide pages, TV, Wi-Fi'
            }
        )
        activity_title = f"Activity: {lu['LU_Title']}"

        session_queue.append({
            
            'type': 'activity',
            'title': activity_title,
            'duration': lu['duration_mins'] // 2,
            'bullets': [],
            'Instructional_Methods': matching_activity['Instructional_Methods'],
            'Resources': matching_activity['Resources'],
            'reference_line': matching_activity['reference_line']
        })

    days = []
    current_date = datetime.strptime(context['Date'], '%d %b %Y')
    day_count = 1

    #While there is still content in the queue, create a new day schedule.
    while session_queue or (not days and not session_queue):
        day_schedule = {'Day': f"Day {day_count}", 'Sessions': []}
        day_count += 1

        # Attendance session
        if day_count == 2:
            day_schedule['Sessions'].append({
                'Time': '0930hrs - 0935hrs (5 mins)',
                'instruction_title': 'Digital Attendance and Introduction to the Course',
                'bullet_points': ['Trainer Introduction', 'Learner Introduction', 'Overview of Course Structure'],
                'Instructional_Methods': 'N/A',
                'Resources': 'QR Attendance, Attendance Sheet',
                'reference_line': ''
            })
        else:
            day_schedule['Sessions'].append({
                'Time': '0930hrs - 0935hrs (5 mins)',
                'instruction_title': 'Digital Attendance (AM)',
                'bullet_points': [],
                'Instructional_Methods': 'N/A',
                'Resources': 'QR Attendance, Attendance Sheet',
                'reference_line': ''
            })

        # Schedule morning sessions from 0935 to 1200 by fitting as many sessions as possible
        schedule_block(day_schedule, session_queue, start_time=parse_time('0935'), end_time=parse_time('1200'))

        # Lunch
        day_schedule['Sessions'].append({
            'Time': '1200hrs - 1245hrs (45 mins)',
            'instruction_title': 'Lunch Break',
            'bullet_points': [],
            'Instructional_Methods': 'N/A',
            'Resources': 'N/A',
            'reference_line': ''
        })

        # Post-lunch with optional tea break
        post_lunch_start = parse_time('1245')
        post_lunch_end = parse_time('1825')
        current_time = post_lunch_start
        post_lunch_session_count = 0
        tea_break_inserted = False

        while current_time < post_lunch_end and session_queue:
            session = session_queue[0]
            remaining_time = (post_lunch_end - current_time).total_seconds() // 60

            # If the session fits within the remaining time, schedule it
            # Otherwise, split the session with remaining time
            if session['duration'] <= remaining_time:
                session = session_queue.popleft()
                end_session = current_time + timedelta(minutes=session['duration'])
            else:
                partial_session = copy.deepcopy(session)
                partial_session['duration'] = int(remaining_time)
                session['duration'] -= int(remaining_time)
                end_session = current_time + timedelta(minutes=remaining_time)
                session = partial_session

            session_entry = {
                'Time': f"{format_time(current_time)} - {format_time(end_session)} ({int((end_session - current_time).total_seconds() // 60)} mins)",
                'instruction_title': session['title'],
                'bullet_points': session['bullets'],
                'Instructional_Methods': session['Instructional_Methods'],
                'Resources': session['Resources'],
                'reference_line': session['reference_line']
            }
            # Add session to the day's schedule
            day_schedule['Sessions'].append(session_entry)
            current_time = end_session
            post_lunch_session_count += 1
            
            # Check if we need to insert a tea break
            if not tea_break_inserted and post_lunch_session_count == 1:
                tea_break_end = current_time + timedelta(minutes=5)
                if tea_break_end <= post_lunch_end:
                    day_schedule['Sessions'].append({
                        'Time': f"{format_time(current_time)} - {format_time(tea_break_end)} (5 mins)",
                        'instruction_title': 'Tea Break',
                        'bullet_points': [],
                        'Instructional_Methods': 'N/A',
                        'Resources': 'Refreshments',
                        'reference_line': ''
                    })
                    current_time = tea_break_end
                    tea_break_inserted = True

        # End of day scheduling
        # Check if we have any sessions left in the queue to indicate last day or not
        is_last_lu_day = not session_queue

        if not is_last_lu_day:
            current_time = schedule_block(day_schedule, session_queue, current_time, parse_time('1825'))
            day_schedule['Sessions'].append({
                'Time': '1825hrs - 1830hrs (5 mins)',
                'instruction_title': 'Recap All Contents and Close',
                'bullet_points': ['Summary of key learning points', 'Q&A'],
                'Instructional_Methods': 'Classroom Didactic Questioning, Practical Performance (PP)',
                'Resources': 'Slide pages, TV, Whiteboard, Wi-Fi',
                'reference_line': ''
            })
        else:
            if (parse_time('1830') - current_time).total_seconds() >= 600:
                feedback_end = current_time + timedelta(minutes=5)
                day_schedule['Sessions'].append({
                    'Time': f"{format_time(current_time)} - {format_time(feedback_end)} (5 mins)",
                    'instruction_title': 'Course Feedback and TRAQOM Survey',
                    'bullet_points': [],
                    'Instructional_Methods': 'N/A',
                    'Resources': 'Feedback Forms, Survey Links',
                    'reference_line': ''
                })
                current_time = feedback_end

            # Final assessment scheduling
            # Calculate total assessment time and available time
            total_assessment_time = sum(parse_duration(method['Total_Delivery_Hours']) for method in context['Assessment_Methods_Details'])
            available_time = (parse_time('1830') - current_time).total_seconds() / 60
            time_ratio = min(1, available_time / total_assessment_time) if total_assessment_time > 0 else 1

            for method in context['Assessment_Methods_Details']:
                duration = parse_duration(method['Total_Delivery_Hours']) * time_ratio
                if current_time >= parse_time('1830'):
                    break
                end_time = min(current_time + timedelta(minutes=duration), parse_time('1830'))
                session_duration = int((end_time - current_time).total_seconds() / 60)
                day_schedule['Sessions'].append({
                    'Time': f"{format_time(current_time)} - {format_time(end_time)} ({session_duration} mins)",
                    'instruction_title': "Final Assessment: " + method['Assessment_Method'],
                    'bullet_points': [],
                    'Instructional_Methods': 'Assessment',
                    'Resources': 'Assessment Plan',
                    'reference_line': ''
                })
                current_time = end_time

            # Stretch last session to 1830 if needed
            if current_time < parse_time('1830') and day_schedule['Sessions']:
                last_session = day_schedule['Sessions'][-1]
                start_str = last_session['Time'].split(' - ')[0]
                start_time = parse_time(start_str.replace('hrs', ''))
                duration_mins = int((parse_time('1830') - start_time).total_seconds() / 60)
                last_session['Time'] = f"{format_time(start_time)} - 1830hrs ({duration_mins} mins)"

        days.append(day_schedule)
        current_date += timedelta(days=1)

    return {'lesson_plan': days}

def parse_time_range(time_str):
    """
    Parse a string like '0930hrs - 0935hrs (5 mins)' into start time, end time (24h format without colon), and duration.
    """
    match = re.match(r'(\d{4})hrs - (\d{4})hrs \((\d+)\s+mins\)', time_str)
    if not match:
        return None, None, None

    start_str, end_str, duration_str = match.groups()
    # Return as HHMM strings without colon, e.g., '0930'
    starttime = start_str
    endtime = end_str
    duration = int(duration_str)
    return starttime, endtime, duration

def addstartendduration(data):
    for day in data['lesson_plan']:
        for session in day['Sessions']:
            start, end, duration = parse_time_range(session['Time'])
            session['starttime'] = start
            session['endtime'] = end
            session['duration'] = duration
            del session['Time']  # Remove original Time field
    return data

def renameactivity(lesson_plan_data):
    for day in lesson_plan_data['lesson_plan']:
        for session in day['Sessions']:
            title = session.get('instruction_title', '')
            # Check if the title starts with 'Activity: LUx:'
            match = re.match(r'(Activity: )LU\d+:(.*)', title)
            if match:
                prefix, rest = match.groups()
                instr_methods = session.get('Instructional_Methods', '').strip()
                # If Instructional_Methods is 'N/A' or empty, just remove LUx: part
                if instr_methods and instr_methods.upper() != 'N/A':
                    # Replace LUx with Instructional Methods + " on"
                    new_title = f"{prefix}{instr_methods} on{rest}"
                else:
                    # If no valid Instructional Methods, just remove LUx: and keep the rest
                    new_title = f"{prefix}{rest}"
                session['instruction_title'] = new_title.strip()
    return lesson_plan_data

def parse_cp_document(uploaded_file):
    """
    Parses a Course Proposal (CP) document (UploadedFile) and returns its content as Markdown text,
    trimmed based on the document type using regex patterns.

    For Word CP (.docx):
      - Excludes everything before a line matching "Part 1" and "Particulars of Course"
      - Excludes everything after a line matching "Part 4" and "Facilities and Resources"
    
    For Excel CP (.xlsx):
      - Excludes everything before a line matching "1 - Course Particulars"
      - Excludes everything after a line matching "3 - Summary"

    Args:
        uploaded_file (UploadedFile): The file uploaded via st.file_uploader.

    Returns:
        str: A trimmed Markdown string containing the parsed document content.
    """
    # Write the uploaded file to a temporary file.
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
        tmp.write(uploaded_file.read())
        temp_file_path = tmp.name

    try:
        # Set up parser for markdown result
        parser = LlamaParse(result_type="markdown", api_key=st.secrets["LLAMA_CLOUD_API_KEY"], 
        system_prompt_append=(
        "**IMPORTANT FOLLOW THE RULES OR YOU WILL FAIL**"
        "1.Extract the entire content of the document without omitting any text, including line breaks, paragraphs, and list items, in the exact order they appear. "
        "2.Parse tables into Markdown tables with the following specific rules:"
        "3. Ensure that the instructional methods column under curriculum table is flattened, meaning that if it contains multiple lines, they should be concatenated into a single line. "
        "4. When a table cell contains multiple lines, especially in the 'Instructional Methods' column, concatenate them as a single string, separated by commas. "
        "5. Never preserve newlines inside table cells in the output Markdown. "
        "6. For the curriculum table with columns like 'S/N', 'LUs', 'LOs*', and 'Instructional Methods', pay special attention to flatten all content in each cell. "
        "7. Ensure the output is a faithful and complete Markdown representation of the document."
        ))
        
    
        # Determine the file extension for mapping
        ext = os.path.splitext(temp_file_path)[1].lower()
        file_extractor = {ext: parser}
    
        # Use SimpleDirectoryReader to load and parse the file
        documents = SimpleDirectoryReader(input_files=[temp_file_path], file_extractor=file_extractor).load_data()
        print("Lllama Parser")
        print(documents)
    
        # Concatenate the parsed text from each Document object into a single Markdown string
        markdown_text = "\n\n".join(doc.text for doc in documents)
    
        # Set up regex patterns based on file extension
        if ext == ".docx":
            start_pattern = re.compile(r"Part\s*1.*?Particulars\s+of\s+Course", re.IGNORECASE)
            end_pattern = re.compile(r"Part\s*4.*?Facilities\s+and\s+Resources", re.IGNORECASE)
        elif ext == ".xlsx":
            start_pattern = re.compile(r"1\s*-\s*Course\s*Particulars", re.IGNORECASE)
            end_pattern = re.compile(r"4\s*-\s*Declarations", re.IGNORECASE)
        else:
            start_pattern = None
            end_pattern = None
    
        # If both patterns exist, search for the matches and trim the text
        if start_pattern and end_pattern:
            start_match = start_pattern.search(markdown_text)
            end_match = end_pattern.search(markdown_text)
            if start_match and end_match and end_match.start() > start_match.start():
                markdown_text = markdown_text[start_match.start():end_match.start()].strip()
    
    finally:
        # Clean up the temporary file
        os.remove(temp_file_path)
    
    return markdown_text

############################################################
# 2. Interpret Course Proposal Data
############################################################
async def interpret_cp(raw_data: dict, model_client: OpenAIChatCompletionClient) -> dict:
    """
    Interprets and extracts structured data from a raw Course Proposal (CP) document.

    This function processes raw CP data using an AI model to extract 
    structured information such as course details, learning units, topics, 
    assessment methods, and instructional methods.

    Args:
        raw_data (dict): 
            The unstructured data extracted from the CP document.
        model_client (OpenAIChatCompletionClient): 
            The AI model client used for structured data extraction.

    Returns:
        dict: 
            A structured dictionary containing course details.

    Raises:
        Exception: 
            If the AI-generated response does not contain the expected fields.
    """

    # Interpreter Agent with structured output enforcement
    interpreter = AssistantAgent(
        name="Interpreter",
        model_client=model_client,
        system_message=f"""
You are an AI assistant that helps extract specific information from a JSON object containing a Course Proposal Form (CP). Your task is to interpret the JSON data, regardless of its structure, and extract the required information accurately.

        ---
        
        **Task:** Extract the following information from the provided JSON data:

        ### Part 1: Particulars of Course

        - Name of Organisation
        - Course Title
        - TSC Title
        - TSC Code
        - Total Training Hours/ Total Instructional Duration (calculated as the sum of Classroom Facilitation, Workplace Learning: On-the-Job (OJT), Practicum, Practical, E-learning: Synchronous and Asynchronous), formatted with units (e.g., "30 hrs", "1 hr")
        - Total Assessment Hours/ Total Assessment Duration, formatted with units (e.g., "2 hrs")
        - Total Course Duration Hours, formatted with units (e.g., "42 hrs")

        ### Part 3: Curriculum Design

        From the Learning Units and Topics Table:

        For each Learning Unit (LU):
        - Learning Unit Title (include the "LUx: " prefix)
        - **Learning Unit Duration (LU_Duration)**: 
          * IMPORTANT: Calculate by summing ALL training duration columns for each LU:
          * CR e-learning + Sync e-Learning + Async e-Learning + PP Duration + OJT + any other duration columns
          * Example: If a Learning Unit has "CR e-learning: 2 hrs" and "PP: 2 hrs", the LU_Duration should be "4 hrs"
          * Convert all times to the same unit (hours) before summing
          * Format the final result with units (e.g., "3.5 hrs", "4 hrs")
        - Topics Covered Under Each LU:
        - For each Topic:
            - **Topic_Title** (include the "Topic x: " prefix and the associated K and A statements in parentheses)
            - **Bullet_Points** (a list of bullet points under the topic; remove any leading bullet symbols such as "-" so that only the content remains)
        - Learning Outcomes (LOs) (include the "LOx: " prefix for each LO)
        - Numbering and Description for the "K" (Knowledge) Statements (as a list of dictionaries with keys "K_number" and "Description")
        - Numbering and Description for the "A" (Ability) Statements (as a list of dictionaries with keys "A_number" and "Description")
        - **Assessment_Methods** (a list of assessment method abbreviations; e.g., ["WA-SAQ", "CS"]). Note: If the CP contains the term "Written Exam", output it as "Written Assessment - Short Answer Questions". If it contains "Practical Exam", output it as "Practical Performance".
        - **Duration Calculation:** When extracting the duration for each assessment method:
            1. If the extracted duration is not exactly 0.5 or a whole number (e.g., 0.5, 1, 2, etc.), interpret it as minutes.
            2. If duplicate entries for the same assessment method occur within the same LU, sum their durations to obtain a total duration.
            3. For CPs in Excel format, under 3 - Summary sheet, the duration appears in the format "(Assessor-to-Candidate Ratio, duration)"—for example, "Written Exam (1:20, 20)" means 20 minutes, and "Others: Case Study (1:20, 25)" appearing twice should result in a total of 50 minutes for Case Study.       
        - **Instructional_Methods** (a list of instructional method abbreviations or names)

        ### Part E: Details of Assessment Methods Proposed

        For each Assessment Method in the CP, extract:
        - **Assessment_Method** (always use the full term, e.g., "Written Assessment - Short Answer Questions", "Practical Performance", "Case Study", "Oral Questioning", "Role Play")
        - **Method_Abbreviation** (if provided in parentheses or generated according to the rules)
        - **Total_Delivery_Hours** (formatted with units, e.g., "1 hr")
        - **Assessor_to_Candidate_Ratio** (a list of minimum and maximum ratios, e.g., ["1:3 (Min)", "1:5 (Max)"])
        
        **Additionally, if the CP explicitly provides the following fields, extract them. Otherwise, do not include them in the final output:**
        - **Type_of_Evidence**  
        - For PP and CS assessment methods, the evidence may be provided as a dictionary where keys are LO identifiers (e.g., "LO1", "LO2", "LO3") and values are the corresponding evidence text. In that case, convert the dictionary into a list of dictionaries with keys `"LO"` and `"Evidence"`.  
        - If the evidence is already provided as a list (for example, a list of strings or a list of dictionaries), keep it as is.
        - **Manner_of_Submission** (as a list, e.g., ["Submission 1", "Submission 2"])
        - **Marking_Process** (as a list, e.g., ["Process 1", "Process 2"])
        - **Retention_Period**: **Extract the complete retention description exactly as provided in the CP.**
        - **No_of_Role_Play_Scripts** (only if the assessment method is Role Play and this information is provided)

        ---
        
        **Instructions:**
        
        - Carefully parse the JSON data and locate the sections corresponding to each part.
        - Even if the JSON structure changes, use your understanding to find and extract the required information.
        - Ensure that the `Topic_Title` includes the "Topic x: " prefix and the associated K and A statements in parentheses exactly as they appear.
        - For Learning Outcomes (LOs), always include the "LOx: " prefix (where x is the number).
        - Present the extracted information in a structured JSON format where keys correspond exactly to the placeholders required for the Word document template.
        - Ensure all extracted information is normalized by:
            - Replacing en dashes (–) and em dashes (—) with hyphens (-)
            - Converting curly quotes (" ") to straight quotes (")
            - Replacing other non-ASCII characters with their closest ASCII equivalents.
        - **Time fields** must include units (e.g., "40 hrs", "1 hr", "2 hrs").
        - For `Assessment_Methods`, always use the abbreviations (e.g., WA-SAQ, PP, CS, OQ, RP) as per the following rules:
            1. Use the abbreviation provided in parentheses if available.
            2. Otherwise, generate an abbreviation by taking the first letters of the main words (ignoring articles/prepositions) and join with hyphens.
            3. For methods containing "Written Assessment", always prefix with "WA-".
            4. If duplicate or multiple variations exist, use the standard abbreviation.
        - **Important:** Verify that the sum of `Total_Delivery_Hours` for all assessment methods equals the `Total_Assessment_Hours`. If individual delivery hours for assessment methods are not specified, divide the `Total_Assessment_Hours` equally among them.
        - For bullet points in each topic, ensure that the number of bullet points exactly matches those in the CP. Re-extract if discrepancies occur.
        - **If the same K or A statement (same numbering and description) appears multiple times within the same LU, keep only one instance. If the same K or A statement appears in different LUs, keep it as it is.**
        - Do not include any extraneous information or duplicate entries.

        Generate structured output matching this schema:
        {json.dumps(CourseData.model_json_schema(), indent=2)}
        """,
    )

    agent_task = f"""
    Please extract and structure the following data: {raw_data}.
    **Return the extracted information as a complete JSON dictionary containing the specified fields. Do not truncate or omit any data. Include all fields and their full content. Do not use '...' or any placeholders to replace data.**
    Simply return the JSON dictionary object directly.
    """

    # Process sample input
    response = await interpreter.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )
    if not response or not response.chat_message:
        return "No content found in the agent's last message."
    # print(response.chat_message.content)
    # return response.chat_message.content

    context = parse_json_content(response.chat_message.content)
    return context

# Streamlit App
def app():
    """
    Streamlit web application for generating courseware documents.

    This function serves as the entry point for the user interface,
    allowing users to upload a Course Proposal document, select 
    their organization, and generate various courseware documents.

    The app guides users through:
    - Uploading a Course Proposal (CP) document.
    - Selecting an organization from a predefined list.
    - Uploading an optional updated Skills Framework (SFw) dataset.
    - Selecting documents to generate (Learning Guide, Lesson Plan, etc.).
    - Processing and downloading the generated documents.

    Raises:
        ValueError: 
            If required input fields are missing.
        Exception: 
            If any step in the document generation process fails.
    """

    st.title("📄 Courseware Document Generator")
    
    # ================================================================
    # MODEL SELECTION FEATURE
    # ================================================================
    st.subheader("Model Selection")
    model_choice = st.selectbox(
        "Select LLM Model:",
        options=list(MODEL_CHOICES.keys()),
        index=0 # Select Default
    )
    st.session_state['selected_model'] = model_choice

    # ================================================================
    # Step 1: Upload Course Proposal (CP) Document
    # ================================================================
    st.subheader("Step 1: Upload Course Proposal (CP) Document")
    cp_file = st.file_uploader("Upload Course Proposal (CP) Document", type=["docx, xlsx"])

    # ================================================================
    # Step 2: Select Name of Organisation
    # ================================================================
    # Create a modal instance with a unique key and title
    crud_modal = Modal(key="crud_modal", title="Manage Organisations")

    st.subheader("Step 2: Enter Relevant Details")
    tgs_course_code = st.text_input("Enter TGS Course Code", key="tgs_course_code", placeholder="e.g., TGS-2023039181")

    col1, col2 = st.columns([0.8, 0.2], vertical_alignment="center")
    # Load organisations from JSON using the utility function
    org_list = load_organizations()
    org_names = [org["name"] for org in org_list] if org_list else []
    with col1:
        if org_names:
            selected_org = st.selectbox("Select Name of Organisation", org_names, key="org_dropdown_main")
        else:
            selected_org = st.selectbox("Select Name of Organisation", [], key="org_dropdown_main")
            st.warning("No organisations found. Click 'Manage' to add organisations.")

    with col2:
        # Wrap the Manage button in a div that uses flexbox for vertical centering.
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("Manage", key="manage_button", use_container_width=True):
            crud_modal.open()

    # ---------------------------
    # Modal: CRUD Interface
    # ---------------------------
    if crud_modal.is_open():
        with crud_modal.container():
            
            # ---- Add New Organisation Form ----
            st.write("#### Add New Organisation")
            with st.form("new_org_form"):
                new_name = st.text_input("Organisation Name", key="new_org_name")
                new_uen = st.text_input("UEN", key="new_org_uen")
                # Use file uploader for the logo instead of a text input
                new_logo_file = st.file_uploader("Upload Logo (optional)", type=["png", "jpg", "jpeg"], key="new_org_logo_file")
                new_submitted = st.form_submit_button("Add Organisation")
                if new_submitted:
                    logo_path = None
                    if new_logo_file is not None:
                        # Construct a safe filename based on the organisation name and file extension
                        _, ext = os.path.splitext(new_logo_file.name)
                        safe_filename = new_name.lower().replace(" ", "_") + ext
                        save_path = os.path.join("Courseware", "utils", "logo", safe_filename)
                        with open(save_path, "wb") as f:
                            f.write(new_logo_file.getvalue())
                        logo_path = save_path
                    new_org = Organization(name=new_name, uen=new_uen, logo=logo_path)
                    add_organization(new_org)
                    st.success(f"Organisation '{new_name}' added.")
                    st.rerun()
            
            # ---- Display Existing Organisations with Edit/Delete Buttons ----
            st.write("#### Existing Organisations")
            org_list = load_organizations()  # Refresh the list

            # Table header
            col_sno, col_name, col_uen, col_logo, col_edit, col_delete = st.columns([1, 3, 2, 2, 1, 2])
            col_sno.markdown("**SNo**")
            col_name.markdown("**Name**")
            col_uen.markdown("**UEN**")
            col_logo.markdown("**Logo**")
            col_edit.markdown("**Edit**")
            col_delete.markdown("**Delete**")

            # Table rows
            for display_idx, org in enumerate(org_list, start=1):
                # The actual index in the list is display_idx - 1
                real_index = display_idx - 1

                row_sno, row_name, row_uen, row_logo, row_edit, row_delete = st.columns([1, 3, 2, 2, 1, 2])
                row_sno.write(display_idx)
                row_name.write(org["name"])
                row_uen.write(org["uen"])
                
                if org["logo"] and os.path.exists(org["logo"]):
                    row_logo.image(org["logo"], width=70)
                else:
                    row_logo.write("No Logo")

                # Edit/Delete Buttons
                if row_edit.button("Edit", key=f"edit_{display_idx}", type="secondary"):
                    st.session_state["org_edit_index"] = real_index
                    st.rerun()
                if row_delete.button("Delete", key=f"delete_{display_idx}", type="primary"):
                    if org["logo"] and os.path.exists(org["logo"]):
                        os.remove(org["logo"])
                    delete_organization(real_index)
                    st.success(f"Organisation '{org['name']}' deleted.")
                    st.rerun()

            # ---- Edit Organisation Form (if a row is selected for editing) ----
            if "org_edit_index" in st.session_state:
                edit_index = st.session_state["org_edit_index"]
                org_to_edit = load_organizations()[edit_index]
                st.write(f"#### Edit Organisation: {org_to_edit['name']}")
                with st.form("edit_org_form"):
                    edited_name = st.text_input("Organisation Name", value=org_to_edit["name"], key="edited_name")
                    edited_uen = st.text_input("UEN", value=org_to_edit["uen"], key="edited_uen")
                    # File uploader for updating the logo image
                    edited_logo_file = st.file_uploader("Upload Logo (optional)", type=["png", "jpg", "jpeg"], key="edited_logo_file")
                    edit_submitted = st.form_submit_button("Update Organisation")
                    if edit_submitted:
                        logo_path = org_to_edit.get("logo", None)
                        if edited_logo_file is not None:
                            _, ext = os.path.splitext(edited_logo_file.name)
                            safe_filename = edited_name.lower().replace(" ", "_") + ext
                            save_path = os.path.join("Courseware", "utils", "logo", safe_filename)
                            with open(save_path, "wb") as f:
                                f.write(edited_logo_file.getvalue())
                            logo_path = save_path
                        updated_org = Organization(name=edited_name, uen=edited_uen, logo=logo_path)
                        update_organization(edit_index, updated_org)
                        st.success(f"Organisation '{edited_name}' updated.")
                        del st.session_state["org_edit_index"]
                        st.rerun()

    # ================================================================
    # Step 3 (Optional): Upload Updated SFW Dataset
    # ================================================================
    st.subheader("Step 3 (Optional): Upload Updated Skills Framework (SFw) Dataset")
    sfw_file = st.file_uploader("Upload Updated SFw Dataset (Excel File)", type=["xlsx"])
    if sfw_file:
        sfw_data_dir = save_uploaded_file(sfw_file, 'input/dataset')
        st.success(f"Updated SFw dataset saved to {sfw_data_dir}")
    else:
        sfw_data_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"

    # ================================================================
    # Step 4: Select Document(s) to Generate using Checkboxes
    # ================================================================
    st.subheader("Step 4: Select Document(s) to Generate")
    generate_lg = st.checkbox("Learning Guide (LG)")
    generate_ap = st.checkbox("Assessment Plan (AP)")
    generate_lp = st.checkbox("Lesson Plan (LP)")
    generate_fg = st.checkbox("Facilitator's Guide (FG)")

    # ================================================================
    # Step 5: Generate Documents
    # ================================================================
    if st.button("Generate Documents"):
        if cp_file is not None and selected_org:
            # Reset previous output document paths
            st.session_state['lg_output'] = None
            st.session_state['ap_output'] = None
            st.session_state['asr_output'] = None
            st.session_state['lp_output'] = None
            st.session_state['fg_output'] = None
            # Use the selected model configuration for all autogen agents
            selected_config = get_model_config(st.session_state['selected_model'])
            api_key = selected_config["config"].get("api_key")
            if not api_key:
                st.error("API key for the selected model is not provided.")
                return
            model_name = selected_config["config"]["model"]
            temperature = selected_config["config"].get("temperature", 0)
            base_url = selected_config["config"].get("base_url", None)

            # Extract model_info from the selected configuration (if provided)
            model_info = selected_config["config"].get("model_info", None)

            # Conditionally set response_format: use structured output only for valid OpenAI models.
            if st.session_state['selected_model'] in ["DeepSeek-V3", "Gemini-Pro-2.5-Exp-03-25"]:
                cp_response_format = None  # DeepSeek and Gemini might not support structured output this way.
                lp_response_format = None
            else:
                cp_response_format = CourseData  # For structured CP extraction
                lp_response_format = LessonPlan  # For timetable generation

            openai_struct_model_client = OpenAIChatCompletionClient(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                base_url=base_url,
                response_format=cp_response_format,  # Only set for valid OpenAI models
                model_info=model_info,
            )

            timetable_openai_struct_model_client = OpenAIChatCompletionClient(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                base_url=base_url,
                response_format=lp_response_format,
                model_info=model_info,
            )

            openai_model_client = OpenAIChatCompletionClient(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                base_url=base_url,
                model_info=model_info,
            )

            # Step 1: Parse the CP document
            try:
                with st.spinner('Parsing the Course Proposal...'):
                    raw_data = parse_cp_document(cp_file)
                    #New!Check output
                    print("Raw data:")
                    print(raw_data)
            except Exception as e:
                st.error(f"Error parsing the Course Proposal: {e}")
                return
            
            try:
                with st.spinner('Extracting Information from Course Proposal...'):
                    context = asyncio.run(interpret_cp(raw_data=raw_data, model_client=openai_struct_model_client))
                    print("Extracted Context:")
                    print(context)

            except Exception as e:
                st.error(f"Error extracting Course Proposal: {e}")
                return

            # After obtaining the context
            if context:
                # Step 2: Add the current date to the raw_data
                current_datetime = datetime.now()
                current_date = current_datetime.strftime("%d %b %Y")
                year = current_datetime.year
                context["Date"] = current_date
                context["Year"] = year
                # Find the selected organisation UEN in the organisation's record
                selected_org_data = next((org for org in org_list if org["name"] == selected_org), None)
                if selected_org_data:
                    context["UEN"] = selected_org_data["uen"]

                tgs_course_code = st.session_state.get("tgs_course_code", "")
                context["TGS_Ref_No"] = tgs_course_code

                st.session_state['context'] = context  # Store context in session state

                # Generate Learning Guide
                if generate_lg:
                    try:
                        with st.spinner('Generating Learning Guide...'):
                            lg_output = generate_learning_guide(context, selected_org, openai_model_client)
                        if lg_output:
                            st.success(f"Learning Guide generated: {lg_output}")
                            st.session_state['lg_output'] = lg_output  # Store output path in session state
                    except Exception as e:
                        st.error(f"Error generating Learning Guide: {e}")

                # Generate Assessment Plan
                if generate_ap:
                    try:
                        with st.spinner('Generating Assessment Plan and Assessment Summary Record...'):
                            ap_output, asr_output = generate_assessment_documents(context, selected_org)
                        if ap_output:
                            st.success(f"Assessment Plan generated: {ap_output}")
                            st.session_state['ap_output'] = ap_output  # Store output path in session state

                        if asr_output:
                            st.success(f"Assessment Summary Record generated: {asr_output}")
                            st.session_state['asr_output'] = asr_output  # Store output path in session state

                    except Exception as e:
                        st.error(f"Error generating Assessment Documents: {e}")

                # Check if any documents require the timetable
                needs_timetable = (generate_lp or generate_fg)

                # Generate the timetable if needed and not already generated
                if needs_timetable and 'lesson_plan' not in context:
                    try:
                        with st.spinner("Generating Timetable..."):
                            hours = int(''.join(filter(str.isdigit, context["Total_Course_Duration_Hours"])))
                            num_of_days = hours / 8
                            timetable_data = asyncio.run(generate_timetable(context, num_of_days, timetable_openai_struct_model_client))
                            context['lesson_plan'] = timetable_data['lesson_plan']
                        st.session_state['context'] = context  # Update context in session state
                    except Exception as e:
                        st.error(f"Error generating timetable: {e}")
                        return  # Exit if timetable generation fails
                    
                # Now generate Lesson Plan
                if generate_lp:
                    try:
                        with st.spinner("Generating Lesson Plan..."):
                            print("Context for LP:")
                            print(context)
                            # After generating the initial timetable
                            #if 'lesson_plan' in context:
                            #    # Optimize the timetable to ensure proper LU duration utilization
                            #    context = optimize_timetable(context)
                            #print("Optimized Context for LP:")
                            #print(context['lesson_plan'])
                            temporary_lesson_plan = fix_lesson_plan_compat(context)
                            print("Temporary Fixed Lesson Plan:")
                            print(temporary_lesson_plan)
                            print("Add Start End and Duration to Lesson Plan")
                            temporary_lesson_plan = addstartendduration(temporary_lesson_plan)
                            print("Lesson Plan with fixed activity name")
                            temporary_lesson_plan = renameactivity(temporary_lesson_plan)
                            print(temporary_lesson_plan)
                            context['lesson_plan'] = temporary_lesson_plan
                            print("Context for LP after fixing:")
                            print(context)
                            
                            
                            lp_output = generate_lesson_plan(context, selected_org)
                        if lp_output:
                            st.success(f"Lesson Plan generated: {lp_output}")
                            st.session_state['lp_output'] = lp_output  # Store output path in session state
     
                    except Exception as e:
                        st.error(f"Error generating Lesson Plan: {e}")

                # Generate Facilitator's Guide
                if generate_fg:
                    try:
                        with st.spinner("Generating Facilitator's Guide..."):
                            fg_output = generate_facilitators_guide(context, selected_org)
                        if fg_output:
                            st.success(f"Facilitator's Guide generated: {fg_output}")
                            st.session_state['fg_output'] = fg_output  # Store output path in session state

                    except Exception as e:
                        st.error(f"Error generating Facilitator's Guide: {e}")
            else:
                st.error("Context is empty. Cannot proceed with document generation.")
        else:
            st.error("Please upload a CP document and select a Name of Organisation.")

    # Check if any courseware document was generated
    if any([
        st.session_state.get('lg_output'),
        st.session_state.get('ap_output'),
        st.session_state.get('asr_output'),
        st.session_state.get('lp_output'),
        st.session_state.get('fg_output')
    ]):
        st.subheader("Download All Generated Documents as ZIP")

        # Create an in-memory ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            
            # Helper function to add a file to the zip archive
            def add_file(file_path, prefix):
                if file_path and os.path.exists(file_path):
                    # Determine file name based on TGS_Ref_No (if available) or fallback to course title
                    if 'TGS_Ref_No' in st.session_state['context'] and st.session_state['context']['TGS_Ref_No']:
                        file_name = f"{prefix}_{st.session_state['context']['TGS_Ref_No']}_{st.session_state['context']['Course_Title']}_v1.docx"
                    else:
                        file_name = f"{prefix}_{st.session_state['context']['Course_Title']}_v1.docx"
                    zipf.write(file_path, arcname=file_name)
            
            # Add each generated document if it exists
            add_file(st.session_state.get('lg_output'), "LG")
            add_file(st.session_state.get('ap_output'), "Assessment_Plan")
            add_file(st.session_state.get('asr_output'), "Assessment_Summary_Record")
            add_file(st.session_state.get('lp_output'), "LP")
            add_file(st.session_state.get('fg_output'), "FG")
        
        # Reset the buffer's position to the beginning
        zip_buffer.seek(0)
        
        # Create a download button for the ZIP archive
        st.download_button(
            label="Download All Documents (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="courseware_documents.zip",
            mime="application/zip"
        )