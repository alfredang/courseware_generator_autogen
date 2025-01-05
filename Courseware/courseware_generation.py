# courseware_generation.py

from Courseware.agentic_LG import generate_learning_guide
from Courseware.agentic_AP import generate_assessment_plan
from Courseware.agentic_FG import generate_facilitators_guide
from Courseware.agentic_LP import generate_lesson_plan
from Courseware.timetable_generator import generate_timetable
from datetime import datetime
from autogen import UserProxyAgent, AssistantAgent
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph
from selenium import webdriver

import os
import dotenv
import requests
import json
import re
import streamlit as st
import urllib.parse
import time


# Initialize session state variables
if 'processing_done' not in st.session_state:
    st.session_state['processing_done'] = False
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

# Function to save uploaded files
def save_uploaded_file(uploaded_file, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    file_path = os.path.join(save_dir, uploaded_file.name)
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# Step 1: Parse the CP document
def parse_cp_document(input_dir):
    # Load the document
    doc = Document(input_dir)

    # Initialize containers
    data = {
        "Course_Proposal_Form": {}
    }

    # Function to parse tables with advanced duplication check
    def parse_table(table):
        rows = []
        for row in table.rows:
            # Process each cell and ensure unique content within the row
            cells = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text not in cells:
                    cells.append(cell_text)
            # Ensure unique rows within the table
            if cells not in rows:
                rows.append(cells)
        return rows

    # Function to add text and table content to a section
    def add_content_to_section(section_name, content):
        if section_name not in data["Course_Proposal_Form"]:
            data["Course_Proposal_Form"][section_name] = []
        # Check for duplication before adding content
        if content not in data["Course_Proposal_Form"][section_name]:
            data["Course_Proposal_Form"][section_name].append(content)

    # Variables to track the current section
    current_section = None

    # Iterate through the elements of the document
    for element in doc.element.body:
        if isinstance(element, CT_P):  # It's a paragraph
            para = Paragraph(element, doc)
            text = para.text.strip()
            if text.startswith("Part"):
                current_section = text  # Get the part name (e.g., Part 1, Part 2)
            elif text:
                add_content_to_section(current_section, text)
        elif isinstance(element, CT_Tbl):  # It's a table
            tbl = Table(element, doc)
            table_content = parse_table(tbl)
            if current_section:
                add_content_to_section(current_section, {"table": table_content})

    return data

# Web scraping function integrated directly
def web_scrape(course_title: str, name_of_org: str) -> str:
    # Format the course title for the URL
    formatted_course_title = urllib.parse.quote(course_title)
    search_url = f"https://www.myskillsfuture.gov.sg/content/portal/en/portal-search/portal-search.html?q={formatted_course_title}"
    print(search_url)

    # Set up the Selenium WebDriver (using Chrome here)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        # Load the page with Selenium
        driver.get(search_url)
        time.sleep(3)  # Wait for JavaScript to load content

        # Parse the loaded page with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Locate the specific course-holder div with the class "courses-card-holder is-horizontal"
        course_holder = soup.find('div', class_='courses-card-holder is-horizontal')
        if not course_holder:
            return "No courses found in the specified format."

        # Find all relevant course cards within this container
        course_cards = course_holder.find_all('div', class_='card')

        for card in course_cards:
            # Check if the card has the necessary elements for a course listing
            provider_div = card.find('div', class_='course-provider')
            title_element = card.find('h5', class_='card-title')
            
            if provider_div and title_element:
                provider_name_element = provider_div.find('a')
                if provider_name_element:
                    provider_name = provider_name_element.get_text(strip=True)
                    # Check if this matches the given organization name
                    if name_of_org.lower() in provider_name.lower():
                        # Find the link to the course detail page
                        course_link_element = title_element.find('a')
                        if course_link_element and 'href' in course_link_element.attrs:
                            course_detail_url = "https://www.myskillsfuture.gov.sg" + course_link_element['href']
                            
                            # Request the course detail page
                            driver.get(course_detail_url)
                            time.sleep(5)  # Wait for JavaScript to load the detail page
                            detail_soup = BeautifulSoup(driver.page_source, 'html.parser')

                            # Extract TGS Ref No (Course ID)
                            tgs_ref_no_element = detail_soup.find('div', class_='course-details-header').find('small')
                            tgs_ref_no = tgs_ref_no_element.find('span').get_text(strip=True) if tgs_ref_no_element else None

                            # Extract UEN number
                            uen_element = detail_soup.find('div', class_='course-provider-info-holder').find_next('small')
                            uen_number = uen_element.find('span').get_text(strip=True) if uen_element else None

                            # Return both TGS Ref No and UEN if available
                            return {
                                "TGS_Ref_No": tgs_ref_no,
                                "UEN": uen_number
                            }
        return "TGS Ref No not found"
    finally:
        driver.quit()

def app():
    # Streamlit UI components
    st.title("Courseware Document Generator")

    # Step 1: Upload Course Proposal (CP) Document
    st.header("Step 1: Upload Course Proposal (CP) Document")
    cp_file = st.file_uploader("Upload Course Proposal (CP) Document", type=["docx"])

    # Step 2: Select Name of Organisation
    st.header("Step 2: Select Name of Organisation")

    organisations = [
        "Tertiary Infotech Pte Ltd",
        "CareTech168 LLP",  
        "Chelsea Kidz Academy Pte Ltd",
        "Firstcom Academy Pte Ltd",
        "Fleuriste Pte Ltd",
        "Genetic Computer School Pte Ltd",
        "Hai Leck Engineering Pte Ltd",
        "IES Academy Pte Ltd",
        "Info-Tech Systems Integrators Pte Ltd",
        "InnoHat Training Pte Ltd",
        "Laures Solutions Pte Ltd",
        "QE Safety Consultancy Pte Ltd",
        "OOm Pte Ltd",
        "Raffles Skills Lab International Training Centre Pte Ltd",
        "TRAINOCATE (S) Pte Ltd",
        "SOQ International Academy Pte Ltd"
    ]

    selected_org = st.selectbox("Select Name of Organisation", organisations)

    # Step 3 (Optional): Upload Updated SFW Dataset
    st.header("Step 3 (Optional): Upload Updated Skills Framework (SFw) Dataset")
    sfw_file = st.file_uploader("Upload Updated SFw Dataset (Excel File)", type=["xlsx"])
    if sfw_file:
        sfw_data_dir = save_uploaded_file(sfw_file, 'input/dataset')
        st.success(f"Updated SFw dataset saved to {sfw_data_dir}")
    else:
        sfw_data_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"

    # Step 4: Select Document(s) to Generate using Checkboxes
    st.header("Step 4: Select Document(s) to Generate")
    generate_lg = st.checkbox("Learning Guide (LG)")
    generate_ap = st.checkbox("Assessment Plan (AP)")
    generate_lp = st.checkbox("Lesson Plan (LP)")
    generate_fg = st.checkbox("Facilitator's Guide (FG)")


    # Step 4: Generate Documents
    if st.button("Generate Documents"):
        if cp_file is not None and selected_org:
            # Save the uploaded CP file
            # cp_input_dir = save_uploaded_file(cp_file, 'input/CP')
            # st.success(f"CP document saved to {cp_input_dir}")

            # Step 1: Parse the CP document
            raw_data = parse_cp_document(cp_file)

            # Step 2: Add the current date to the raw_data
            current_datetime = datetime.now()
            current_date = current_datetime.strftime("%d %b %Y")
            year = current_datetime.year
            raw_data["Date"] = current_date
            raw_data["Year"] = year

            # Load environment variables
            dotenv.load_dotenv()

            # Load API key from environment
            # OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
            OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
            GENERATION_MODEL_NAME = st.secrets["GENERATION_MODEL"]
            REPLACEMENT_MODEL_NAME = st.secrets["REPLACEMENT_MODEL"]

            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not found in environment variables.")
            if not GENERATION_MODEL_NAME:
                raise ValueError("MODEL_NAME not found in environment variables.")
            if not REPLACEMENT_MODEL_NAME:
                raise ValueError("MODEL_NAME not found in environment variables.")
            
            gen_config_list = [{"model": GENERATION_MODEL_NAME,"api_key": OPENAI_API_KEY}]
            rep_config_list = [{"model": REPLACEMENT_MODEL_NAME,"api_key": OPENAI_API_KEY}]

            llm_config = {"config_list": gen_config_list, "timeout": 360}
            rep_config = {"config_list": rep_config_list, "timeout": 360}

            # 1. User Proxy Agent (Provides unstructured data to the interpreter)
            user_proxy = UserProxyAgent(
                name="User",
                is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
                human_input_mode="NEVER",  # Automatically provides unstructured data
                code_execution_config={"work_dir": "output", "use_docker": False} # Takes data from a directory
            )

            # 2. Interpreter Agent (Converts unstructured data into structured data)
            interpreter = AssistantAgent(
                name="Interpreter",
                llm_config=llm_config,
                system_message="""
                You are an AI assistant that helps extract specific information from a JSON object containing a Course Proposal Form. Your task is to interpret the JSON data, regardless of its structure, and extract the required information accurately.

                ---

                **Task:** Extract the following information from the provided JSON data:

                ### Part 1: Particulars of Course

                - Name of Organisation
                - Course Title
                - TSC Title
                - TSC Code
                - Total Training Hours (sum of Classroom facilitation, Workplace learning: On-the-Job (OJT), Practicum, Practical, E-learning: Synchronous and Asynchronous), formatted with units (e.g., "30 hrs", "1 hr")
                - Total Assessment Hours, formatted with units (e.g., "2 hrs")
                - Total Course Duration Hours, formatted with units (e.g., "42 hrs")

                ### Part 3: Curriculum Design

                From the Learning Units and Topics Table:

                For each Learning Unit (LU):
                - Learning Unit Title (include the "LUx: " prefix)
                - Topics Covered Under Each LU:
                - For each Topic:
                    - **Topic_Title** (include the "Topic x: " prefix and associated K and A statements in parentheses)
                    - **Bullet_Points** (list of bullet points under the topic)
                - Learning Outcomes (LOs)
                - Numbering and Description for the "K" (Knowledge) Statements (as a list of dictionaries with "K_number" and "Description")
                - Numbering and Description for the "A" (Ability) Statements (as a list of dictionaries with "A_number" and "Description")
                - **Assessment_Methods** (list of assessment methods abbreviation, e.g., ["WA-SAQ", "CS"])
                - **Instructional_Methods** (list of instructional methods)

                ### Part E: Details of Assessment Methods Proposed

                - For each Assessment Method:
                - **Assessment_Method**
                - **Total_Delivery_Hours** (formatted with units, e.g., "1 hr")
                - **Assessor_to_Candidate_Ratio**

                ---

                **Instructions:**

                - Carefully parse the JSON data and locate the sections corresponding to each part.
                - Even if the JSON structure changes, use your understanding to find and extract the required information.
                - Ensure that the `Topic_Title` includes the "Topic x: " prefix and the associated K and A statements in parentheses as they appear in the course proposal.
                - For Learning Outcomes (LOs), always include the "LOx: " prefix (where x is the number) at the beginning of each LO. For example, "LO1: Evaluate organisational needs for integrating cloud solutions with existing systems."
                - Present the extracted information in a structured JSON format, where keys correspond to the placeholders needed for placeholder replacement in a Word document.
                - Ensure all extracted information is accurate and matches the data in the JSON input.
                - **Time fields** should include units, e.g., "40 hrs", "1 hr", "2 hrs".
                - `Assessment_Methods` should be a list of methods.
                - In `Assessment_Methods_Details`, separate each assessment method with its own `Assessor_to_Candidate_Ratio` and `Total_Delivery_Hours`.
                - **Ensure that the sum of `Total_Delivery_Hours` for all assessment methods equals the `Total_Assessment_Hours`.**
                - **If individual `Total_Delivery_Hours` for assessment methods are not specified in the data, divide the `Total_Assessment_Hours` equally among the assessment methods.**
                - Do not include any extraneous information.
                
                **Text Normalization:**
                - When extracting text, especially for assessment methods and other fields, normalize the text by replacing special characters:
                - Replace en dashes (–) with regular hyphens (-)
                - Replace em dashes (—) with regular hyphens (-)
                - Replace curly quotes (" ") with straight quotes (")
                - Replace other non-ASCII characters with their closest ASCII equivalents
                - This normalization should be applied to all extracted text fields to ensure consistency and avoid encoding issues.

                **Additional Validation:**
                1. Calculate Total Training Hours as the sum of all course components (Classroom facilitation, OJT, Practicum, Practical, E-learning Synchronous, E-learning Asynchronous).
                2. Use the Assessment hours as provided in the form for Total Assessment Hours.
                3. Use the Total Duration as specified in the form for Total Course Duration Hours.
                4. Verify that the Total Course Duration Hours matches the sum of Total Training Hours and Total Assessment Hours.
                5. If there's a discrepancy, use the Total Duration specified in the form as the authoritative Total Course Duration Hours
                6. **Bullet Points Validation:**
                   - Compare the number of bullet points extracted for each topic against the source data
                   - If any discrepancy is found, re-extract the bullet points for that topic
                   - Only proceed when all bullet points for all topics are fully extracted
                   - Example: For a topic like "Governance" with 12 bullet points in source, ensure exactly 12 bullet points are extracted:
                     ```
                     "Bullet_Points": [
                         "Organizational Strategy, Goals, and Objectives",
                         "Organizational Structure, Roles and Responsibilities",
                         "Organizational Culture",
                         "Policies and Standards",
                         "Business Processes",
                         "Organizational Assets",
                         "Enterprise Risk Management and Risk Management Framework",
                         "Three Lines of Defense",
                         "Risk Profile",
                         "Risk Appetite and Risk Tolerance",
                         "Legal, Regulatory and Contractual Requirements",
                         "Professional Ethics of Risk Management"
                     ]
                     ```
                     
                ** Output Format**
                - Use double quotes around all field names and string values.
                - Remove any redundant or duplicate entries within the dictionary.
                - Avoid any trailing commas, particularly at the end of arrays or objects.
                - For `Assessment_Methods_Details`, ensure no duplicate assessment entries and verify the total structure aligns with the specified format.
                - Before finalizing, double-check and reformat the dictionary if necessary to prevent any parsing errors on the receiving end.

                **Assessment Method Abbreviation Rules:**
                When processing assessment methods, follow these rules to generate the Method_Abbreviation:

                1. Standard Assessment Method Abbreviations:
                - Written Assessment - Short Answer Questions → WA-SAQ
                - Practical Performance → PP
                - Case Study → CS
                - Oral Questioning → OQ
                - Role Play → RP

                2. For any other assessment method:
                a. If the abbreviation is provided in parentheses, use that abbreviation
                    Example: "Practical Performance (PP)" → "PP"
                
                b. If no abbreviation is provided, create one by:
                    - Taking the first letter of each main word (excluding articles and prepositions)
                    - Joining the letters with hyphens for multi-word methods
                    Example: "Technical Documentation Review" → "TDR"

                3. Special Cases:
                - If the method includes "Written Assessment", always prefix with "WA-"
                - If multiple variations of the same method exist, use the standard abbreviation
                    Example: "Practice Performance", "Practical Performance Assessment" → both use "PP"

                **Output Format Update:**
                In the Assessment_Methods_Details section, always include both the full name and abbreviation

                Return a JSON dictionary object with the following structure:
                import
                ```json
                {
                    "Date":"...",
                    "Year":"...",
                    "Name_of_Organisation": "...",
                    "Course_Title": "...",
                    "TSC_Title": "...",
                    "TSC_Code": "...",
                    "Total_Training_Hours": "...",  // e.g., "38 hrs" 
                    "Total_Assessment_Hours": "...",  // e.g., "2 hrs"
                    "Total_Course_Duration_Hours": "...",  // e.g., "40 hrs"
                    "Learning_Units": [
                        {
                            "LU_Title": "...",
                            "Topics": [
                                {
                                    "Topic_Title": "Topic x: ... (Kx, Ax)",  // Include the "Topic x: " prefix
                                    "Bullet_Points": ["...", "..."]
                                },
                                // Additional Topics
                            ],
                            "LO": "LOx: ...", // Include the "LOx: " prefix
                            "K_numbering_description": [
                                {
                                    "K_number": "K1",
                                    "Description": "..."
                                },
                                // Additional K statements
                            ],
                            "A_numbering_description": [
                                {
                                    "A_number": "A1",
                                    "Description": "..."
                                },
                                // Additional A statements
                            ],
                            "Assessment_Methods": ["...", "..."],  // List of methods, Always use abbreviations e.g., WA-SAQ, PP, CS, OQ, RP
                            "Instructional_Methods": ["...", "..."]  // List of methods
                        },
                        // Additional LUs
                    ],
                    "Assessment_Methods_Details": [
                        {
                            "Assessment_Method": "...", // Always use full term e.g., Written Assessment - Short-Answer Questions (WA-SAQ), Practical Performance (PP), Case Study (CS), Oral Questioning (OQ) 
                            "Method_Abbreviation": ""...", // Abbreviation of Assessment Method e.g., WA-SAQ, PP, CS, OQ, RP
                            "Total_Delivery_Hours": "...",  // e.g., "1 hr"
                            "Assessor_to_Candidate_Ratio": "["...", "..."] // List of min and max ratios e.g., ["1:3 (Min)", "1:5 (Max)"]
                        },
                        // Additional methods
                    ]
                }
                ```
                """,
            )

            agent_tasks = {
                "interpreter": f"""
                Please extract and structure the following data: {raw_data}.
                **Return the extracted information as a complete JSON dictionary containing the specified fields. Do not truncate or omit any data. Include all fields and their full content. Do not use '...' or any placeholders to replace data.**
                Simply return the JSON dictionary object directly and 'TERMINATE'.
                """
            }

            try:
                with st.spinner('Extracting Information from Course Proposal...'):
                    # Run the interpreter agent conversation
                    chat_results = user_proxy.initiate_chats(
                        [
                            {
                                "chat_id": 1,
                                "recipient": interpreter,
                                "message": agent_tasks["interpreter"],
                                "silent": False,
                                "summary_method": "last_msg",
                                "max_turns": 2
                            }
                        ]
                    )
            except Exception as e:
                st.error(f"Error extracting Course Proposal: {e}")

            # Extract the final context dictionary from the agent's response
            try:
                last_message_content = chat_results[-1].chat_history[-1].get("content", "")
                if not last_message_content:
                    st.error("No content found in the agent's last message.")
                    return
                # Clean the content to ensure it's in the expected format
                last_message_content = last_message_content.strip()
                # Extract JSON from triple backticks
                json_pattern = re.compile(r'```json\s*(\{.*?\})\s*```', re.DOTALL)
                json_match = json_pattern.search(last_message_content)
                if json_match:
                    json_str = json_match.group(1)
                    context = json.loads(json_str)
                    print(f"CONTEXT JSON MAPPING: \n\n{context}")
                else:
                    # Try extracting any JSON present in the content
                    json_pattern_alt = re.compile(r'(\{.*\})', re.DOTALL)
                    json_match_alt = json_pattern_alt.search(last_message_content)
                    if json_match_alt:
                        json_str = json_match_alt.group(1)
                        context = json.loads(json_str)
                        print(f"CONTEXT JSON MAPPING: \n\n{context}")
                    else:
                        st.error("No JSON found in the agent's response.")
                        return
            except json.JSONDecodeError as e:
                st.error(f"Error parsing context JSON: {e}")
                return

            # After obtaining the context
            if context:
                # Run web_scrape function to get TGS Ref No and UEN
                try:
                    with st.spinner('Retrieving TGS Ref No and UEN...'):
                        web_scrape_result = web_scrape(context['Course_Title'], context['Name_of_Organisation'])
                        if isinstance(web_scrape_result, dict):
                            # Update context with web_scrape_result
                            context.update(web_scrape_result)
                        else:
                            st.warning(f"Web scrape result: {web_scrape_result}")
                    st.session_state['context'] = context  # Store context in session state
                except Exception as e:
                    st.error(f"Error in web scraping: {e}")
                    return

                # Generate Learning Guide
                if generate_lg:
                    try:
                        with st.spinner('Generating Learning Guide...'):
                            lg_output = generate_learning_guide(context, selected_org, llm_config)
                        st.success(f"Learning Guide generated: {lg_output}")
                        st.session_state['lg_output'] = lg_output  # Store output path in session state
           
                    except Exception as e:
                        st.error(f"Error generating Learning Guide: {e}")

                # Generate Assessment Plan
                if generate_ap:
                    try:
                        with st.spinner('Generating Assessment Plan...'):
                            ap_output = generate_assessment_plan(context, selected_org, rep_config)
                        st.success(f"Assessment Plan generated: {ap_output}")
                        st.session_state['ap_output'] = ap_output  # Store output path in session state
   
                    except Exception as e:
                        st.error(f"Error generating Assessment Plan: {e}")

                # Check if any documents require the timetable
                needs_timetable = (generate_lp or generate_fg)

                # Generate the timetable if needed and not already generated
                if needs_timetable and 'lesson_plan' not in context:
                    try:
                        with st.spinner("Generating Timetable..."):
                            hours = int(''.join(filter(str.isdigit, context["Total_Course_Duration_Hours"])))
                            num_of_days = hours / 8
                            timetable_data = generate_timetable(context, num_of_days, llm_config)
                            context['lesson_plan'] = timetable_data['lesson_plan']
                        st.session_state['context'] = context  # Update context in session state
                    except Exception as e:
                        st.error(f"Error generating timetable: {e}")
                        return  # Exit if timetable generation fails
                    
                # Now generate Lesson Plan
                if generate_lp:
                    try:
                        with st.spinner("Generating Lesson Plan..."):
                            lp_output = generate_lesson_plan(context, selected_org, rep_config)
                        st.success(f"Lesson Plan generated: {lp_output}")
                        st.session_state['lp_output'] = lp_output  # Store output path in session state
                        # Read the file and provide a download button
     
                    except Exception as e:
                        st.error(f"Error generating Lesson Plan: {e}")

                # Generate Facilitator's Guide
                if generate_fg:
                    try:
                        with st.spinner("Generating Facilitator's Guide..."):
                            fg_output = generate_facilitators_guide(context, selected_org, rep_config)
                        st.success(f"Facilitator's Guide generated: {fg_output}")
                        st.session_state['fg_output'] = fg_output  # Store output path in session state

                    except Exception as e:
                        st.error(f"Error generating Facilitator's Guide: {e}")
                
                st.session_state['processing_done'] = True  # Indicate that processing is done

            else:
                st.error("Context is empty. Cannot proceed with document generation.")
        else:
            st.error("Please upload a CP document and select a Name of Organisation.")
 
    if st.session_state.get('processing_done'):
        st.header("Download Generated Documents")

        # Ensure 'context' exists in session state
        if 'context' in st.session_state:
            context = st.session_state['context']
        else:
            st.error("Context not found in session state.")
            st.stop()  # Stops the script execution
            
        # Learning Guide
        lg_output = st.session_state.get('lg_output')
        if lg_output and os.path.exists(lg_output):
            with open(lg_output, "rb") as f:
                file_bytes = f.read()
            # Check if 'TGS_Ref_No' is in context
            if 'TGS_Ref_No' in context and context['TGS_Ref_No']:
                file_name = f"LG_{context['TGS_Ref_No']}_{context['Course_Title']}_v1.docx"
            else:
                file_name = f"LG_{context['Course_Title']}_v1.docx"
            st.download_button(
                label="Download Learning Guide",
                data=file_bytes,
                file_name=file_name,
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

        # Assessment Plan
        ap_output = st.session_state.get('ap_output')
        if ap_output and os.path.exists(ap_output):
            with open(ap_output, "rb") as f:
                file_bytes = f.read()
            # Check if 'TGS_Ref_No' is in context
            if 'TGS_Ref_No' in context and context['TGS_Ref_No']:
                file_name = f"Assessment Plan_{context['TGS_Ref_No']}_{context['Course_Title']}_v1.docx"
            else:
                file_name = f"Assessment Plan_{context['Course_Title']}_v1.docx"
            st.download_button(
                label="Download Assessment Plan",
                data=file_bytes,
                file_name=file_name,
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

        # Lesson Plan
        lp_output = st.session_state.get('lp_output')
        if lp_output and os.path.exists(lp_output):
            with open(lp_output, "rb") as f:
                file_bytes = f.read()
            # Check if 'TGS_Ref_No' is in context
            if 'TGS_Ref_No' in context and context['TGS_Ref_No']:
                file_name = f"LP_{context['TGS_Ref_No']}_{context['Course_Title']}_v1.docx"
            else:
                file_name = f"LP_{context['Course_Title']}_v1.docx"
            st.download_button(
                label="Download Lesson Plan",
                data=file_bytes,
                file_name=file_name,
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

        # Facilitator's Guide
        fg_output = st.session_state.get('fg_output')
        if fg_output and os.path.exists(fg_output):
            with open(fg_output, "rb") as f:
                file_bytes = f.read()
            # Check if 'TGS_Ref_No' is in context
            if 'TGS_Ref_No' in context and context['TGS_Ref_No']:
                file_name = f"FG_{context['TGS_Ref_No']}_{context['Course_Title']}_v1.docx"
            else:
                file_name = f"FG_{context['Course_Title']}_v1.docx"
            st.download_button(
                label="Download Facilitator's Guide",
                data=file_bytes,
                file_name=file_name,
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )