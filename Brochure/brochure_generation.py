# brochure_generation.py

import os
import re
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
import streamlit as st
from typing import List, Dict, Optional
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import time

# Initialize session state variables
if 'course_title' not in st.session_state:
    st.session_state['course_title'] = None
if 'file_url' not in st.session_state:
    st.session_state['file_url'] = None
if 'json_data' not in st.session_state:
    st.session_state['json_data'] = None

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
]

# Data models
class CourseTopic(BaseModel):
    title: str
    subtopics: List[str]

class CourseData(BaseModel):
    course_title: str
    course_description: List[str]
    learning_outcomes: List[str]
    tsc_title: str
    tsc_code: str
    wsq_funding: Dict[str, str]
    tgs_reference_no: str
    gst_exclusive_price: str
    gst_inclusive_price: str
    session_days: str
    duration_hrs: str
    course_details_topics: List[CourseTopic]
    course_url: str  # Added course_url to match {Course_URL}

    def to_dict(self):
        return self.dict()

class BrochureResponse(BaseModel):
    course_title: str
    file_url: str

def scrape_course_data(url: str) -> CourseData:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)

    try:
        # Navigate to the course page
        driver.get(url)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Allow time for content to load

        # Extract Course Title
        try:
            course_title_elem = driver.find_element(By.CSS_SELECTOR, 'div.product-name h1')
            course_title = course_title_elem.text.strip()
        except:
            course_title = "Not Applicable"

        # Extract data from the "short-description" div
        try:
            short_description = driver.find_element(By.CLASS_NAME, "short-description")
            course_description = [p.text for p in short_description.find_elements(By.TAG_NAME, "p")[:2]]
        except:
            course_description = ["Not Applicable"]

        # Extract Learning Outcomes
        try:
            lo_section = short_description.find_element(By.XPATH, ".//h2[contains(text(), 'Learning Outcomes')]/following-sibling::ul[1]")
            learning_outcomes = [li.text.strip() for li in lo_section.find_elements(By.TAG_NAME, 'li')]
        except:
            learning_outcomes = []

        # Extract TSC Title and TSC Code
        try:
            skills_framework_text = driver.find_element(By.XPATH, "//h2[contains(text(), 'Skills Framework')]/following-sibling::p").text.strip()
            match = re.search(r"guideline of\s+(.*?)\s+(\S+)\s+under", skills_framework_text)
            tsc_title = match.group(1).strip() if match else "Not Applicable"
            tsc_code = match.group(2).strip() if match else "Not Applicable"
        except:
            tsc_title, tsc_code = "Not Applicable", "Not Applicable"

        # Extract WSQ Funding table
        try:
            wsq_funding_table = short_description.find_element(By.TAG_NAME, "table")
            funding_rows = wsq_funding_table.find_elements(By.TAG_NAME, "tr")

            headers = ['Full Fee', 'GST', 'Baseline', 'MCES / SME']
            data_row = funding_rows[-1]
            data_cells = data_row.find_elements(By.TAG_NAME, "td")
            wsq_funding = {headers[i]: data_cells[i].text.strip() for i in range(len(headers))}
            effective_date_text = funding_rows[0].text.strip()
            wsq_funding['Effective Date'] = effective_date_text if effective_date_text else 'Not Available'
        except:
            wsq_funding = {"Effective Date": "Not Available", "Full Fee": "Not Available", "GST": "Not Available", "Baseline": "Not Available", "MCES / SME": "Not Available"}

        # Extract TGS Reference Number
        try:
            sku_div = driver.find_element(By.CLASS_NAME, "sku")
            tgs_reference_no = sku_div.text.strip().replace("Course Code:", "").strip()
        except:
            tgs_reference_no = "Not Applicable"

        # Extract Prices
        try:
            price_box = driver.find_element(By.CLASS_NAME, "price-box")
            gst_exclusive_price = price_box.find_element(By.CSS_SELECTOR, ".regular-price .price").text.strip()
            gst_inclusive_price = price_box.find_element(By.ID, "gtP").text.strip()
        except:
            gst_exclusive_price, gst_inclusive_price = "Not Applicable", "Not Applicable"

        # Extract Course Information (Session days, Duration hrs)
        try:
            course_info_div = driver.find_element(By.CLASS_NAME, "block-related")
            course_info_list = course_info_div.find_elements(By.CSS_SELECTOR, "#bs-pav li")
            session_days = "Not Applicable"
            duration_hrs = "Not Applicable"
            for item in course_info_list:
                text = item.text.strip().split(":")
                if len(text) == 2:
                    key = text[0].strip()
                    value = text[1].strip()
                    if key == "Session (days)":
                        session_days = value
                    elif key == "Duration (hrs)":
                        duration_hrs = value
        except:
            session_days, duration_hrs = "Not Applicable", "Not Applicable"

        # Extract Topics
        course_details_topics = []
        try:
            details_section = driver.find_element(By.XPATH, "//div[@class='tabs-panels']//h2[text()='Course Details']/following-sibling::div[@class='std']")
            topics = details_section.find_elements(By.XPATH, ".//p[strong]")
            for topic_elem in topics:
                title = topic_elem.find_element(By.TAG_NAME, "strong").text.strip()
                ul = topic_elem.find_element(By.XPATH, "following-sibling::*[1]")
                subtopics = [li.text.strip() for li in ul.find_elements(By.TAG_NAME, "li")]
                course_details_topics.append(CourseTopic(title=title, subtopics=subtopics))
        except Exception as e:
            print(f"Error extracting topics: {e}")

        # Return scraped data as a CourseData object
        return CourseData(
            course_title=course_title,
            course_description=course_description,
            learning_outcomes=learning_outcomes,
            tsc_title=tsc_title,
            tsc_code=tsc_code,
            wsq_funding=wsq_funding,
            tgs_reference_no=tgs_reference_no,
            gst_exclusive_price=gst_exclusive_price,
            gst_inclusive_price=gst_inclusive_price,
            session_days=session_days,
            duration_hrs=duration_hrs,
            course_details_topics=course_details_topics,
            course_url=url
        )
    finally:
        driver.quit()

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken

