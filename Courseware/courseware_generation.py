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
from pathlib import Path
import logging
import json 
import time
import asyncio
from datetime import datetime, timedelta
import re
import copy
from collections import defaultdict

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

def round_to_nearest_5(duration, round_type='down'):
    """
    Round duration (in minutes) to the nearest multiple of 5.
    
    Args:
        duration: Duration in minutes
        round_type: 'down' or 'up' to specify rounding direction
        
    Returns:
        (rounded_duration, leftover_minutes)
    """
    if round_type == 'down':
        rounded = (duration // 5) * 5
        leftover = duration - rounded
    else:  # round up
        rounded = ((duration + 4) // 5) * 5
        leftover = rounded - duration
    
    return rounded, leftover

def parse_duration(duration_str):
    """Convert 'hr' or 'min' duration strings to minutes."""
    if 'hr' in duration_str:
        hours = float(duration_str.split()[0])
        return int(hours * 60)
    elif 'min' in duration_str:
        return int(duration_str.split()[0])
    return 0

def parse_time(time_str):
    """Extract time from string like '0935hrs' or '0935'."""
    clean_time = re.sub(r'\s*\(.*?\)', '', time_str) # remove (xx mins)
    time_part = clean_time.split('-')[0].strip().replace('hrs', '').strip()
    if len(time_part) == 4 and time_part.isdigit():
        return datetime.strptime(time_part, '%H%M')
    return None # Should not happen if AI follows format

def format_time(dt_object):
    """Format datetime object to 'HHMMhrs'."""
    return dt_object.strftime('%H%Mhrs')

def format_duration_string(minutes):
    if not isinstance(minutes, (int, float)) or minutes < 0:
        return "0min" # Default or error string
    minutes = int(minutes)
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}hr {mins}min"
    elif hours > 0:
        return f"{hours}hr"
    else:
        return f"{mins}min"

def fix_lesson_plan_compat(input_data):
    if isinstance(input_data, str):
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON input string for fix_lesson_plan_compat")
    elif isinstance(input_data, dict):
        data = input_data
    else:
        raise TypeError(f"Cannot process input of type {type(input_data)} for fix_lesson_plan_compat. Expected dict or JSON string.")

    if 'lesson_plan' in data and 'Learning_Units' in data:
        return fix_lesson_plan(data) 
    elif 'lesson_plan' in data: 
        st.info("fix_lesson_plan_compat: Input seems to be lesson_plan only. LU duration validation will be skipped.")
        return fix_lesson_plan(data) 
    elif 'Learning_Units' in data: 
        st.warning("fix_lesson_plan_compat: Input has Learning_Units but no 'lesson_plan' key. AI might have failed to generate it.")
        return fix_lesson_plan(data)
    else:
        st.error("fix_lesson_plan_compat: Input data does not contain 'lesson_plan' or 'Learning_Units'. Cannot proceed.")
        return {"lesson_plan": []}


def _get_lu_id_from_title(title_str):
    if not title_str: return None
    # Look for "LU<number>", "LU <number>", "Learning Unit <number>"
    # Also try to catch "Topic X of LUY", "Activity for LUY"
    match = re.search(r'(?:LU|Learning Unit)\s*(\d+)|(?:Topic\s*\w+\s*(?:of|for)?\s*LU(\d+))|(?:Activity\s*(?:for|on)?\s*LU(\d+))', title_str, re.IGNORECASE)
    if match:
        # Return the first non-None capturing group
        return next((g for g in match.groups() if g is not None), None)
    return None

def check_start_end_duration(lesson_plan):
    """
    For each session in the lesson plan, check that starttime + duration = endtime.
    Warn if any mismatch is found.
    """
    import streamlit as st
    from datetime import datetime, timedelta
    def parse_time_str(t):
        if not t or len(t) != 4 or not t.isdigit():
            return None
        return datetime.strptime(t, "%H%M")
    def parse_duration_str(d):
        if not d:
            return 0
        d = d.lower()
        hr = 0
        mn = 0
        hr_match = re.search(r"(\d+)hr", d)
        min_match = re.search(r"(\d+)min", d)
        if hr_match:
            hr = int(hr_match.group(1))
        if min_match:
            mn = int(min_match.group(1))
        return hr * 60 + mn
    for day_idx, day in enumerate(lesson_plan.get('lesson_plan', [])):
        for session_idx, session in enumerate(day.get('Sessions', [])):
            start = session.get('starttime')
            end = session.get('endtime')
            duration = session.get('duration')
            if start and end and duration:
                start_dt = parse_time_str(start)
                end_dt = parse_time_str(end)
                dur_min = parse_duration_str(duration)
                if start_dt and end_dt:
                    calc_end = start_dt + timedelta(minutes=dur_min)
                    if calc_end != end_dt:
                        st.warning(f"Day {day_idx+1}, Session {session_idx+1} ('{session.get('instruction_title','')}'): starttime {start}, duration {duration} => {calc_end.strftime('%H%M')}, but endtime is {end}. Mismatch.")

def fix_lesson_plan(data_input_context):
    if isinstance(data_input_context, str):
        try:
            context = json.loads(data_input_context)
        except json.JSONDecodeError:
            st.error("Error: Invalid JSON input to fix_lesson_plan.")
            return {"lesson_plan": []}
    elif isinstance(data_input_context, dict):
        context = data_input_context
    else:
        st.error(f"Error: Invalid input type to fix_lesson_plan: {type(data_input_context)}.")
        return {"lesson_plan": []}

    if 'lesson_plan' in context and isinstance(context.get('lesson_plan'), list):
        processed_lesson_plan = {"lesson_plan": copy.deepcopy(context['lesson_plan'])}
    elif isinstance(context, list) and all(isinstance(d, dict) and "Day" in d and "Sessions" in d for d in context):
        st.info("Interpreting input 'context' directly as the list of lesson plan days, as 'lesson_plan' key was missing or invalid.")
        processed_lesson_plan = {"lesson_plan": copy.deepcopy(context)}
    else:
        st.error("Critical Error: Lesson plan structure is missing, malformed, or input 'context' is not a valid fallback.")
        return {"lesson_plan": []}

    # --- Robustness Checks Setup ---
    learning_units_data = context.get('Learning_Units')
    lu_target_durations = {}
    if learning_units_data and isinstance(learning_units_data, list):
        for lu_item in learning_units_data:
            lu_title_from_manifest = lu_item.get('LU_Title')
            lu_id_from_manifest = _get_lu_id_from_title(lu_title_from_manifest)
            if lu_id_from_manifest:
                lu_target_durations[lu_id_from_manifest] = parse_duration(lu_item.get('LU_Duration', "0min"))
            else:
                st.warning(f"Could not parse LU ID from Learning_Units manifest item: '{lu_title_from_manifest}'. This LU cannot be duration-checked.")
    else:
        st.warning("fix_lesson_plan: 'Learning_Units' not found in context or is not a list. LU duration adherence check will be skipped.")

    lu_actual_durations = defaultdict(int)
    forbidden_activity_ims = ["lecture", "group discussion", "peer sharing"]
    
    # --- Main Processing Loop with Robustness Checks ---
    for day_idx, day_schedule in enumerate(processed_lesson_plan.get('lesson_plan', [])):
        current_time_dt = None
        lunch_occurred_today = False
        
        for session_idx, session in enumerate(day_schedule.get('Sessions', [])):
            title = session.get('instruction_title', '')
            title_lower = title.lower()
            instructional_methods_str = session.get('Instructional_Methods', '').lower()
            resources_str = session.get('Resources', '').lower()
            # Get original case for reference_line for accurate heuristic checks if needed
            reference_line_original = session.get('reference_line', '') 
            reference_line_lower = reference_line_original.lower()
            bullet_points = session.get('bullet_points', [])
            start_str = session.get('starttime')
            duration_str = session.get('duration')
            
            session_duration_minutes = 0
            if duration_str:
                hours = 0; minutes_val = 0
                hr_match = re.search(r'(\d+)hr', duration_str)
                min_match = re.search(r'(\d+)min', duration_str)
                if hr_match: hours = int(hr_match.group(1))
                if min_match: minutes_val = int(min_match.group(1))
                session_duration_minutes = (hours * 60) + minutes_val
            elif start_str and session.get('endtime'):
                start_dt_temp = parse_time(start_str)
                end_dt_temp = parse_time(session.get('endtime'))
                if start_dt_temp and end_dt_temp:
                    session_duration_minutes = int((end_dt_temp - start_dt_temp).total_seconds() // 60)
            
            if session_duration_minutes == 0 and not any(keyword in title_lower for keyword in ['break', 'attendance', 'introduction', 'course overview', 'feedback', 'traqom', 'assessment']):
                 st.warning(f"Day {day_idx+1}, Session {session_idx+1} ('{title}') has 0 duration or invalid time fields, and is not a typical non-timed event.")

            is_tea_break = 'tea break' in title_lower
            if not is_tea_break and session_duration_minutes % 15 != 0:
                st.warning(f"Day {day_idx+1}, Session '{title}' duration {session_duration_minutes}m is not a multiple of 15.")
            if is_tea_break and session_duration_minutes != 10:
                 st.warning(f"Day {day_idx+1}, Tea Break duration is {session_duration_minutes}m, expected 10m.")

            start_dt = None # Define start_dt here for broader scope within session loop
            if start_str:
                start_dt = parse_time(start_str)
                if start_dt:
                    if current_time_dt and start_dt != current_time_dt:
                        st.warning(f"Day {day_idx+1}, Session '{title}': Start time {start_str} does not match previous end time {format_time(current_time_dt)}.")
                    calculated_end_dt = start_dt + timedelta(minutes=session_duration_minutes)
                    session['starttime'] = start_dt.strftime('%H%M')
                    session['endtime'] = calculated_end_dt.strftime('%H%M')
                    session['duration'] = format_duration_string(session_duration_minutes)
                    current_time_dt = calculated_end_dt
                else:
                    st.warning(f"Day {day_idx+1}, Session '{title}': Invalid starttime format '{start_str}'.")
                    current_time_dt = None
            elif current_time_dt:
                st.warning(f"Day {day_idx+1}, Session '{title}': Missing starttime. Inferring from previous session.")
                start_dt = current_time_dt
                session['starttime'] = current_time_dt.strftime('%H%M')
                calculated_end_dt = current_time_dt + timedelta(minutes=session_duration_minutes)
                session['endtime'] = calculated_end_dt.strftime('%H%M')
                session['duration'] = format_duration_string(session_duration_minutes)
                current_time_dt = calculated_end_dt
            else:
                st.error(f"Day {day_idx+1}, Session '{title}': Missing starttime and no previous time to infer from.")
                current_time_dt = None
            
            if not isinstance(session.get('bullet_points'), list):
                session['bullet_points'] = []
            if 'reference_line' not in session:
                session['reference_line'] = ""

            # --- Start of Specific Robustness Checks for this session ---
            lu_id_for_session = _get_lu_id_from_title(title)
            is_content_session = not any(keyword in title_lower for keyword in ['break', 'assessment', 'feedback', 'traqom', 'attendance', 'introduction', 'course overview'])
            if lu_id_for_session and is_content_session:
                lu_actual_durations[lu_id_for_session] += session_duration_minutes
            elif not lu_id_for_session and is_content_session and not title_lower.startswith('activity:'):
                st.warning(f"Day {day_idx+1}, Session '{title}' seems like LU content but LU ID could not be parsed from title.")

            if title_lower.startswith('activity:'):
                for forbidden_im in forbidden_activity_ims:
                    if forbidden_im in instructional_methods_str:
                        st.warning(f"Day {day_idx+1}, Activity '{title}' uses forbidden IM: '{instructional_methods_str}'.")
                        break

            if day_idx == 0 and session_idx == 0:
                if "digital attendance and introduction to the course" not in title_lower:
                    st.warning(f"Day 1, Session 1: Title should be 'Digital Attendance and Introduction to the Course', got '{title}'.")
                if session_duration_minutes != 15:
                    st.warning(f"Day 1, Session 1: Duration should be 15 mins, got {session_duration_minutes}m.")
                if "qr attendance" not in resources_str or "attendance sheet" not in resources_str:
                    st.warning(f"Day 1, Session 1: Missing 'QR Attendance' or 'Attendance Sheet' in resources ('{session.get('Resources')}').")
                if not any("trainer introduction" in bp.lower() for bp in bullet_points) or \
                   not any("learner introduction" in bp.lower() for bp in bullet_points) or \
                   not any("overview of course structure" in bp.lower() for bp in bullet_points):
                    st.warning(f"Day 1, Session 1: Missing one or more required bullet points (Trainer/Learner Intro, Overview).")
            else:
                is_am_attendance_topic = title_lower.startswith("digital attendance (am) & topic")
                is_pm_attendance_topic = title_lower.startswith("digital attendance (pm) & topic")
                if is_am_attendance_topic and ("qr attendance" not in resources_str or "attendance sheet" not in resources_str):
                    st.warning(f"Day {day_idx+1}, Session '{title}': AM attendance topic missing 'QR Attendance' or 'Attendance Sheet' in resources.")
                if is_pm_attendance_topic and "digital attendance (pm)" not in resources_str:
                    st.warning(f"Day {day_idx+1}, Session '{title}': PM attendance topic missing 'Digital Attendance (PM)' in resources.")

            if is_content_session:
                if "lecture" in instructional_methods_str and "refer to online references" not in reference_line_lower:
                    st.warning(f"Day {day_idx+1}, Session '{title}': Lecture session has unusual reference line: '{reference_line_original}'.")
                if "case study" in instructional_methods_str and "refer to some online case stud" not in reference_line_lower:
                    st.warning(f"Day {day_idx+1}, Session '{title}': Case Study session has unusual reference line: '{reference_line_original}'.")

            if title_lower == 'lunch break':
                lunch_occurred_today = True
                if start_dt:
                    if not (datetime.strptime("11:30", "%H:%M").time() <= start_dt.time() <= datetime.strptime("13:00", "%H:%M").time()):
                        st.warning(f"Day {day_idx+1}, Lunch Break at {start_dt.strftime('%H%M')} is outside the 11:30-13:00 window.")

            if is_tea_break and not lunch_occurred_today:
                st.warning(f"Day {day_idx+1}, Tea Break ('{title}') scheduled before Lunch.")

            if "recap all contents and close" in title_lower:
                st.warning(f"Day {day_idx+1}, Session '{title}' is a Recap session, which should be removed as per requirements.")
        
    # --- End of All Days Robustness Checks (LU Duration and Feedback/TRAQOM) ---
    if lu_target_durations: 
        for lu_id, target_duration in lu_target_durations.items():
            actual_duration = lu_actual_durations.get(lu_id, 0)
            if actual_duration != target_duration:
                st.warning(f"LU {lu_id}: Target duration {format_duration_string(target_duration)} ({target_duration}m), but actual summed duration for topics/activities is {format_duration_string(actual_duration)} ({actual_duration}m). Mismatch of {format_duration_string(target_duration - actual_duration)}.")
        for lu_id, actual_duration in lu_actual_durations.items():
            if lu_id not in lu_target_durations:
                st.warning(f"Found sessions potentially for LU ID '{lu_id}' (total {format_duration_string(actual_duration)}m from topics/activities) but this LU ID was not found in the Learning_Units manifest for duration checking.")
    
    if processed_lesson_plan.get('lesson_plan') and len(processed_lesson_plan['lesson_plan']) > 0:
        last_day_sessions = processed_lesson_plan['lesson_plan'][-1].get('Sessions', [])
        if last_day_sessions:
            assessment_session_indices = [i for i, s in enumerate(last_day_sessions) if "final assessment" in s.get('instruction_title','').lower()]
            if assessment_session_indices:
                first_assessment_idx = min(assessment_session_indices)
                if first_assessment_idx > 0:
                    session_before_assessment = last_day_sessions[first_assessment_idx - 1]
                    sba_title_lower = session_before_assessment.get('instruction_title','').lower()
                    sba_res_lower = session_before_assessment.get('Resources','').lower()
                    is_activity = sba_title_lower.startswith("activity:")
                    has_feedback_keywords = "course feedback" in sba_title_lower or "traqom survey" in sba_title_lower
                    has_feedback_res = "feedback forms" in sba_res_lower or "survey links" in sba_res_lower
                    if not (is_activity and has_feedback_keywords and has_feedback_res):
                        st.warning(f"Last Day: Session before assessments ('{session_before_assessment.get('instruction_title')}') does not seem to be the correctly merged Feedback/TRAQOM activity. Title: '{sba_title_lower}', Resources: '{sba_res_lower}'.")
            else:
                     st.warning("Last Day: Final assessment is the first session. No preceding activity for Feedback/TRAQOM found.")
        else: 
                st.info("Last Day: No sessions titled 'Final Assessment' found to check TRAQOM merging against.")

    final_plan_structure = copy.deepcopy(processed_lesson_plan)
    if 'Learning_Units' not in final_plan_structure and 'Learning_Units' in context:
        final_plan_structure['Learning_Units'] = context['Learning_Units']

    final_plan_structure = renameactivity(final_plan_structure)
    final_plan_structure = postprocess_resources(final_plan_structure)
    # --- Check starttime + duration = endtime for all sessions ---
    check_start_end_duration(final_plan_structure)
    return final_plan_structure

def parse_time_range(time_str):
    """
    Parse a string like '0930hrs - 0935hrs (5 mins)' or '0930 - 0935 (5min)' into:
    - start time (as '0930'),
    - end time (as '0935'),
    - duration (as 'Xh Ymin' formatted string).
    Handles variations in 'hrs' and 'min' text.
    """
    # Regex to capture HHMM, HHMM, and duration (e.g., "5 mins", "1 hr", "2hr 30min")
    # Making "hrs" and space around hyphen optional, and duration flexible
    match = re.match(r'(\d{4})(?:hrs)?\s*-\s*(\d{4})(?:hrs)?\s*\((\d+)\s*(?:min|hr|mins|hrs)(?:\s+\d+\s*(?:min|mins))?\)', time_str, re.IGNORECASE)
    
    if not match:
        return None, None, None

    start_str, end_str, duration_full_str = match.groups()
    starttime = start_str
    endtime = end_str
    
    # Convert duration_full_str to minutes first
    duration_total_minutes = 0
    hours_match = re.search(r'(\d+)\s*(?:hr|hrs)', duration_full_str, re.IGNORECASE)
    if hours_match:
        duration_total_minutes += int(hours_match.group(1)) * 60
    
    mins_match = re.search(r'(\d+)\s*(?:min|mins)', duration_full_str, re.IGNORECASE)
    if mins_match:
        # If "hr" was also present, this regex might pick up the minutes part of "Xhr Ymin"
        # We need to be careful not to double count if the pattern is like "1hr 30min"
        # A simple way:
        temp_str_for_min = duration_full_str
        if hours_match: # if hours were found, remove them from string before searching for mins
            temp_str_for_min = re.sub(r'(\d+)\s*(?:hr|hrs)', '', temp_str_for_min, flags=re.IGNORECASE).strip()
        
        # Re-run minute match on the potentially modified string
        mins_match_refined = re.search(r'(\d+)\s*(?:min|mins)', temp_str_for_min, re.IGNORECASE)
        if mins_match_refined:
            duration_total_minutes += int(mins_match_refined.group(1))
        elif not hours_match and mins_match: # Only mins were in the original string
             duration_total_minutes += int(mins_match.group(1))


    # Format duration_total_minutes into "Xh Ymin"
    duration_formatted = format_duration_string(duration_total_minutes)

    return starttime, endtime, duration_formatted

def addstartendduration(data):
    """
    Processes lesson plan data to add 'starttime', 'endtime', and 'duration' (formatted string)
    to each session, derived from the 'Time' field.
    The 'Time' field is then removed.
    This function is kept for now if the AI *still* outputs the old "Time" field format,
    but the new fix_lesson_plan tries to handle direct starttime/endtime/duration from AI.
    """
    if 'lesson_plan' not in data or not data['lesson_plan']:
        st.warning("addstartendduration: 'lesson_plan' is missing or empty. Skipping.")
        return data

    for day in data['lesson_plan']:
        if 'Sessions' not in day or not day['Sessions']:
            continue
        for session in day['Sessions']:
            if 'Time' in session and session['Time']:
                start, end, duration_str = parse_time_range(session['Time'])
                if start and end and duration_str:
                    session['starttime'] = start
                    session['endtime'] = end
                    session['duration'] = duration_str
                    del session['Time']
                else:
                    st.warning(f"Could not parse Time string: {session['Time']}. Session title: {session.get('instruction_title')}")
                    session['starttime'] = session.get('starttime', '')
                    session['endtime'] = session.get('endtime', '')
                    session['duration'] = session.get('duration', '')
            elif not all(k in session for k in ['starttime', 'endtime', 'duration']):
                st.warning(f"Session missing starttime/endtime/duration and no 'Time' field to parse. Session: {session.get('instruction_title')}")
    return data

def renameactivity(lesson_plan_data):
    # Create a mapping of Learning Unit numbers to their instructional methods
    lu_instructional_methods = {}
    
    # Extract instructional methods from Learning Units
    for lu in lesson_plan_data.get('Learning_Units', []):
        lu_title = lu.get('LU_Title', '')
        # Extract LU number (e.g., "LU1" from "LU1: Identify Conflicts")
        lu_match = re.match(r'LU(\d+):', lu_title)
        if lu_match:
            lu_number = lu_match.group(1)
            # Get instructional methods and join them with ", "
            methods = lu.get('Instructional_Methods', [])
            if isinstance(methods, list):
                lu_instructional_methods[lu_number] = ", ".join(methods)
            else:
                lu_instructional_methods[lu_number] = methods
    
    # Process each day and session
    for day in lesson_plan_data['lesson_plan']:
        for session in day['Sessions']:
            title = session.get('instruction_title', '')
            
            # Check if the title starts with 'Activity: LUx:'
            match = re.match(r'(Activity: )LU(\d+):(.*)', title)
            if match:
                prefix, lu_number, rest = match.groups()
                
                # Get instructional methods from the corresponding Learning Unit
                instr_methods = lu_instructional_methods.get(lu_number, '')
                
                # If we have valid instructional methods, use them
                if instr_methods and instr_methods.upper() != 'N/A':
                    # Replace LUx with Instructional Methods + " on"
                    new_title = f"{prefix}{instr_methods} on{rest}"
                else:
                    # If no valid Instructional Methods, just remove LUx: and keep the rest
                    new_title = f"{prefix}{rest}"
                
                session['instruction_title'] = new_title.strip()
    
    return lesson_plan_data

def postprocess_resources(lesson_plan_data):
    found_pm_attendance = False
    found_assessment_attendance = False

    for day in lesson_plan_data['lesson_plan']:
        sessions = day['Sessions']
        for i, session in enumerate(sessions):
            title = session['instruction_title']
            resources = session.get('Resources', '')

            # Rule 1: Digital Attendance (PM)
            if title.lower() == 'lunch break':
                # Check next session
                if i + 1 < len(sessions):
                    next_session = sessions[i + 1]
                    next_resources = next_session.get('Resources', '')
                    if "Digital Attendance (PM)" not in next_resources:
                        # Add only here
                        next_session['Resources'] = "Digital Attendance (PM), " + next_resources if next_resources else "Digital Attendance (PM)"
                    found_pm_attendance = True
                continue  # Skip lunch block

            # Remove Digital Attendance (PM) if it's elsewhere
            if "Digital Attendance (PM)" in resources and not (
                found_pm_attendance and i > 0 and sessions[i - 1]['instruction_title'].lower() == 'lunch break'
            ):
                session['Resources'] = ", ".join(
                    [res.strip() for res in resources.split(",") if res.strip() != "Digital Attendance (PM)"]
                )

            # Rule 2: Digital Attendance Assessment
            is_final_assessment = title.strip().lower().startswith("final assessment")
            if "Digital Attendance Assessment" in resources:
                if not found_assessment_attendance and is_final_assessment:
                    found_assessment_attendance = True
                else:
                    # Remove from any subsequent assessments
                    session['Resources'] = ", ".join(
                        [res.strip() for res in resources.split(",") if res.strip() != "Digital Attendance Assessment"]
                    )

            # Add Digital Attendance Assessment to the first final assessment if not yet found
            if is_final_assessment and not found_assessment_attendance:
                if "Digital Attendance Assessment" not in resources:
                    session['Resources'] = "Digital Attendance Assessment, " + resources if resources else "Digital Attendance Assessment"
                found_assessment_attendance = True

    return lesson_plan_data


def parse_cp_documentold(uploaded_file):
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

def parse_cp_document(uploaded_file):
    """Parse document using Unstructured.io instead of LlamaParse"""
    
    from unstructured.partition.auto import partition
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
        tmp.write(uploaded_file.read())
        temp_file_path = tmp.name
    
    try:
        # Extract content using Unstructured
        elements = partition(temp_file_path)
        
        # Convert elements to text instead of markdown
        text_chunks = []
        for element in elements:
            # Get the text from each element
            text_chunks.append(str(element))
        
        # Join all text chunks with double newlines to create markdown-like formatting
        markdown_text = "\n\n".join(text_chunks)
        
        # Handle table formatting - simple conversion to maintain structure
        # Replace table rows with markdown-style table rows
        markdown_text = re.sub(r'(\n\s*\|\s*[^|]+\s*\|\s*)+', lambda m: m.group().replace('\n', '') + '\n', markdown_text)
        
        # Apply the same regex filtering from your original function
        ext = os.path.splitext(temp_file_path)[1].lower()
        if ext == ".docx":
            start_pattern = re.compile(r"Part\s*1.*?Particulars\s+of\s+Course", re.IGNORECASE)
            end_pattern = re.compile(r"Part\s*4.*?Facilities\s+and\s+Resources", re.IGNORECASE)
        elif ext == ".xlsx":
            start_pattern = re.compile(r"1\s*-\s*Course\s*Particulars", re.IGNORECASE)
            end_pattern = re.compile(r"4\s*-\s*Declarations", re.IGNORECASE)
        else:
            start_pattern = None
            end_pattern = None
        
        if start_pattern and end_pattern:
            start_match = start_pattern.search(markdown_text)
            end_match = end_pattern.search(markdown_text)
            if start_match and end_match and end_match.start() > start_match.start():
                markdown_text = markdown_text[start_match.start():end_match.start()].strip()
                
        return markdown_text
    
    finally:
        os.remove(temp_file_path)

def setup_batch_processing():
    """
    Sets up the batch processing environment.
    Creates the output directory and initializes the log file.
    
    Returns:
        tuple: (batch_output_dir, log_file_path)
    """
    # Create the batch output directory
    batch_output_dir = os.path.join("batchoutput", datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(batch_output_dir, exist_ok=True)
    
    # Initialize the log file
    log_file_path = os.path.join(batch_output_dir, "batch_processing_log.txt")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()  # Also output to console
        ]
    )
    
    with open(log_file_path, "w") as log_file:
        log_file.write(f"Batch Processing Log - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("-" * 80 + "\n\n")
    
    return batch_output_dir, log_file_path

def process_single_cp(file_path, selected_org, batch_output_dir, generate_options, model_clients, log_file_path):
    """
    Process a single course proposal file.
    
    Args:
        file_path (str): Path to the CP file
        selected_org (str): Selected organization name
        batch_output_dir (str): Output directory for batch processing
        generate_options (dict): Options for document generation
        model_clients (dict): Dictionary of model clients
        log_file_path (str): Path to the log file
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    file_name = os.path.basename(file_path)
    file_stem = os.path.splitext(file_name)[0]
    
    with open(log_file_path, "a") as log_file:
        log_file.write(f"Processing file: {file_name}\n")
    
    logging.info(f"Processing file: {file_name}")
    
    try:
        # Open the file
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        # Create a temporary UploadedFile-like object
        class TempUploadedFile:
            def __init__(self, name, content):
                self.name = name
                self._content = content
            
            def read(self):
                return self._content
                
        cp_file = TempUploadedFile(file_name, file_bytes)
        
        # Parse the CP document
        raw_data = parse_cp_document(cp_file)
        
        # Extract information
        context = asyncio.run(interpret_cp(
            raw_data=raw_data, 
            model_client=model_clients['openai_struct']
        ))
        
        # Add date and organization info
        current_datetime = datetime.now()
        current_date = current_datetime.strftime("%d %b %Y")
        year = current_datetime.year
        context["Date"] = current_date
        context["Year"] = year
        
        # Find the selected organisation UEN
        org_list = load_organizations()
        selected_org_data = next((org for org in org_list if org["name"] == selected_org), None)
        if selected_org_data:
            context["UEN"] = selected_org_data["uen"]
        
        # Process TGS Ref No if available
        tgs_course_code = st.session_state.get("tgs_course_code", "")
        context["TGS_Ref_No"] = tgs_course_code
        
        # Store generated documents paths
        generated_files = []
        
        # Generate Learning Guide if selected
        if generate_options.get('generate_lg'):
            try:
                logging.info(f"Generating Learning Guide for {file_name}")
                lg_output = generate_learning_guide(context, selected_org, model_clients['openai'])
                if lg_output:
                    # Move the file to batch output directory with input file's name
                    new_path = os.path.join(batch_output_dir, f"{file_stem}_LG.docx")
                    os.rename(lg_output, new_path)
                    generated_files.append(new_path)
                    logging.info(f"Learning Guide generated: {new_path}")
            except Exception as e:
                logging.error(f"Error generating Learning Guide: {str(e)}")
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"ERROR - Learning Guide: {str(e)}\n")
        
        # Generate Assessment Plan if selected
        if generate_options.get('generate_ap'):
            try:
                logging.info(f"Generating Assessment Documents for {file_name}")
                ap_output, asr_output = generate_assessment_documents(context, selected_org)
                
                if ap_output:
                    new_path = os.path.join(batch_output_dir, f"{file_stem}_AP.docx")
                    os.rename(ap_output, new_path)
                    generated_files.append(new_path)
                    logging.info(f"Assessment Plan generated: {new_path}")
                
                if asr_output:
                    new_path = os.path.join(batch_output_dir, f"{file_stem}_ASR.docx")
                    os.rename(asr_output, new_path)
                    generated_files.append(new_path)
                    logging.info(f"Assessment Summary Record generated: {new_path}")
            except Exception as e:
                logging.error(f"Error generating Assessment Documents: {str(e)}")
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"ERROR - Assessment Documents: {str(e)}\n")
        
        # Check if timetable is needed
        needs_timetable = (generate_options.get('generate_lp') or generate_options.get('generate_fg'))
        
        # Generate timetable if needed
        if needs_timetable and 'lesson_plan' not in context:
            try:
                logging.info(f"Generating Timetable for {file_name}")
                hours = int(''.join(filter(str.isdigit, context["Total_Course_Duration_Hours"])))
                num_of_days = hours / 8
                timetable_data = asyncio.run(generate_timetable(
                    context, 
                    num_of_days, 
                    model_clients['timetable_openai_struct']
                ))
                context['lesson_plan'] = timetable_data['lesson_plan']
            except Exception as e:
                logging.error(f"Error generating Timetable: {str(e)}")
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"ERROR - Timetable: {str(e)}\n")
                return False  # Exit if timetable generation fails
        
        # Generate Lesson Plan if selected
        if generate_options.get('generate_lp'):
            try:
                logging.info(f"Generating Lesson Plan for {file_name}")
                temporary_lesson_plan = fix_lesson_plan_compat(context)
                temporary_lesson_plan = addstartendduration(temporary_lesson_plan)
                temporary_lesson_plan = renameactivity(temporary_lesson_plan)
                context['lesson_plan'] = temporary_lesson_plan
                
                lp_output = generate_lesson_plan(context, selected_org)
                if lp_output:
                    new_path = os.path.join(batch_output_dir, f"{file_stem}_LP.docx")
                    os.rename(lp_output, new_path)
                    generated_files.append(new_path)
                    logging.info(f"Lesson Plan generated: {new_path}")
            except Exception as e:
                logging.error(f"Error generating Lesson Plan: {str(e)}")
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"ERROR - Lesson Plan: {str(e)}\n")
        
        # Generate Facilitator's Guide if selected
        if generate_options.get('generate_fg'):
            try:
                logging.info(f"Generating Facilitator's Guide for {file_name}")
                fg_output = generate_facilitators_guide(context, selected_org)
                if fg_output:
                    new_path = os.path.join(batch_output_dir, f"{file_stem}_FG.docx")
                    os.rename(fg_output, new_path)
                    generated_files.append(new_path)
                    logging.info(f"Facilitator's Guide generated: {new_path}")
            except Exception as e:
                logging.error(f"Error generating Facilitator's Guide: {str(e)}")
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"ERROR - Facilitator's Guide: {str(e)}\n")
        
        # Log success
        with open(log_file_path, "a") as log_file:
            log_file.write(f"SUCCESS - Generated {len(generated_files)} document(s) for {file_name}\n")
            log_file.write(f"  Generated files: {', '.join(generated_files)}\n\n")
        
        logging.info(f"Successfully processed {file_name}")
        return True
        
    except Exception as e:
        # Log any unexpected errors
        error_msg = f"ERROR - Unexpected error processing {file_name}: {str(e)}"
        logging.error(error_msg)
        with open(log_file_path, "a") as log_file:
            log_file.write(error_msg + "\n\n")
        return False
    
    
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
    st.subheader("Step 1: Upload Course Proposal (CP) Document or Folder")
    upload_type = st.radio(
        "Choose upload method:",
        ["Single File", "Batch Process Folder"],
        index=0
    )

    if upload_type == "Single File":
        cp_file = st.file_uploader("Upload Course Proposal (CP) Document", type=["docx", "xlsx"])
        batch_mode = False
    else:
        cp_folder = st.text_input("Enter folder path containing Course Proposal documents", 
                                placeholder="e.g., C:/Users/username/Documents/course_proposals")
        
        if cp_folder and os.path.exists(cp_folder):
            # Count valid files in the folder
            valid_files = [f for f in os.listdir(cp_folder) 
                        if f.lower().endswith(('.docx', '.xlsx')) 
                        and not f.startswith('~$')]  # Exclude temp files
            
            if valid_files:
                st.success(f"Found {len(valid_files)} valid course proposal files in the folder.")
                st.write("First 5 files:")
                for i, file in enumerate(valid_files[:5]):
                    st.write(f"{i+1}. {file}")
                if len(valid_files) > 5:
                    st.write(f"... and {len(valid_files) - 5} more files")
            else:
                st.warning(f"No valid course proposal files (.docx, .xlsx) found in {cp_folder}")
        
        elif cp_folder:
            st.error(f"Folder not found: {cp_folder}")
        
        batch_mode = True
        cp_file = None

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
        if (batch_mode and cp_folder and os.path.exists(cp_folder)) or (not batch_mode and cp_file is not None):
            if not selected_org:
                st.error("Please select a Name of Organisation.")
                st.stop()
                
            # Use the selected model configuration for all autogen agents
            selected_config = get_model_config(st.session_state['selected_model'])
            api_key = selected_config["config"].get("api_key")
            if not api_key:
                st.error("API key for the selected model is not provided.")
                st.stop()
                
            model_name = selected_config["config"]["model"]
            temperature = selected_config["config"].get("temperature", 0)
            base_url = selected_config["config"].get("base_url", None)
            model_info = selected_config["config"].get("model_info", None)

            # Set up response formats based on selected model
            if st.session_state['selected_model'] in ["DeepSeek-V3", "Gemini-Pro-2.5-Exp-03-25"]:
                cp_response_format = None
                lp_response_format = None
            else:
                cp_response_format = CourseData
                lp_response_format = LessonPlan

            # Initialize model clients
            model_clients = {
                'openai_struct': OpenAIChatCompletionClient(
                    model=model_name,
                    api_key=api_key,
                    temperature=temperature,
                    base_url=base_url,
                    response_format=cp_response_format,
                    model_info=model_info,
                ),
                'timetable_openai_struct': OpenAIChatCompletionClient(
                    model=model_name,
                    api_key=api_key,
                    temperature=temperature,
                    base_url=base_url,
                    response_format=lp_response_format,
                    model_info=model_info,
                ),
                'openai': OpenAIChatCompletionClient(
                    model=model_name,
                    api_key=api_key,
                    temperature=temperature,
                    base_url=base_url,
                    model_info=model_info,
                )
            }
            
            # Store document generation options
            generate_options = {
                'generate_lg': generate_lg,
                'generate_ap': generate_ap,
                'generate_lp': generate_lp,
                'generate_fg': generate_fg
            }
            
            if batch_mode:
                # Set up batch processing environment
                batch_output_dir, log_file_path = setup_batch_processing()
                
                # Get list of valid CP files
                valid_files = [f for f in os.listdir(cp_folder) 
                            if f.lower().endswith(('.docx', '.xlsx')) 
                            and not f.startswith('~$')]  # Exclude temp files
                
                if not valid_files:
                    st.error("No valid course proposal files found in the specified folder.")
                    st.stop()
                
                # Display progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process each file
                successful_count = 0
                failed_count = 0
                
                for i, filename in enumerate(valid_files):
                    file_path = os.path.join(cp_folder, filename)
                    status_text.text(f"Processing file {i+1}/{len(valid_files)}: {filename}")
                    
                    # Process the file
                    success = process_single_cp(
                        file_path=file_path,
                        selected_org=selected_org,
                        batch_output_dir=batch_output_dir,
                        generate_options=generate_options,
                        model_clients=model_clients,
                        log_file_path=log_file_path
                    )
                    
                    if success:
                        successful_count += 1
                    else:
                        failed_count += 1
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(valid_files))
                
                # Show completion message
                status_text.text(f"Batch processing complete! Successfully processed {successful_count} files, {failed_count} failed.")
                
                # Show download link for the batch output folder
                if successful_count > 0:
                    # Create a zip file of the batch output
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(batch_output_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, os.path.dirname(batch_output_dir))
                                zipf.write(file_path, arcname=arcname)
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        label="Download Batch Results (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
                    
                    # Also provide a link to the log file
                    with open(log_file_path, "rb") as log_file:
                        log_content = log_file.read()
                    st.download_button(
                        label="Download Processing Log",
                        data=log_content,
                        file_name="batch_processing_log.txt",
                        mime="text/plain"
                    )
                    
                st.info(f"All processed files are saved in: {batch_output_dir}")
                
            else:
                # Single file processing (existing code)
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
                            print("Context for AP:")
                            print(context)
                            
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
                            print("Lesson Plan after fixed resources:")
                            temporary_lesson_plan = postprocess_resources(temporary_lesson_plan)
                            print(temporary_lesson_plan)
                            context['lesson_plan'] = temporary_lesson_plan
                            print("Context for LP after fixing:")
                            print(context)
                            
                            #print("Org name:")
                            #print(selected_org)
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
            
            if cp_file is not None:
                file_stem = os.path.splitext(cp_file.name)[0]
            else:
                file_stem = "output"

            def add_file(file_path, suffix):
                if file_path and os.path.exists(file_path):
                    file_name = f"{file_stem}_{suffix}.docx"
                    zipf.write(file_path, arcname=file_name)

            # Add each generated document if it exists
            add_file(st.session_state.get('lg_output'), "LG")
            add_file(st.session_state.get('ap_output'), "AP")
            add_file(st.session_state.get('asr_output'), "ASR")
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