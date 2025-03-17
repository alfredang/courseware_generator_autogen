import re
import streamlit as st
from typing import List, Dict
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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

# Constants for folder IDs
TEMPLATES_FOLDER_ID = "1dNdgyMxOt2z5ftzjwuBky73gxFgIXiqg"  # Templates folder
WSQ_DOCUMENTS_FOLDER_ID = "1Rt6x1TQn1QAE-lYWRCnhNOmeUNhDQ0tR"  # 1 WSQ Document folder

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
    tsc_framework: str
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
    error: str = None
    exists: bool = False

def scrape_course_data(url: str) -> CourseData:
    """
    Scrapes course details from a given course webpage.

    This function extracts key course information, including title, description, 
    learning outcomes, pricing, session duration, TSC details, and WSQ funding.

    Args:
        url (str): 
            The URL of the course page to scrape.

    Returns:
        CourseData: 
            A structured object containing the extracted course details.

    Raises:
        WebDriverException: 
            If Selenium fails to load the page.
        NoSuchElementException: 
            If expected elements are not found on the webpage.
    """

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
            # Now extract the framework (e.g., "Human Resource" from "under Human Resource Skills Framework")
            framework_match = re.search(r"under\s+(.+?)\s+Skills\s+Framework", skills_framework_text, re.IGNORECASE)
            tsc_framework = framework_match.group(1).strip() if framework_match else "Not Applicable"
        except:
            tsc_title, tsc_code, tsc_framework = "Not Applicable", "Not Applicable", "Not Applicable"

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
            tsc_framework=tsc_framework,
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

def generate_brochure_wrapper(data: CourseData, course_folder_name: str) -> BrochureResponse:
    """
    Wrapper function to generate a Google Docs brochure for a given course.

    This function integrates with `generate_brochure` to create a brochure document,
    handling errors and pre-existing file cases.

    Args:
        data (CourseData): 
            Structured course data used to populate the brochure template.
        course_folder_name (str): 
            The folder name under "1 WSQ Documents" where the brochure should be stored.

    Returns:
        BrochureResponse: 
            A structured response indicating the generated file URL, 
            existing brochure status, or any errors encountered.
    """

    try:
        brochure_info = generate_brochure(data, course_folder_name)  # Now returns a dictionary
        
        # Handle error cases
        if "error" in brochure_info:
            error_message = brochure_info.get("error")
            course_title = brochure_info.get("course_title", data.course_title)
            return BrochureResponse(course_title=course_title, file_url="", error=error_message)
        
        # Handle success case
        course_title = brochure_info.get("course_title")
        shareable_link = brochure_info.get("shareable_link")
        
        # Handle existing file case
        if "exists" in brochure_info and brochure_info["exists"]:
            return BrochureResponse(
                course_title=course_title, 
                file_url=shareable_link,
                exists=True
            )
        
        return BrochureResponse(course_title=course_title, file_url=shareable_link)
    except Exception as e:
        # Catch any unexpected errors and wrap them in the response
        return BrochureResponse(
            course_title=data.course_title, 
            file_url="", 
            error=f"Unexpected error in brochure generation: {str(e)}"
        )

def authenticate():
    """
    Authenticates with Google Drive and Docs using a service account.

    Returns:
        google.auth.credentials.Credentials: 
            The authenticated credentials for accessing Google services.

    Raises:
        Exception: 
            If authentication fails due to incorrect credentials.
    """
    creds = None
    try:
        creds = service_account.Credentials.from_service_account_info(
        st.secrets["GOOGLE_API_CREDS"]
        )
        return creds

    except Exception as e:
        st.error(f"An error occurred during authentication: {e}")
        return None

def find_folder(drive_service, parent_folder_id, folder_name):
    """
    Finds a specific folder within a given parent folder on Google Drive.

    Args:
        drive_service: 
            The Google Drive API service instance.
        parent_folder_id (str): 
            The ID of the parent folder where the search should occur.
        folder_name (str): 
            The exact name of the folder to search for.

    Returns:
        str or None: 
            The folder ID if found, otherwise None.
    """
    
    # Use a specific query to find the exact folder
    query = f"name = '{folder_name}' and '{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=5  # Increased to handle possible duplicate names
    ).execute()
    
    items = response.get('files', [])
    if items:
        # If multiple folders with the same name exist, use the first one
        print(f"Found existing folder: {folder_name} (ID: {items[0]['id']})")
        return items[0]['id']
    
    # Return None if folder doesn't exist
    print(f"Folder not found: {folder_name} in parent folder: {parent_folder_id}")
    return None