def generate_brochure_wrapper(data: CourseData) -> BrochureResponse:
    brochure_info = generate_brochure(data)  # Now returns a dictionary
    course_title = brochure_info.get("course_title")
    shareable_link = brochure_info.get("shareable_link")
    return BrochureResponse(course_title=course_title, file_url=shareable_link)

def authenticate():
    creds = None
    try:
        creds = service_account.Credentials.from_service_account_info(
        st.secrets["GOOGLE_API_CREDS"]
        )
        return creds

    except Exception as e:
        st.error(f"An error occurred during authentication: {e}")
        return None

def copy_template(drive_service, template_id, new_title):
    try:
        body = {'name': new_title}
        new_doc = drive_service.files().copy(
            fileId=template_id, body=body
        ).execute()
        print(f"Created document with ID: {new_doc.get('id')}")
        return new_doc.get('id')
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def find_placeholders(docs_service, document_id):
    doc = docs_service.documents().get(documentId=document_id).execute()
    placeholders = set()

    for element in doc.get('body', {}).get('content', []):
        if 'table' in element:
            # Process table rows and cells
            table = element['table']
            for row in table.get('tableRows', []):
                for cell in row.get('tableCells', []):
                    for content in cell.get('content', []):
                        if 'paragraph' in content:
                            for run in content['paragraph'].get('elements', []):
                                text_run = run.get('textRun')
                                if text_run and 'content' in text_run:
                                    matches = re.findall(r'\{(.*?)\}', text_run['content'])
                                    placeholders.update(matches)
        elif 'paragraph' in element:
            # Process regular text paragraphs
            for run in element['paragraph'].get('elements', []):
                text_run = run.get('textRun')
                if text_run and 'content' in text_run:
                    matches = re.findall(r'\{(.*?)\}', text_run['content'])
                    placeholders.update(matches)

    return placeholders

def find_text_range(docs_service, document_id, search_text):
    """
    Find the start and end indices of the given text in the document.
    """
    doc = docs_service.documents().get(documentId=document_id).execute()
    content = doc.get('body', {}).get('content', [])
    for element in content:
        if 'paragraph' in element:
            for run in element['paragraph'].get('elements', []):
                text_run = run.get('textRun')
                if text_run and 'content' in text_run:
                    text = text_run['content']
                    start_index = run.get('startIndex')
                    if search_text in text and start_index is not None:
                        start = start_index + text.index(search_text)
                        end = start + len(search_text)
                        return start, end
    return None, None

def replace_placeholders_in_doc(docs_service, document_id, replacements):
    try:
        requests = []

        for placeholder, replacement in replacements.items():
            # Replace placeholders
            requests.append({
                'replaceAllText': {
                    'containsText': {
                        'text': f'{{{placeholder}}}',
                        'matchCase': True,
                    },
                    'replaceText': replacement,
                }
            })

        # Execute batch update for replacing text
        docs_service.documents().batchUpdate(
            documentId=document_id, body={'requests': requests}).execute()

        # Add hyperlink for Course_URL
        if 'Course_URL' in replacements:
            course_url_text = replacements['Course_URL']
            start, end = find_text_range(docs_service, document_id, course_url_text)
            if start is not None and end is not None:
                hyperlink_request = {
                    'updateTextStyle': {
                        'range': {
                            'startIndex': start,
                            'endIndex': end,
                        },
                        'textStyle': {
                            'link': {
                                'url': course_url_text
                            }
                        },
                        'fields': 'link'
                    }
                }
                docs_service.documents().batchUpdate(
                    documentId=document_id, body={'requests': [hyperlink_request]}).execute()

        print(f"Replaced placeholders in document ID: {document_id}")

    except HttpError as error:
        print(f"An error occurred during placeholder replacement: {error}")

def generate_brochure(data: CourseData):
    creds = authenticate()
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Find the template document
    template_name = '(Template) WSQ - Course Title Brochure'
    query = f"name = '{template_name}' and mimeType='application/vnd.google-apps.document'"
    response = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=1
    ).execute()
    items = response.get('files', [])
    if not items:
        print("Template document not found.")
        return
    template_id = items[0]['id']
    
    # Check if a document with the same name already exists
    new_title = f"{data.course_title} Brochure"
    new_doc_id = copy_template(drive_service, template_id, new_title)
    
    # Build replacements
    replacements = {}
    data_dict = data.model_dump()
    
    # Map data fields to placeholders
    mapping = {
        'Course_Title': data_dict.get('course_title', 'Not Applicable'),
        'Course_Desc': '\n\n'.join(data_dict.get('course_description', [])),
        'Learning_Outcomes': '\n'.join([lo for lo in data_dict.get('learning_outcomes', [])]),
        'TGS_Ref_No': data_dict.get('tgs_reference_no', 'Not Applicable'),
        'TSC_Title': data_dict.get('tsc_title', 'Not Applicable'),
        'TSC_Code': data_dict.get('tsc_code', 'Not Applicable'),
        'GST_Excl_Price': data_dict.get('gst_exclusive_price', 'Not Applicable'),
        'GST_Incl_Price': data_dict.get('gst_inclusive_price', 'Not Applicable'),
        'Duration_Hrs': data_dict.get('duration_has', 'Not Applicable'),
        'Session_Days': data_dict.get('session_days', 'Not Applicable'),
        
        'Course_URL': data_dict.get('course_url', 'Not Applicable'),
        'Effective_Date': data_dict.get('wsq_funding', {}).get('Effective Date', 'Not Applicable') if data_dict.get('wsq_funding') else 'Not Applicable',
        'Full_Fee': data_dict.get('wsq_funding', {}).get('Full Fee', 'Not Applicable') if data_dict.get('wsq_funding') else 'Not Applicable',
        'GST': data_dict.get('wsq_funding', {}).get('GST', 'Not Applicable') if data_dict.get('wsq_funding') else 'Not Applicable',
        'Baseline_Price': data_dict.get('wsq_funding', {}).get('Baseline', 'Not Applicable') if data_dict.get('wsq_funding') else 'Not Applicable',
        'MCES_SME_Price': data_dict.get('wsq_funding', {}).get('MCES / SME', 'Not Applicable') if data_dict.get('wsq_funding') else 'Not Applicable',
    }

    # Handle {Course_Topics} placeholder
    course_topics = data_dict.get('course_details_topics', [])
    if course_topics:
        if len(course_topics) > 10:
            # Only include the main topics
            topics_text = '\n'.join([topic['title'] for topic in course_topics])
        else:
            # Include topics with subtopics
            topics_text = ''
            for topic in course_topics:
                topics_text += f"{topic['title']}\n"
                for subtopic in topic['subtopics']:
                    topics_text += f"{subtopic}\n"
                topics_text += '\n'
        mapping['Course_Topics'] = topics_text.strip()
    else:
        mapping['Course_Topics'] = 'Not Applicable'
    # Find placeholders in the document
    placeholders = find_placeholders(docs_service, new_doc_id)
    print(f"Placeholders found in document: {placeholders}")
    
    # Filter replacements for placeholders found
    replacements = {k: v for k, v in mapping.items() if k in placeholders}

    if not replacements:
        print("No matching placeholders found. Skipping update.")
        return new_doc_id

    # Replace placeholders
    replace_placeholders_in_doc(docs_service, new_doc_id, replacements)
    
    # Get the shareable link for the document
    shareable_link = f"https://drive.google.com/file/d/{new_doc_id}/view"

    return {
        "course_title": data_dict.get('course_title', 'Unknown Course Title'),
        "shareable_link": shareable_link
    }

def extract_tool_response(chat_content):
    """
    Extracts course title and file URL from the tool response.
    """
    try:
        # Parse the JSON content
        content = dict(chat_content)
        parsed_content = json.loads(content)
        course_title = parsed_content.get("course_title", "Unknown Course Title")
        file_url = parsed_content.get("file_url", None)
        
        if course_title and file_url:
            return course_title, file_url

    except Exception as e:
        print(f"Error extracting tool response: {e}")
    return None, None


async def brochure_autogen(course_data, model_client):
    doc_writer_agent = AssistantAgent(
        name="doc_writer",
        model_client=model_client,
        tools=[generate_brochure_wrapper],
        system_message="""
            You are an assistant that generates brochures based on course data. 

            ### Instructions:
            "When replacing placeholders for Learning Outcomes and Course Topics, check for prefixes like '-', '*', or 'LOx:' at the start of each line, and remove them before inserting the text into the document. 
            Do not modify the contents otherwise; only remove the prefixes.
            Ensure that all fields, including `wsq_funding`, remain within the `data` dictionary.
        """
    )
    agent_task = f"""
        Please generate a brochure using the following course data: {course_data}
        **Do not modify the data structure or move any fields outside of the `data` dictionary.**
        Provide the shareable file link to the generated brochure.
    """
    # Process sample input
    response = await doc_writer_agent.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )

    output = response.chat_message.content
    
    if output:
        return output 
    else:
        raise Exception(f"Error: Brochure chat content missing.")

# Streamlit app
def app():
    # Enable wide mode for the layout
    st.title("📄 Brochure Generator with Autogen")
    model_client = OpenAIChatCompletionClient(
        model=st.secrets["REPLACEMENT_MODEL_NAME"],
        temperature=0,
        api_key=st.secrets["OPENAI_API_KEY"]
    )

    # Create two columns
    left_col, right_col = st.columns([1, 1])  # Adjust column ratio (e.g., 1:2 for a wider right column)

    with left_col:
        st.header("Instructions:")
        st.markdown("""
        Enter a valid course URL from the Tertiary Courses website, and click "Generate Brochure" to scrape the data and generate a brochure.
        """)
        
        # URL input
        course_url = st.text_input("Enter the Course URL:")

        if st.button("Generate Brochure"):
            if not course_url:
                st.error("Please provide a valid URL.")
                return

            try:
                # Step 1: Scrape course data
                with st.spinner("Scraping course data..."):
                    course_data = scrape_course_data(course_url)
                    st.success("Course data scraped successfully!")
                    st.session_state['course_data'] = course_data.to_dict()  # Save scraped data to session state
                    print(course_data)
                creds = None
                with st.spinner("Authenticating with Google Drive..."):
                    creds = authenticate()

                # Check if a brochure for the course already exists
                with st.spinner("Checking for existing brochure in Google Drive..."):
                    drive_service = build('drive', 'v3', credentials=creds)
                    
                    existing_title = f"{course_data.course_title} Brochure"
                    query = f"name = '{existing_title}' and mimeType='application/vnd.google-apps.document' and trashed = false"
                    response = drive_service.files().list(
                        q=query,
                        spaces='drive',
                        fields='files(id, name)',
                        pageSize=1
                    ).execute()
                    existing_docs = response.get('files', [])

                    if existing_docs:
                        # If a document with the same title exists, show an alert
                        existing_doc_id = existing_docs[0]['id']
                        shareable_link = f"https://drive.google.com/file/d/{existing_doc_id}/view"
                        st.warning(
                            f"""A brochure for the course \"{course_data.course_title}\" already exists.
                            \n[View existing brochure]({shareable_link})
                            """
                        )
                        return
                # Step 2: Display the scraped JSON
                with right_col:
                    st.json(st.session_state['course_data'], expanded=1)

                
                # Step 3: Generate brochure
                try:
                    with st.spinner("Generating brochure using Autogen..."):
                        response = asyncio.run(brochure_autogen(json.dumps(st.session_state['course_data'])), model_client)
                    
                except Exception as e:
                    st.error(f"An error occurred: {e}")

                # Step 4: Extract tool response
                course_title, file_url = extract_tool_response(response)
                if course_title and file_url:
                    st.session_state['course_title'] = course_title
                    st.session_state['file_url'] = file_url
                    st.success(f"The brochure for the course \"{course_title}\" has been successfully generated.")
                else:
                    st.error("The tool response did not contain valid data.")

            except Exception as e:
                st.error(f"An error occurred: {e}")

        # Safely check if file_url exists in session state
        file_url = st.session_state.get('file_url')
        if file_url:
            # Display link button for the brochure
            st.link_button(
                label="View Brochure",
                url=file_url,
                icon=":material/description:"
            )