def copy_template(drive_service, template_id, new_title, destination_folder_id):
    """
    Copies a Google Docs template to a specified destination folder.

    If a document with the same name already exists in the destination folder, 
    it will not create a duplicate.

    Args:
        drive_service: 
            The Google Drive API service instance.
        template_id (str): 
            The ID of the template document to copy.
        new_title (str): 
            The name of the new document to be created.
        destination_folder_id (str): 
            The ID of the folder where the new document should be stored.

    Returns:
        str or None: 
            The ID of the newly created document or the existing document if it already exists.
    """

    try:
        # First check if a file with the same name already exists in the destination folder
        query = f"name = '{new_title}' and '{destination_folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed = false"
        response = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        
        existing_files = response.get('files', [])
        if existing_files:
            print(f"Document '{new_title}' already exists in folder {destination_folder_id}. Using existing document.")
            return existing_files[0]['id']
        
        # If no existing file, create a new copy
        body = {
            'name': new_title,
            'parents': [destination_folder_id]
        }
        
        new_doc = drive_service.files().copy(
            fileId=template_id, body=body
        ).execute()
        
        print(f"Created document with ID: {new_doc.get('id')} in folder: {destination_folder_id}")
        return new_doc.get('id')
    except HttpError as error:
        print(f"An error occurred while copying template: {error}")
        return None

def find_placeholders(docs_service, document_id):
    """
    Identifies placeholders in a Google Docs template.

    This function scans the document for text enclosed in curly braces `{}` 
    and returns a list of placeholders.

    Args:
        docs_service: 
            The Google Docs API service instance.
        document_id (str): 
            The ID of the document to scan.

    Returns:
        set: 
            A set of unique placeholders found in the document.
    """

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
    Finds the start and end indices of a given text in a Google Docs document.

    This function retrieves the document content and scans its paragraphs 
    to locate the specified search text. It returns the start and end character 
    indices if found.

    Args:
        docs_service: 
            The Google Docs API service instance.
        document_id (str): 
            The ID of the Google Docs document.
        search_text (str): 
            The exact text string to search for within the document.

    Returns:
        tuple:
            - `int`: The start index of the search text within the document.
            - `int`: The end index of the search text within the document.
            - Returns `(None, None)` if the text is not found.

    Raises:
        HttpError: 
            If there is an issue retrieving the document.
        KeyError: 
            If the expected content structure is not found in the document response.
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
    """
    Replaces placeholders in a Google Docs template with actual course data.

    This function processes a document and replaces all `{placeholders}` 
    with corresponding values from the provided dictionary.

    Args:
        docs_service: 
            The Google Docs API service instance.
        document_id (str): 
            The ID of the document to modify.
        replacements (dict): 
            A dictionary where keys are placeholder names and values are their replacements.

    Raises:
        HttpError: 
            If the update request fails due to an API issue.
    """

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

def generate_brochure(data: CourseData, course_folder_name: str):
    """
    Generates a Google Docs brochure for a given course.

    This function:
    1. Searches for a predefined template.
    2. Copies the template to the correct course folder.
    3. Replaces placeholders with actual course details.
    4. Returns a shareable link to the generated brochure.

    Args:
        data (CourseData): 
            The structured course data to populate the template.
        course_folder_name (str): 
            The name of the course folder where the brochure should be stored.

    Returns:
        dict: 
            A dictionary containing the generated document's shareable link 
            or an error message if the process fails.
    """

    creds = authenticate()
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Find the template document in the Templates folder
    template_name = '(Template) WSQ - Course Title Brochure'
    query = f"name = '{template_name}' and mimeType='application/vnd.google-apps.document' and '{TEMPLATES_FOLDER_ID}' in parents and trashed = false"
    response = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=1
    ).execute()
    
    items = response.get('files', [])
    if not items:
        print("Template document not found in the Templates folder.")
        return {"error": "Template document not found in Templates folder", "course_title": data.course_title}
    
    template_id = items[0]['id']
    print(f"Found template document: {template_name} (ID: {template_id})")
    
    # Verify the WSQ Documents folder exists
    try:
        wsq_folder = drive_service.files().get(fileId=WSQ_DOCUMENTS_FOLDER_ID, fields="name").execute()
        print(f"Found WSQ Documents folder: {wsq_folder.get('name')} (ID: {WSQ_DOCUMENTS_FOLDER_ID})")
    except HttpError as error:
        print(f"Error accessing WSQ Documents folder: {error}")
        return {"error": "Cannot access WSQ Documents folder", "course_title": data.course_title}
    
    # Find the course folder in WSQ Documents - do NOT create if it doesn't exist
    course_folder_id = find_folder(drive_service, WSQ_DOCUMENTS_FOLDER_ID, course_folder_name)
    if not course_folder_id:
        return {"error": f"Course folder '{course_folder_name}' not found in WSQ Documents folder", "course_title": data.course_title}
    
    # Find the Brochure folder within the course folder - do NOT create if it doesn't exist
    brochure_folder_id = find_folder(drive_service, course_folder_id, "Brochure")
    if not brochure_folder_id:
        return {"error": f"Brochure folder not found in {course_folder_name}", "course_title": data.course_title}
    
    # Check if a brochure already exists in the destination folder
    new_title = f"{data.course_title} Brochure"
    try:
        query = f"name = '{new_title}' and mimeType='application/vnd.google-apps.document' and '{brochure_folder_id}' in parents and trashed = false"
        response = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        
        existing_files = response.get('files', [])
        if existing_files:
            existing_file_id = existing_files[0]['id']
            print(f"Found existing brochure: {new_title} (ID: {existing_file_id})")
            return {
                "course_title": data.course_title,
                "shareable_link": f"https://docs.google.com/document/d/{existing_file_id}/edit",
                "exists": True
            }
    except Exception as e:
        print(f"Error checking for existing brochure: {e}")
        # Continue execution even if check fails
    
    # Copy the template to the Brochure folder with a new name - never overwrite existing files
    try:
        new_doc_id = copy_template(drive_service, template_id, new_title, brochure_folder_id)
        if not new_doc_id:
            return {"error": "Failed to create document", "course_title": data.course_title}
        print(f"Successfully copied template to: {new_title} (ID: {new_doc_id})")
    except Exception as e:
        print(f"Error copying template: {e}")
        return {"error": f"Error copying template: {str(e)}", "course_title": data.course_title}
    
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
        'TSC_Framework': data_dict.get('tsc_framework', 'Not Applicable'),
        'GST_Excl_Price': data_dict.get('gst_exclusive_price', 'Not Applicable'),
        'GST_Incl_Price': data_dict.get('gst_inclusive_price', 'Not Applicable'),
        'Duration_Hrs': data_dict.get('duration_hrs', 'Not Applicable'),
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
        return {
            "course_title": data_dict.get('course_title', 'Unknown Course Title'),
            "shareable_link": f"https://docs.google.com/document/d/{new_doc_id}/edit"
        }

    # Replace placeholders
    replace_placeholders_in_doc(docs_service, new_doc_id, replacements)
    
    # Return course title and shareable link
    return {
        "course_title": data_dict.get('course_title', 'Unknown Course Title'),
        "shareable_link": f"https://docs.google.com/document/d/{new_doc_id}/edit"
    }

# Streamlit app
def app():
    """
    Streamlit web application for generating course brochures.

    This function provides a user interface for:
    - Entering a course URL and folder name.
    - Scraping course data.
    - Authenticating with Google Drive.
    - Checking for existing course brochures.
    - Generating new brochures if needed.

    Raises:
        ValueError: 
            If required input fields are missing.
        Exception: 
            If any step in the brochure generation process fails.
    """

    # Enable wide mode for the layout
    st.title("📄 Brochure Generator")

    st.subheader("Instructions:")
    st.markdown("""
    #### 🌐 Course URL and Folder Selection Instructions

    1. **Enter a valid course URL from the Tertiary Courses website**  
        - Format: `https://www.tertiarycourses.com.sg/[course_title].html`  
    
    2. **Enter the exact Course Folder name from the `1 WSQ Documents` directory**  
        - Format: `TGS-[Course Code] - [Course Title]` or `TGS-[Course Code] - [Course Title] (NEW)`

    3. **Click "Generate Brochure"** to scrape data and generate the course brochure automatically.  
    """)

    
    # URL input
    course_url = st.text_input("Enter the Course URL:")
    
    # Course folder name input
    course_folder_name = st.text_input("Enter the Course Folder name:")
    
    # Add a warning about folder requirements
    st.warning("⚠️ Important: Both the _**Course Folder**_ and its _**Brochure**_ subfolder must already exist. This app will NOT create any folders.")

    if st.button("Generate Brochure"):
        if not course_url:
            st.error("Please provide a valid URL.")
            return
            
        if not course_folder_name:
            st.error("Please provide a Course Folder name.")
            return
            
        # Basic validation for folder name
        if any(char in course_folder_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            st.error("Course folder name contains invalid characters. Please avoid using: / \\ : * ? \" < > |")
            return

        try:
            # Step 1: Scrape course data
            with st.spinner("Scraping course data..."):
                course_data = scrape_course_data(course_url)
                st.success("Course data scraped successfully!")
                st.session_state['course_data'] = course_data.to_dict()  # Save scraped data to session state
            
            with st.spinner("Authenticating with Google Drive..."):
                creds = authenticate()
                if not creds:
                    st.error("Authentication failed. Please check your credentials.")
                    return
                    
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Step 2: Check if the Course Folder exists in "1 WSQ Documents"
            with st.spinner(f"Checking if the folder '{course_folder_name}' exists..."):
                try:
                    drive_service = build('drive', 'v3', credentials=creds)
                    
                    # Check if the course folder exists
                    query = f"name = '{course_folder_name}' and '{WSQ_DOCUMENTS_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                    response = drive_service.files().list(
                        q=query,
                        spaces='drive',
                        fields='files(id, name)',
                        pageSize=1
                    ).execute()
                    
                    course_folders = response.get('files', [])
                    if not course_folders:
                        st.error(f"Error: Folder '{course_folder_name}' not found in '1 WSQ Documents'. Please verify the folder name and try again.")
                        return
                        
                    course_folder_id = course_folders[0]['id']
                    
                    # Check if Brochure folder exists within the course folder
                    query = f"name = 'Brochure' and '{course_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                    response = drive_service.files().list(
                        q=query,
                        spaces='drive',
                        fields='files(id, name)',
                        pageSize=1
                    ).execute()
                    
                    brochure_folders = response.get('files', [])
                    if not brochure_folders:
                        st.error(f"Error: 'Brochure' folder not found within '{course_folder_name}'. Please create this folder first.")
                        return
                except Exception as e:
                    st.error(f"Error checking folders: {e}")
                    return
                
            # Step 3: Check if a Brochure folder exists and if it already contains a brochure for this course
            with st.spinner("Checking for existing brochure..."):
                # First, find the course folder ID
                if course_folders:
                    course_folder_id = course_folders[0]['id']
                    
                    # Check if Brochure folder exists
                    query = f"name = 'Brochure' and '{course_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                    response = drive_service.files().list(
                        q=query,
                        spaces='drive',
                        fields='files(id, name)',
                        pageSize=1
                    ).execute()
                    
                    brochure_folders = response.get('files', [])
                    if brochure_folders:
                        brochure_folder_id = brochure_folders[0]['id']
                        
                        # Check if a brochure with the same name already exists
                        brochure_name = f"{course_data.course_title} Brochure"
                        query = f"name = '{brochure_name}' and '{brochure_folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed = false"
                        response = drive_service.files().list(
                            q=query,
                            spaces='drive',
                            fields='files(id, name)',
                            pageSize=1
                        ).execute()
                        
                        existing_brochures = response.get('files', [])
                        if existing_brochures:
                            existing_brochure_id = existing_brochures[0]['id']
                            shareable_link = f"https://docs.google.com/document/d/{existing_brochure_id}/edit"
                            
                            st.warning(
                                f"""A brochure for the course \"{course_data.course_title}\" already exists in the folder path:
                                1 WSQ Documents > {course_folder_name} > Brochure
                                \n[View existing brochure]({shareable_link})
                                """
                            )
                            return
            
            # Step 4: Generate brochure
            try:
                with st.spinner("Generating brochure..."):
                    # Convert the dictionary back to a CourseData object
                    course_data = CourseData(**st.session_state['course_data'])
                    response = generate_brochure_wrapper(course_data, course_folder_name)
                
                # Check if there was an error or if brochure already exists
                if hasattr(response, 'error') and response.error is not None:
                    st.error(f"Error: {response.error}")
                    return
                    
                if hasattr(response, 'exists') and response.exists:
                    st.warning(
                        f"""A brochure for the course \"{response.course_title}\" already exists in the folder path:
                        1 WSQ Documents > {course_folder_name} > Brochure
                        
                        The existing file will not be overwritten to prevent data loss.
                        \n[View existing brochure]({response.file_url})
                        """
                    )
                    # Still set session state so the "View Brochure" button works
                    st.session_state['course_title'] = response.course_title
                    st.session_state['file_url'] = response.file_url
                    return
                
                # Set session state with response data
                st.session_state['course_title'] = response.course_title
                st.session_state['file_url'] = response.file_url
                
                st.success(
                    f"""The brochure for the course \"{response.course_title}\" has been successfully generated and saved to:
                    1 WSQ Documents > {course_folder_name} > Brochure
                    """
                )

            except Exception as e:
                st.error(f"An error occurred while generating the brochure: {e}")
                if "not found" in str(e).lower():
                    st.error("One or more required folders were not found. Please ensure both the course folder and Brochure subfolder exist.")

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