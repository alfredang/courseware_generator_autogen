"""
File: brochure_generation_v2.py

===============================================================================
Brochure Generation v2 Module
===============================================================================
Description:
    This module generates WSQ Course Brochures by web scraping course information
    from provided URLs and populating the standardized brochure template.
    Outputs are generated in both PDF and Word document formats.

Main Functionalities:
    • web_scrape_course_info(url): Scrapes course information from URL
    • populate_brochure_template(course_data): Fills template with scraped data
    • generate_brochure_outputs(html_content, course_title): Creates PDF and Word outputs
    • app(): Streamlit web interface for the brochure generation process

Dependencies:
    - streamlit
    - requests
    - beautifulsoup4
    - pdfkit or weasyprint
    - jinja2

Author:
    Wong Xin Ping
Date:
    18 September 2025
===============================================================================
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import tempfile
import os
from pathlib import Path
import re
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel

# Data models matching original structure
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
    course_url: str

    def to_dict(self):
        return self.dict()

# Web scraping imports - Multiple browser options
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import asyncio
    from pyppeteer import launch
    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# PDF generation imports - prioritize libraries that don't need external deps
PDF_GENERATOR = None
try:
    from xhtml2pdf import pisa
    PDF_GENERATOR = 'xhtml2pdf'
except ImportError:
    try:
        import pdfkit
        PDF_GENERATOR = 'pdfkit'
    except ImportError:
        PDF_GENERATOR = None

# Note: WeasyPrint import moved to inside PDF generation function to avoid import errors

# Base directory for brochure template assets (e.g., images)
TEMPLATE_ASSET_DIR = (Path(__file__).resolve().parent / "brochure_template").resolve()

# Helper for xhtml2pdf to resolve relative asset URIs (e.g., images) to filesystem paths
def _xhtml2pdf_link_callback(uri, rel):
    try:
        # Allow http(s) and data URIs to pass through
        if uri.startswith("http://") or uri.startswith("https://") or uri.startswith("data:"):
            return uri
        # Resolve relative paths against the template assets directory
        resolved = (TEMPLATE_ASSET_DIR / uri).resolve()
        return str(resolved)
    except Exception:
        # Fallback: return original URI (xhtml2pdf will attempt as-is)
        return uri



def web_scrape_course_info(url: str) -> CourseData:
    """
    Web scrape course information from the provided URL using browserless service.
    
    Args:
        url (str): The URL to scrape course information from
        
    Returns:
        CourseData: Extracted course information
    """
    try:
        if SELENIUM_AVAILABLE:  # Re-enable browserless for better scraping
            # Use browserless service for web scraping
            soup = scrape_with_browserless(url)
        else:
            # Use requests as fallback
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract TSC code first to determine correct framework
        tsc_code = extract_tsc_code(soup)

        # Try to extract framework directly from text first, fallback to mapping
        extracted_framework = extract_tsc_framework(soup)
        if extracted_framework != "Not Applicable":
            framework = extracted_framework
        else:
            framework = get_framework_from_tsc_code(tsc_code)

        # Extract data in original format structure
        course_data = CourseData(
            course_title=extract_course_title_wsq_format(soup),
            course_description=extract_course_description_paragraphs(soup),
            learning_outcomes=extract_learning_outcomes_list(soup),
            tsc_title=extract_tsc_title(soup),
            tsc_code=tsc_code,
            tsc_framework=framework,  # Use extracted framework or fallback to mapping
            wsq_funding=extract_wsq_funding_table(soup),
            tgs_reference_no=extract_tgs_reference_number(soup),
            gst_exclusive_price=extract_fee_before_gst_format(soup),
            gst_inclusive_price=extract_fee_with_gst_format(soup),
            session_days=extract_session_days(soup),
            duration_hrs=extract_duration_hrs(soup),
            course_details_topics=extract_course_topics_with_subtopics(soup),
            course_url=url
        )
        
        return course_data
        
    except Exception as e:
        st.error(f"Error scraping URL: {e}")
        # Return default CourseData object on error with professional defaults
        return CourseData(
            course_title="WSQ - Professional Course Training",
            course_description=[
                "This advanced course is designed for professionals eager to dive deep into the realm of building sophisticated systems.",
                "As the course progresses, participants will delve into practical aspects and implementation strategies."
            ],
            learning_outcomes=[
                "Evaluate core concepts and methodologies",
                "Analyze advanced implementation techniques", 
                "Assess practical application scenarios"
            ],
            tsc_title="Skills Development",
            tsc_code="ICT-INT-0047-1.1",
            tsc_framework="ICT",
            wsq_funding={"Full Fee": "$900", "GST": "$81.00", "Baseline": "$531.00", "MCES / SME": "$351.00"},
            tgs_reference_no="TGS-2025097470",
            gst_exclusive_price="$900.00",
            gst_inclusive_price="$981.00", 
            session_days="2",
            duration_hrs="16",
            course_details_topics=[
                CourseTopic(title="Core Fundamentals", subtopics=["Basic concepts", "Foundational theory"]),
                CourseTopic(title="Advanced Techniques", subtopics=["Practical implementation", "Best practices"]),
                CourseTopic(title="Real-world Applications", subtopics=["Case studies", "Industry examples"])
            ],
            course_url=url
        )


def scrape_with_browserless(url: str):
    """
    Scrape website using browserless service with Selenium.
    
    Args:
        url (str): URL to scrape
        
    Returns:
        BeautifulSoup: Parsed HTML content
    """
    try:
        # Get browserless configuration from Streamlit secrets
        browserless_endpoint = st.secrets.get("BROWSER_WEBDRIVER_ENDPOINT", "")
        browserless_token = st.secrets.get("BROWSER_TOKEN", "")
        
        if not browserless_endpoint:
            raise Exception("BROWSER_WEBDRIVER_ENDPOINT not configured in secrets")
        
        # Set up Chrome options for browserless
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Add token to browserless endpoint if available
        if browserless_token and not browserless_endpoint.endswith('/webdriver'):
            if '?' in browserless_endpoint:
                browserless_endpoint = f"{browserless_endpoint}&token={browserless_token}"
            else:
                browserless_endpoint = f"{browserless_endpoint}?token={browserless_token}"
        
        # Initialize remote WebDriver
        driver = webdriver.Remote(
            command_executor=browserless_endpoint,
            options=chrome_options
        )
        
        try:
            # Navigate to the URL
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source and parse with BeautifulSoup
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            return soup
            
        finally:
            driver.quit()
            
    except Exception as e:
        st.warning(f"Browserless scraping failed: {e}. Falling back to requests.")
        # Fallback to requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        return BeautifulSoup(response.content, 'html.parser')


def extract_course_title_wsq_format(soup):
    """Extract course title in WSQ format from the webpage"""
    # Try multiple selectors for course title
    selectors = [
        'h1',
        '.course-title', 
        '.title',
        '.page-title',
        'title'
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            title = element.get_text().strip()
            if title and len(title) > 10:
                # Format as WSQ title if not already formatted
                if not title.startswith('WSQ -'):
                    title = f"WSQ - {title}"
                return title
    
    return "WSQ - Course Title Not Found"


def extract_course_description_paragraphs(soup):
    """Extract course description paragraphs (list format like original)"""
    # Try to find course description in various sections
    descriptions = []
    
    # Look for course descriptions in various sections
    description_selectors = [
        '.short-description p',
        '.product-description p',
        '.course-description p',
        '.description p',
        'p'
    ]
    
    for selector in description_selectors:
        elements = soup.select(selector)
        for elem in elements:
            text = elem.get_text().strip()
            if len(text) > 100 and any(word in text.lower() for word in ['course', 'designed', 'professional', 'learn', 'training']):
                descriptions.append(text)
                if len(descriptions) >= 2:  # Limit to 2 paragraphs like original
                    break
        if descriptions:
            break
    
    # Fallback descriptions if nothing found
    if not descriptions:
        descriptions = [
            "This advanced course is designed for professionals eager to dive deep into the realm of building sophisticated systems.",
            "As the course progresses, participants will delve into practical aspects and implementation strategies."
        ]
    
    return descriptions[:2]  # Return max 2 paragraphs


def extract_learning_outcomes_list(soup):
    """Extract learning outcomes as a list (like original format)"""
    outcomes = []
    
    # Try multiple approaches to find learning outcomes
    learning_outcome_selectors = [
        'h2:contains("Learning Outcomes") + ul li',
        'h3:contains("Learning Outcomes") + ul li',
        '.learning-outcomes li',
        'h2:contains("What You") + ul li',
        'h3:contains("What You") + ul li'
    ]
    
    # Try CSS selectors first
    for selector in learning_outcome_selectors:
        try:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text().strip()
                if len(text) > 20:
                    if not text.endswith('.'):
                        text += '.'
                    outcomes.append(text)
        except:
            continue
    
    # If no outcomes found with CSS, try manual search
    if not outcomes:
        headings = soup.find_all(['h2', 'h3', 'h4'])
        for heading in headings:
            if any(term in heading.get_text().lower() for term in ['learning outcome', 'what you', 'objectives', 'you will learn']):
                # Find the next ul/ol element
                next_list = heading.find_next(['ul', 'ol'])
                if next_list:
                    items = next_list.find_all('li')
                    for item in items:
                        text = item.get_text().strip()
                        if len(text) > 20:
                            if not text.endswith('.'):
                                text += '.'
                            outcomes.append(text)
                    break
    
    # Fallback outcomes if nothing found
    if not outcomes:
        outcomes = [
            "Evaluate Large Language Model (LLM) AI models by identifying their strengths and limitations.",
            "Analyze Retrieval-augmented generation (RAG) algorithms to improve efficiency.",
            "Assess the feasibility of implementing multi-agent AI applications."
        ]
    
    return outcomes[:5]  # Limit to 5 outcomes max


def extract_tsc_title(soup):
    """Extract TSC title from Skills Framework text"""
    text = soup.get_text()
    patterns = [
        # More specific patterns first - "guideline of" patterns
        r'guideline of\s+(.*?)\s+([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s+TSC',
        r'follows the guideline of\s+(.*?)\s+([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)',
        r'guideline of\s+([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+):\s+(.*?)\s+under\s+[A-Z]+\s+Skills',
        # Pattern for technical skills format "Data Storytelling and Visualisation FSE-DAT-5020-1.1 Level 5 TSC"
        r'(?:and\s+proficiency\s+level:\s*)?([A-Za-z\s&-]+?)\s+([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s+Level\s+[0-9]+\s*TSC\s+under',
        # Pattern for descriptive format "Data Analytics and Information Technology Management - Data Mining and Modelling Level 4 TSC"
        r'([\w\s&-]+?)\s+Level\s+[0-9]+\s*TSC\s+under\s+[\w\s]+Skills\s+Framework',
        # Generic patterns (less specific, use as fallback)
        r'([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+):\s+(.*?)\s+under\s+.*?Skills\s+Framework'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # For "guideline of" patterns - title is in group 1
            if 'guideline of' in pattern:
                if ':' in match.group(0) and len(match.groups()) >= 2:
                    # Pattern with TSC code first, title is in group 2
                    return match.group(2).strip()
                else:
                    # Normal pattern, title is in group 1
                    return match.group(1).strip()
            # For descriptive format pattern (only has one group - the title)
            elif 'Level.*TSC.*under.*Skills.*Framework' in pattern:
                return match.group(1).strip()
            # For technical skills patterns (group 1 is title, group 2 is TSC code)
            elif len(match.groups()) >= 2:
                return match.group(1).strip()
            else:
                return match.group(1).strip()

    return "Not Applicable"


def extract_tsc_code(soup):
    """Extract TSC code from Skills Framework text"""
    text = soup.get_text()
    patterns = [
        # Pattern for standard TSC code format
        r'[\w\s&]+?\s*([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s+Level\s+[0-9]+\s*TSC\s+under',
        r'[\w\s&]+?\s*([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s*TSC\s+under',
        # Existing patterns
        r'guideline of\s+.*?\s+([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s+TSC',
        r'([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s+TSC',
        r'([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Check if it's descriptive format without standard TSC code
    descriptive_match = re.search(r'([\w\s&-]+?)\s+Level\s+[0-9]+\s*TSC\s+under\s+[\w\s]+Skills\s+Framework', text, re.IGNORECASE)
    if descriptive_match:
        return "Not Applicable"  # No standard TSC code format

    return "Not Applicable"


def get_framework_from_tsc_code(tsc_code):
    """Map TSC code prefix to Skills Framework name"""
    if not tsc_code or tsc_code == "Not Applicable":
        return "Not Applicable"

    # Extract prefix (e.g., "ICT" from "ICT-ACE-5030-1.1")
    prefix = tsc_code.split('-')[0] if '-' in tsc_code else tsc_code[:3]

    # TSC prefix to Skills Framework mapping
    framework_mapping = {
        'ACC': 'Accountancy',
        'RET': 'Retail',
        'MED': 'Media',
        'ICT': 'Infocomm Technology',
        'BEV': 'Built Environment',
        'DSN': 'Design',
        'DNS': 'Design',
        'AGR': 'Agriculture',
        'ELE': 'Electronics',
        'LOG': 'Logistics',
        'STP': 'Sea Transport',
        'TOU': 'Tourism',
        'AER': 'Aerospace',
        'ATP': 'Air Transport',
        'BPM': 'BioPharmaceuticals Manufacturing',
        'ECM': 'Energy and Chemicals',
        'EGS': 'Engineering Services',
        'EPW': 'Energy and Power',
        'EVS': 'Environmental Services',
        'FMF': 'Food Manufacturing',
        'FSE': 'Financial Services',
        'FSS': 'Food Services',
        'HAS': 'Hotel and Accommodation Services',
        'HCE': 'Healthcare',
        'HRS': 'Human Resource',
        'INP': 'Intellectual Property',
        'LNS': 'Landscape',
        'MAR': 'Marine and Offshore',
        'PRE': 'Precision Engineering',
        'PTP': 'Public Transport',
        'SEC': 'Security',
        'SSC': 'Social Service',
        'TAE': 'Training and Adult Education',
        'WPH': 'Workplace Safety and Health',
        'WST': 'Wholesale Trade',
        'ECC': 'Early Childhood Care and Education',
        'ART': 'Arts'
    }

    return framework_mapping.get(prefix, "Not Applicable")

def extract_tsc_framework(soup):
    """Extract TSC framework from Skills Framework text"""
    text = soup.get_text()
    patterns = [
        # New pattern for "FSE-DAT-5020-1.1 Level 5 TSC under Financial Services Skills Framework" (handles \xa0)
        r'[A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+\s+(?:Level\s+[0-9]+\s*)?TSC\s+under\s+([\w\s]+?)\s+Skills\s+Framework',
        # Existing patterns
        r'TSC\s+under\s+([\w\s]+?)\s+Skills\s+Framework',
        r'under\s+([\w\s]+?)\s+Skills\s+Framework',
        r'([\w\s]+?)\s+Skills\s+Framework'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            framework = match.group(1).strip()
            # Clean up common extra words
            framework = re.sub(r'\s+', ' ', framework)
            return framework

    return "Not Applicable"


def extract_wsq_funding_table(soup):
    """Extract WSQ funding values from Tertiary Courses website with correct table format"""
    funding_data = {
        "Effective Date": "Not Available",
        "Full Fee": "Not Available", 
        "GST": "Not Available",
        "Baseline": "Not Available",
        "MCES / SME": "Not Available"
    }
    
    try:
        full_text = soup.get_text()
        
        # Find effective date first
        date_match = re.search(r'Effective for Courses starting from (\d{1,2}\s+\w+\s+\d{4})', full_text, re.IGNORECASE)
        if date_match:
            funding_data['Effective Date'] = date_match.group(1)
        
        # Look for WSQ funding table by finding the table structure
        tables = soup.find_all('table')
        for table in tables:
            table_text = table.get_text()
            
            # Check if this is the funding table by looking for specific content
            if all(term in table_text for term in ['Full', 'Fee', 'GST', 'Baseline', 'MCES']):
                rows = table.find_all('tr')
                
                # Find data row with dollar amounts
                for row in rows:
                    row_text = row.get_text()
                    # Look for row with dollar amounts (should have multiple $ signs)
                    dollar_matches = re.findall(r'\$(\d+(?:,\d+)?(?:\.\d{2})?)', row_text)
                    
                    if len(dollar_matches) >= 4:  # Should have at least 4 dollar amounts
                        funding_data['Full Fee'] = f"${dollar_matches[0]}"
                        funding_data['GST'] = f"${dollar_matches[1]}" 
                        funding_data['Baseline'] = f"${dollar_matches[2]}"
                        funding_data['MCES / SME'] = f"${dollar_matches[3]}"
                        break
                        
                if funding_data['Full Fee'] != "Not Available":
                    break
        
        # Fallback: Extract from text patterns if table parsing fails
        if funding_data['Full Fee'] == "Not Available":
            # Look for dollar amounts in the text near funding keywords
            funding_section = re.search(r'starting from.{1,500}?(\$\d+.*?\$\d+.*?\$\d+.*?\$\d+)', full_text, re.DOTALL)
            if funding_section:
                amounts = re.findall(r'\$(\d+(?:,\d+)?(?:\.\d{2})?)', funding_section.group(1))
                if len(amounts) >= 4:
                    funding_data['Full Fee'] = f"${amounts[0]}"
                    funding_data['GST'] = f"${amounts[1]}"
                    funding_data['Baseline'] = f"${amounts[2]}"
                    funding_data['MCES / SME'] = f"${amounts[3]}"
        
    except Exception as e:
        pass
    
    return funding_data


def extract_tgs_reference_number(soup):
    """Extract TGS reference number (course code)"""
    text = soup.get_text()
    patterns = [
        r'Course Code[:\s]+([A-Z0-9-]+)',
        r'TGS[:\s]*-?[:\s]*([0-9]+)',
        r'Reference[:\s]+([A-Z0-9-]+)',
        r'Code[:\s]+([A-Z0-9-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            code = match.group(1)
            # Format as TGS if not already
            if not code.startswith('TGS'):
                code = f"TGS-{code}"
            return code
    
    # Generate a TGS code format as fallback
    import random
    return f"TGS-{random.randint(2020000000, 2030000000)}"


def extract_session_days(soup):
    """Extract session days information"""
    text = soup.get_text()
    patterns = [
        r'Session\s*\(days\)[:\s]*(\d+)',
        r'Session[:\s]+(\d+)\s*days?',
        r'(\d+)\s*days?\s*session',
        r'Duration[:\s]*(\d+)\s*days?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "Not Applicable"


def extract_duration_hrs(soup):
    """Extract duration in hours"""
    text = soup.get_text()
    patterns = [
        r'Duration\s*\(hrs\)[:\s]*(\d+)',
        r'Duration[:\s]+(\d+)\s*hrs?',
        r'(\d+)\s*hrs?\s*duration',
        r'(\d+)\s*hours?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "Not Applicable"


def extract_course_topics_with_subtopics(soup):
    """Extract course topics with subtopics as CourseTopic objects"""
    topics = []
    
    try:
        # Look for course details section with more comprehensive selectors
        details_selectors = [
            '.course-details',
            '#course-details',
            '.course-outline',
            '.syllabus',
            '.curriculum',
            '.course-content',
            '.learning-units',
            '.modules',
            '.topics'
        ]
        
        details_section = None
        for selector in details_selectors:
            details_section = soup.select_one(selector)
            if details_section:
                break
        
        if not details_section:
            # Look for details in tabs or sections
            headings = soup.find_all(['h2', 'h3', 'h4'])
            for heading in headings:
                heading_text = heading.get_text().lower()
                if any(term in heading_text for term in ['course details', 'outline', 'syllabus', 'curriculum', 'modules', 'learning units', 'lu1', 'lu2']):
                    details_section = heading.parent or heading.find_next()
                    break

            # If still not found, use the entire page
            if not details_section:
                details_section = soup
        
        if details_section:
            # Find topic headings with subtopics - look more broadly
            topic_headings = details_section.find_all(['h3', 'h4', 'h5', 'strong', 'b'])

            for heading in topic_headings:
                title = heading.get_text().strip()

                # Filter out non-topic headings (but keep Final Assessment and Learning Units)
                excluded_terms = [
                    'requirements', 'entry requirements', 'minimum requirements',
                    'prerequisites', 'eligibility', 'certification', 'certificate',
                    'funding', 'fees', 'pricing'
                ]

                # Accept Learning Units (LU1, LU2, etc.) and Final Assessment specifically
                is_learning_unit = title.lower().startswith('lu') and any(char.isdigit() for char in title)
                is_final_assessment = 'final assessment' in title.lower() or 'final assement' in title.lower()

                if (len(title) > 5 and
                    (is_learning_unit or is_final_assessment or
                     not any(term in title.lower() for term in excluded_terms))):  # Valid topic title

                    subtopics = []

                    # Find subtopics (usually in the next ul/ol)
                    next_list = heading.find_next(['ul', 'ol'])
                    if next_list:
                        items = next_list.find_all('li')
                        for item in items:
                            subtopic_text = item.get_text().strip()

                            # Filter out entry requirements and assessment methods from subtopics
                            excluded_subtopic_terms = [
                                'gce', 'o levels', 'computer literacy', 'minimum', 'able to operate',
                                'written assessment', 'short answer questions', 'wa-saq', 'practical performance',
                                'pp)', 'assessment method', 'evaluation', 'test', 'exam'
                            ]

                            # For Final Assessment, allow shorter terms like "MCQ"
                            min_length = 2 if 'final assessment' in title.lower() else 3

                            if (len(subtopic_text) > min_length and
                                not any(term in subtopic_text.lower() for term in excluded_subtopic_terms)):
                                subtopics.append(subtopic_text)

                    # Special handling for Final Assessment
                    if 'final assessment' in title.lower():
                        # Always add Final Assessment, even without subtopics
                        topics.append(CourseTopic(title=title, subtopics=subtopics))
                    elif subtopics:  # Only add other topics that have subtopics
                        topics.append(CourseTopic(title=title, subtopics=subtopics))
    except:
        pass
    
    # Enhanced fallback - try to extract LU patterns from text if HTML structure fails
    if not topics:
        import re
        page_text = soup.get_text()

        # Look for Learning Unit patterns in the text
        lu_patterns = re.findall(r'(LU\d+[^\n]*)', page_text)

        if lu_patterns:
            print(f"Found {len(lu_patterns)} Learning Units in text, extracting with content...")

            # For each LU, try to find its content/subtopics
            for i, lu_text in enumerate(lu_patterns):
                lu_text = lu_text.strip()
                if len(lu_text) > 5:  # Valid LU title

                    # Try to find content for this LU by looking for text after it
                    lu_subtopics = []

                    # Look for the LU in the HTML structure to find associated content
                    lu_elements = soup.find_all(text=re.compile(re.escape(lu_text), re.IGNORECASE))

                    for lu_element in lu_elements:
                        parent = lu_element.parent if lu_element.parent else None
                        if parent:
                            # Look for lists or content after this LU
                            next_sibling = parent.find_next(['ul', 'ol', 'div', 'p'])
                            if next_sibling:
                                if next_sibling.name in ['ul', 'ol']:
                                    # Found a list - extract list items
                                    items = next_sibling.find_all('li')
                                    for item in items:
                                        item_text = item.get_text().strip()
                                        # Filter out assessment methods
                                        if (len(item_text) > 3 and
                                            not any(term in item_text.lower() for term in [
                                                'written assessment', 'practical performance', 'wa-saq', 'pp)'
                                            ])):
                                            lu_subtopics.append(item_text)
                                elif next_sibling.name in ['div', 'p']:
                                    # Found text content
                                    content_text = next_sibling.get_text().strip()
                                    if (len(content_text) > 10 and
                                        not any(term in content_text.lower() for term in [
                                            'written assessment', 'practical performance'
                                        ])):
                                        # Split into bullet points if it's a long text
                                        if len(content_text) > 100:
                                            # Try different splitting methods
                                            if 'Topic' in content_text:
                                                # Find and extract "Topic X: Description" patterns
                                                topic_matches = re.findall(r'Topic \d+[^T]*?(?=Topic \d+|$)', content_text)
                                                for match in topic_matches:
                                                    match = match.strip()
                                                    if len(match) > 15:  # Valid topic description
                                                        # Clean up the match
                                                        match = re.sub(r'^Topic \d+[:.\s]*', '', match)  # Remove "Topic X:" prefix
                                                        match = match.strip()
                                                        if len(match) > 10:
                                                            lu_subtopics.append(match)
                                            else:
                                                # Split by sentences
                                                sentences = content_text.split('.')
                                                for sentence in sentences[:3]:  # Take first 3 sentences
                                                    if len(sentence.strip()) > 10:
                                                        lu_subtopics.append(sentence.strip())
                                        else:
                                            lu_subtopics.append(content_text)

                    # If no specific content found, add a generic description
                    if not lu_subtopics:
                        lu_number = f"LU{i+1}"
                        if "introduction" in lu_text.lower():
                            lu_subtopics = ["Overview of core concepts", "Foundational principles"]
                        elif "evaluate" in lu_text.lower():
                            lu_subtopics = ["Assessment techniques", "Evaluation methods"]
                        elif "develop" in lu_text.lower():
                            lu_subtopics = ["Implementation strategies", "Development practices"]
                        else:
                            lu_subtopics = ["Learning objectives", "Practical applications"]

                    topics.append(CourseTopic(
                        title=lu_text,
                        subtopics=lu_subtopics[:5]  # Limit to 5 subtopics max
                    ))

        # If still no topics, use generic fallback
        if not topics:
            topics = [
                CourseTopic(
                    title="Introduction to Core Concepts",
                    subtopics=["Overview of fundamental concepts", "Basic principles and theory", "Practical applications"]
                ),
                CourseTopic(
                    title="Intermediate Implementation",
                    subtopics=["Advanced techniques", "Best practices", "Real-world scenarios"]
                ),
                CourseTopic(
                    title="Advanced Applications",
                    subtopics=["Complex problem solving", "Industry applications", "Case studies"]
                )
            ]

    # Clean up duplicate final assessments and fix typos
    final_assessment_topics = []
    other_topics = []

    for topic in topics:
        if 'final assessment' in topic.title.lower() or 'final assement' in topic.title.lower():
            final_assessment_topics.append(topic)
        else:
            other_topics.append(topic)

    # Remove duplicates and ensure we have exactly one Final Assessment
    if final_assessment_topics:
        topics = other_topics + [CourseTopic(title="Final Assessment", subtopics=[])]
    else:
        topics.append(CourseTopic(title="Final Assessment", subtopics=[]))

    return topics  # Return all topics found - no artificial limit


def get_topic_title(topics_list, index):
    """Helper function to get topic title by index"""
    if index < len(topics_list):
        topic = topics_list[index]
        if isinstance(topic, dict):
            title = topic.get('title', f'Learning Unit {index + 1}')
        elif hasattr(topic, 'title'):
            title = topic.title
        else:
            title = f'Learning Unit {index + 1}'
        
        # Format as LU1:, LU2: etc.
        if not title.startswith('LU'):
            return f'LU{index + 1}: {title}'
        return title
    return f'LU{index + 1}: Course Content Module'


def get_topic_details(topics_list, index):
    """Helper function to get topic details by index"""
    if index < len(topics_list):
        topic = topics_list[index]
        if isinstance(topic, dict):
            subtopics = topic.get('subtopics', [])
        elif hasattr(topic, 'subtopics'):
            subtopics = topic.subtopics
        else:
            subtopics = []
        
        if subtopics:
            # Format subtopics with T1:, T2:, etc. prefixes
            formatted_subtopics = []
            for i, subtopic in enumerate(subtopics):
                formatted_subtopics.append(f"T{i+1}:{subtopic}")
            return '<br>'.join(formatted_subtopics)
    
    return f'T1: Topic {index + 1} content details\nT2: Practical exercises and implementation\nT3: Assessment activities'


def format_learning_outcomes_html(outcomes):
    """Format learning outcomes as HTML list items for the template"""
    if not outcomes:
        outcomes = [
            "Understand core concepts and principles",
            "Apply practical skills in real-world scenarios",
            "Evaluate and assess implementation effectiveness"
        ]
    
    formatted_outcomes = []
    for i, outcome in enumerate(outcomes):
        # Remove LO prefix if present and format as list item
        clean_outcome = outcome.replace(f"LO{i+1}:", "").replace("LO:", "").strip()
        formatted_outcomes.append(f"<li>{clean_outcome}</li>")
    
    return '\n    '.join(formatted_outcomes)


def format_course_outline_table(topics):
    """Format course topics as HTML table for the new template format"""
    if not topics:
        # Default topics structure matching professional format
        topics = [
            CourseTopic(title="Introduction to Core Technologies", subtopics=[
                "Overview of fundamental concepts",
                "Setting up development environment", 
                "Basic implementation principles"
            ]),
            CourseTopic(title="Advanced Implementation Techniques", subtopics=[
                "Best practices and methodologies",
                "Practical hands-on exercises",
                "Real-world application scenarios"
            ]),
            CourseTopic(title="Professional Application & Assessment", subtopics=[
                "Industry case studies",
                "Performance optimization",
                "Final project assessment"
            ])
        ]
    
    # Create HTML table matching the professional brochure format
    table_html = """
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <thead>
            <tr style="background-color: #f5f5f5;">
                <th style="border: 1px solid #333; padding: 12px; text-align: left; font-weight: bold;">Learning Unit</th>
                <th style="border: 1px solid #333; padding: 12px; text-align: left; font-weight: bold;">Topics</th>
            </tr>
        </thead>
        <tbody>
    """
    
    # Process topics (limit to 3 main units for 5-page format)
    for i, topic in enumerate(topics[:3]):
        if isinstance(topic, dict):
            title = topic.get('title', f'Learning Unit {i+1}')
            subtopics = topic.get('subtopics', [])
        elif hasattr(topic, 'title'):
            title = topic.title
            subtopics = topic.subtopics if hasattr(topic, 'subtopics') else []
        else:
            title = str(topic)
            subtopics = []
        
        # Format subtopics with T1:, T2:, etc.
        formatted_subtopics = []
        for j, subtopic in enumerate(subtopics):  # No limit - extract all subtopics
            formatted_subtopics.append(f"T{j+1}: {subtopic}")
        
        subtopics_text = "<br>".join(formatted_subtopics) if formatted_subtopics else f"T1: {title} content details<br>T2: Practical implementation"
        
        table_html += f"""
            <tr>
                <td style="border: 1px solid #333; padding: 12px; vertical-align: top; font-weight: bold; width: 30%;">
                    LU{i+1}: {title}
                </td>
                <td style="border: 1px solid #333; padding: 12px; vertical-align: top; width: 70%;">
                    {subtopics_text}
                </td>
            </tr>
        """
    
    # Add Final Assessment row
    table_html += """
            <tr>
                <td style="border: 1px solid #333; padding: 12px; vertical-align: top; font-weight: bold;">
                    Final Assessment
                </td>
                <td style="border: 1px solid #333; padding: 12px; vertical-align: top;">
                    T1: Practical assessment<br>T2: Knowledge evaluation<br>T3: Project demonstration
                </td>
            </tr>
        </tbody>
    </table>
    """
    
    return table_html


# Removed problematic formatting functions that were breaking template structure
# Now using direct text replacement to preserve exact brochure.html format


def extract_topic_with_intro(soup, index):
    """Extract topic titles formatted like the PDF example"""
    # Example format: "Topic 1: Introduction to Large Language Model (LLM) AI Orchestration"
    headings = soup.find_all(['h2', 'h3', 'h4'])
    topics = []
    
    for heading in headings:
        text = heading.get_text().strip()
        if len(text) > 15 and len(text) < 120:
            # Format as topic if not already formatted
            if not text.startswith('Topic'):
                text = f"Topic {index + 1}: {text}"
            topics.append(text)
    
    topic_templates = [
        "Topic 1: Introduction to Large Language Model (LLM) AI Orchestration",
        "Topic 2: Retrieval-Augmented Generation (RAG)", 
        "Topic 3: Implementing a Multi-Agent AI Workflow"
    ]
    
    if index < len(topics):
        return topics[index]
    elif index < len(topic_templates):
        return topic_templates[index]
    
    return f"Topic {index + 1}: Course Content Module"


def extract_topic_details_formatted(soup, index):
    """Extract topic details in bullet format like PDF example"""
    # Template details matching the PDF structure
    template_details = [
        "Overview of LLM AI orchestration\nRunning local LLM\nBuilding an LLM app\nDebugging LLM app",
        "Overview of Retrieval-augmented generation (RAG)\nText Embedding\nVector database\nSimilarity Search\nBuilding an RAG",
        "Introduction to the ReAct agent framework\nImplementing a ReAct agent\nEquipping agent with tools and skills\nOverview of multi-agent AI frameworks - LangGraph, CrewAI, AutoGen etc\nSetting up and running your first multi agent workflow"
    ]
    
    # Try to extract structured content from webpage
    sections = soup.find_all(['div', 'section'])
    for section in sections:
        items = section.find_all('li')
        if len(items) > 2:  # If we find a substantial list
            details = []
            for item in items[:6]:  # Limit to 6 items per topic
                text = item.get_text().strip()
                if len(text) > 10:
                    details.append(text)
            if details:
                return '\n'.join(details)
    
    # Return template details
    if index < len(template_details):
        return template_details[index]
    
    return "Course content details\nPractical exercises\nHands-on implementation\nAssessment activities"


def extract_course_code_format(soup):
    """Extract course code in TGS format"""
    text = soup.get_text()
    patterns = [
        r'Course Code[:\s]+([A-Z0-9-]+)',
        r'Code[:\s]+([A-Z0-9-]+)',
        r'(TGS-[0-9]+)',
        r'Reference[:\s]+([A-Z0-9-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Generate a TGS code format
    import random
    return f"TGS-{random.randint(2020000000, 2030000000)}"


def extract_skills_framework_format(soup):
    """Extract skills framework in exact PDF format"""
    text = soup.get_text()
    patterns = [
        r'Skills Framework[:\s]+(.*?)(?:\n|TSC|under)',
        r'Framework[:\s]+(.*?)(?:\n|TSC|under)', 
        r'(.*?)TSC.*?Skills Framework',
        r'TSC[:\s]+(.*?)(?:\n|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            framework = match.group(1).strip()
            if len(framework) > 10:
                return framework[:200]
    
    # Default format matching PDF example
    return "Artificial Intelligence Application AER-TEM-4026-1.1 TSC under ICT Skills Framework"


def extract_fee_before_gst_format(soup):
    """Extract fee before GST in exact format"""
    text = soup.get_text()
    patterns = [
        r'\$(\d+(?:,\d+)?(?:\.\d{2})?)\s*(?:\()?(?:Bef|Before).*?GST',
        r'(?:Fee|Cost|Price)[:\s]+\$(\d+(?:,\d+)?(?:\.\d{2})?)',
        r'\$(\d+(?:,\d+)?(?:\.\d{2})?)\s*(?:before|bef)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"${match.group(1)}.00" if '.' not in match.group(1) else f"${match.group(1)}"
    
    return "$900.00"


def extract_fee_with_gst_format(soup):
    """Extract fee with GST in exact format"""
    text = soup.get_text()
    patterns = [
        r'\$(\d+(?:,\d+)?(?:\.\d{2})?)\s*(?:\()?(?:Incl|Including).*?GST',
        r'Total[:\s]+\$(\d+(?:,\d+)?(?:\.\d{2})?)',
        r'\$(\d+(?:,\d+)?(?:\.\d{2})?)\s*(?:with|incl)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"${match.group(1)}.00" if '.' not in match.group(1) else f"${match.group(1)}"
    
    # Calculate GST if we have before GST amount
    before_gst = extract_fee_before_gst_format(soup)
    if before_gst != "$900.00":
        try:
            amount = float(before_gst.replace('$', '').replace(',', ''))
            with_gst = amount * 1.09  # Singapore GST 9%
            return f"${with_gst:.2f}"
        except:
            pass
            
    return "$981.00"


def extract_time_schedule_format(soup):
    """Extract time schedule in exact format"""
    text = soup.get_text()
    patterns = [
        r'Time[:\s]+([\d:]+\s*(?:am|pm)\s*-\s*[\d:]+\s*(?:am|pm))',
        r'Schedule[:\s]+([\d:]+\s*(?:am|pm)\s*-\s*[\d:]+\s*(?:am|pm))',
        r'([\d:]+\s*(?:am|pm)\s*-\s*[\d:]+\s*(?:am|pm))',
        r'(\d+:\d+\s*-\s*\d+:\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            time_str = match.group(1)
            # Standardize format
            time_str = time_str.replace('AM', 'am').replace('PM', 'pm')
            return time_str
    
    return "9:30am-6:30pm"


def extract_duration_format(soup):
    """Extract duration in exact format"""
    text = soup.get_text()
    patterns = [
        r'Duration[:\s]+(\d+\s*hrs?\s*(?:\(\d+\s*days?\))?)',
        r'(\d+\s*hrs?\s*(?:\(\d+\s*days?\))?)',
        r'(\d+\s*hours?\s*(?:\(\d+\s*days?\))?)',
        r'(\d+\s*days?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            duration = match.group(1).lower()
            # Standardize format
            duration = duration.replace('hours', 'hrs').replace('hour', 'hr')
            if 'day' in duration and 'hr' not in duration:
                # Convert days to hours (assuming 8 hrs/day)
                days = int(re.search(r'(\d+)', duration).group(1))
                hours = days * 8
                return f"{hours}hrs ({days} days)"
            return duration
    
    return "16hrs (2 days)"


def extract_requirement_formatted(soup, index):
    """Extract requirements in exact bullet format"""
    requirements_from_pdf = [
        "Able to operate using computer functions with minimum Computer Literacy Level 2 based on ICAS Computer Skills Assessment Framework.",
        "Minimum 3 GCE 'O' Levels Passes including English or WPL Level 5 (Average of Reading, Listening, Speaking & Writing Scores)."
    ]
    
    # Try to extract from webpage
    text = soup.get_text()
    requirement_patterns = [
        r'(?:prerequisite|requirement|entry).*?(?:\n.*?){1,5}',
        r'(?:minimum|basic).*?(?:\n.*?){1,3}'
    ]
    
    extracted_reqs = []
    for pattern in requirement_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            clean_req = re.sub(r'\s+', ' ', match).strip()
            if len(clean_req) > 20:
                extracted_reqs.append(clean_req)
    
    if index < len(extracted_reqs):
        return extracted_reqs[index]
    elif index < len(requirements_from_pdf):
        return requirements_from_pdf[index]
    
    return f"Entry requirement {index + 1} as per WSQ standards."


def extract_full_fee_for_table(soup):
    """Extract full fee for funding table"""
    before_gst = extract_fee_before_gst_format(soup)
    return before_gst.replace('.00', '') if before_gst.endswith('.00') else before_gst


def extract_gst_amount_for_table(soup):
    """Extract GST amount for funding table"""
    before_gst = extract_fee_before_gst_format(soup)
    try:
        amount = float(before_gst.replace('$', '').replace(',', ''))
        gst = amount * 0.09
        return f"${gst:.2f}"
    except:
        return "$81.00"


def extract_baseline_fee_calculated(soup):
    """Calculate baseline net fee (typical WSQ funding)"""
    try:
        with_gst = extract_fee_with_gst_format(soup)
        amount = float(with_gst.replace('$', '').replace(',', ''))
        # Typical baseline funding covers about 40-50%
        baseline_net = amount * 0.54  # User pays ~54%
        return f"${baseline_net:.2f}"
    except:
        return "$531.00"


def extract_mces_fee_calculated(soup):
    """Calculate MCES/SME net fee (enhanced WSQ funding)"""
    try:
        with_gst = extract_fee_with_gst_format(soup)
        amount = float(with_gst.replace('$', '').replace(',', ''))
        # MCES/SME gets higher funding, user pays less
        mces_net = amount * 0.36  # User pays ~36%  
        return f"${mces_net:.2f}"
    except:
        return "$351.00"


# Old extraction functions removed - now using format-specific functions above


def populate_brochure_template(course_data: CourseData) -> str:
    """
    Populate the brochure template with scraped course data.
    
    Args:
        course_data (dict): Course information extracted from web scraping
        
    Returns:
        str: Populated HTML content
    """
    # Get the correct path to the brochure template
    current_dir = Path(__file__).parent  # Current module directory
    template_path = current_dir / "brochure_template" / "brochure.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Convert CourseData to dict for easier processing
        data_dict = course_data.to_dict()
        
        # Replace content in the brochure.html template with scraped data
        # This replaces specific content that should be scraped instead of hardcoded
        
        # Replace course title (appears multiple times)
        course_title = data_dict.get('course_title', 'WSQ - Professional Course Training')
        template_content = template_content.replace(
            'WSQ - Design and Build Responsive Websites from Scratch',
            course_title
        )
        
        # Replace about course paragraphs
        about_paragraphs = data_dict.get('course_description', [
            'This advanced course is designed for professionals eager to dive deep into the realm of building sophisticated systems.',
            'As the course progresses, participants will delve into practical aspects and implementation strategies.'
        ])
        
        if len(about_paragraphs) >= 1:
            template_content = template_content.replace(
                'Elevate your web development skills with our course on Responsive Web Interface Design using Bootstrap. This course equips you with the knowledge and practical skills to build visually appealing and highly functional web interfaces. You\'ll learn how to use Bootstrap\'s grid system, components, and utilities to design layouts that adapt seamlessly to various screen sizes. The course covers essential concepts like navigation bars, form controls, and responsive typography, ensuring you can create professional-quality websites.',
                about_paragraphs[0]
            )
            
        if len(about_paragraphs) >= 2:
            template_content = template_content.replace(
                'In addition to the core Bootstrap components, this course also delves into best practices for user experience (UX) design. You\'ll understand how to conduct basic usability tests, apply responsive design patterns, and optimize site performance. These complementary skills will enable you to create web interfaces that not only look good but also provide an exceptional user experience, making you a more versatile and employable front-end developer.',
                about_paragraphs[1]
            )
        
        # Replace learning outcomes - PRESERVE EXACT HTML STRUCTURE
        learning_outcomes = data_dict.get('learning_outcomes', [])
        if learning_outcomes and len(learning_outcomes) > 0:
            # Build complete learning outcomes list dynamically
            outcomes_html = []
            for outcome in learning_outcomes:
                # Clean the outcome text (remove LO prefixes, extra dots)
                clean_outcome = outcome.replace('LO1:', '').replace('LO2:', '').replace('LO3:', '').replace('LO4:', '').replace('LO5:', '').replace('LO6:', '').strip().rstrip('.')
                outcomes_html.append(f'            <li>{clean_outcome}.</li>')
            
            # Replace the entire learning outcomes list
            old_outcomes_block = '''            <li>Identify Bootstrap framework functionalities and information flows for responsive web interface.</li>
            <li>Develop components and design GUI.</li>
            <li>Evaluate the web responsiveness and interactivity.</li>
            <li>Apply Bootstrap framework to update single page design.</li>'''
            
            new_outcomes_block = '\n'.join(outcomes_html)
            template_content = template_content.replace(old_outcomes_block, new_outcomes_block)
        
        # Replace course outline table content - GENERATE COMPLETE TABLE DYNAMICALLY
        course_topics = data_dict.get('course_details_topics', [])
        if course_topics and len(course_topics) > 0:
            # Build complete course outline table HTML for ALL topics with dynamic pagination
            table_rows = []

            for topic in course_topics:
                # Handle both dict and object formats
                if isinstance(topic, dict):
                    topic_title = topic.get('title', 'Course Topic')
                    topic_subtopics = topic.get('subtopics', [])
                else:
                    topic_title = getattr(topic, 'title', 'Course Topic')
                    topic_subtopics = getattr(topic, 'subtopics', [])

                # Add topic header row
                table_rows.append(f'                    <tr>')
                table_rows.append(f'                        <td class="topic-header"><strong>{topic_title}</strong></td>')
                table_rows.append(f'                    </tr>')

                # Add subtopics content row (skip for Final Assessment)
                if topic_subtopics and 'final assessment' not in topic_title.lower():
                    subtopics_text = '<br>\n                        '.join(topic_subtopics)
                    table_rows.append(f'                    <tr>')
                    table_rows.append(f'                        <td>{subtopics_text}</td>')
                    table_rows.append(f'                    </tr>')
            
            # Replace the entire hardcoded table content
            old_table_content = '''                    <tr>
                        <td class="topic-header"><strong>Topic 1: Overview of Responsive Web Interface Design and Bootstrap</strong></td>
                    </tr>
                    <tr>
                        <td>What is Responsive Web Design?<br>
                        Introduction to Bootstrap Framework<br>
                        Create Responsive Web Layout using Bootstrap</td>
                    </tr>
                    <tr>
                        <td class="topic-header"><strong>Topic 2: Components and Graphics Content</strong></td>
                    </tr>
                    <tr>
                        <td>Create Basic Bootstrap Components<br>
                        Design GUI with Style and Content Elements</td>
                    </tr>
                    <tr>
                        <td class="topic-header"><strong>Topic 3: Interactivity and Responsiveness</strong></td>
                    </tr>
                    <tr>
                        <td>Create Interactive Components<br>
                        Apply Bootstrap Utilities<br>
                        Evaluate Web Interface Interactivity and Responsiveness<br>
                        Passing Data via Props</td>
                    </tr>
                    <tr>
                        <td class="topic-header"><strong>Topic 4: Single Page Design</strong></td>
                    </tr>
                    <tr>
                        <td>Web Design Requirement for Single Page<br>
                        Implement Single Page Design</td>
                    </tr>
                    <tr>
                        <td class="topic-header"><strong>Final Assessment</strong></td>
                    </tr>'''
            
            new_table_content = '\n'.join(table_rows)
            template_content = template_content.replace(old_table_content, new_table_content)
        
        # Replace course information
        template_content = template_content.replace('TGS-2021002504', data_dict.get('tgs_reference_no', 'TGS-2025097470'))

        # Handle TSC information - format differently based on whether there's a standard TSC code
        tsc_title = data_dict.get('tsc_title', 'Skills Development')
        tsc_code = data_dict.get('tsc_code', 'ICT-INT-0047-1.1')

        if tsc_code == "Not Applicable":
            # For descriptive format without standard TSC code
            tsc_info = f"{tsc_title} TSC"
        else:
            # For standard TSC code format
            tsc_info = f"{tsc_title} {tsc_code} TSC"

        # Replace the entire Skills Framework line including HTML structure
        old_skills_framework = '<strong>User Interface Design ICT-DES-3008-1.1 TSC</strong> under ICT Skills Framework'
        new_skills_framework = f"<strong>{tsc_info}</strong> under {data_dict.get('tsc_framework', 'ICT')} Skills Framework"
        template_content = template_content.replace(old_skills_framework, new_skills_framework)
        
        # Replace fees
        template_content = template_content.replace('$750.00 (Bef. GST)', f"{data_dict.get('gst_exclusive_price', '$900.00')} (Bef. GST)")
        template_content = template_content.replace('$817.50 (Incl. GST)', f"{data_dict.get('gst_inclusive_price', '$981.00')} (Incl. GST)")
        
        # Replace duration
        duration_text = f"{data_dict.get('duration_hrs', '16')}hrs ({data_dict.get('session_days', '2')} days)"
        template_content = template_content.replace('16hrs (2 days)', duration_text)
        
        # Replace registration link
        registration_url = data_dict.get('course_url', 'https://www.tertiarycourses.com.sg/')
        template_content = template_content.replace('https://www.tertiarycourses.com.sg/wsq-bootstrap-web-design.html', registration_url)
        
        # Replace funding table values
        wsq_funding = data_dict.get('wsq_funding', {})
        template_content = template_content.replace('$750', wsq_funding.get('Full Fee', '$900').replace('.00', ''))
        template_content = template_content.replace('$67.50', wsq_funding.get('GST', '$81.00'))
        template_content = template_content.replace('$442.50', wsq_funding.get('Baseline', '$531.00'))
        template_content = template_content.replace('$292.50', wsq_funding.get('MCES / SME', '$351.00'))
        
        # Replace certificate information
        template_content = template_content.replace('User Interface Design<br>\n                        ICT-DES-3008-1.1 TSC', f"{data_dict.get('tsc_title', 'Skills Development')}<br>\n                        {data_dict.get('tsc_code', 'ICT-INT-0047-1.1')} TSC")
        
        return template_content
        
    except Exception as e:
        st.error(f"Error reading template: {e}")
        st.error(f"Template path attempted: {template_path}")
        return ""


def generate_pdf_output(html_content: str, output_path: str) -> bool:
    """
    Generate PDF output from HTML content using Playwright for perfect CSS preservation.
    
    Args:
        html_content (str): HTML content to convert
        output_path (str): Output file path for PDF
        
    Returns:
        bool: Success status
    """
    try:
        # Use Playwright for PDF generation first - best CSS support
        if PLAYWRIGHT_AVAILABLE:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    
                    # Create temporary HTML file in template directory so images can be loaded
                    import tempfile
                    import os
                    temp_html = os.path.join(TEMPLATE_ASSET_DIR, "temp_brochure.html")
                    
                    # Write HTML content to temporary file in template directory
                    with open(temp_html, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # Navigate to the file so images load properly
                    page.goto(f'file://{temp_html}', wait_until='networkidle')
                    
                    # Generate PDF with proper margins
                    page.pdf(
                        path=output_path,
                        format='A4',
                        margin={
                            'top': '25px',
                            'right': '20px', 
                            'bottom': '0px',
                            'left': '20px'
                        },
                        print_background=True,  # Preserve background colors and images
                        prefer_css_page_size=True,  # Use CSS page size if specified
                    )
                    
                    browser.close()
                    
                    # Clean up temporary file
                    try:
                        os.remove(temp_html)
                    except:
                        pass
                        
                return True
            except Exception as e:
                st.warning(f"Playwright failed: {e}")
        
        # Fallback to WeasyPrint if Playwright fails
        try:
            from weasyprint import HTML
            HTML(string=html_content, base_url=str(TEMPLATE_ASSET_DIR)).write_pdf(
                output_path,
                stylesheets=None,
                presentational_hints=True,
            )
            return True
        except ImportError:
            st.warning("WeasyPrint not available")
        except Exception as e:
            st.warning(f"WeasyPrint failed: {e}")

        # Fallback to pdfkit (uses wkhtmltopdf)
        if PDF_GENERATOR == 'pdfkit':
            try:
                import pdfkit
                pdfkit.from_string(html_content, output_path, options={
                    'page-size': 'A4',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': "UTF-8",
                    'no-outline': None,
                    'enable-local-file-access': None
                })
                return True
            except Exception as e:
                st.warning(f"pdfkit failed: {e}")

        # Fallback to xhtml2pdf
        if PDF_GENERATOR == 'xhtml2pdf':
            try:
                with open(output_path, 'wb') as output_file:
                    pisa_status = pisa.CreatePDF(
                        html_content,
                        dest=output_file,
                        link_callback=_xhtml2pdf_link_callback,
                        encoding='UTF-8',
                        show_error_as_pdf=True
                    )
                    return not pisa_status.err
            except Exception as e:
                st.warning(f"xhtml2pdf failed: {e}")

        # Final fallback - simple text PDF
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text()
            
            c = canvas.Canvas(output_path, pagesize=A4)
            _, height = A4
            
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "Course Brochure")
            
            c.setFont("Helvetica", 10)
            y_position = height - 100
            
            lines = text_content.split('\n')
            for line in lines[:50]:
                if y_position < 50:
                    c.showPage()
                    y_position = height - 50
                    
                c.drawString(50, y_position, line.strip()[:80])
                y_position -= 15
            
            c.save()
            st.warning("PDF generated using fallback method (text-only)")
            return True
            
        except ImportError:
            st.error("No PDF generator available. Please install playwright or weasyprint.")
            return False
            
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return False




def generate_brochure_outputs(html_content: str, course_title: str) -> dict:
    """
    Generate PDF output.

    Args:
        html_content (str): Populated HTML content
        course_title (str): Course title for file naming

    Returns:
        dict: File paths of generated outputs
    """
    # Create safe filename
    safe_title = re.sub(r'[^\w\s-]', '', course_title)
    safe_title = re.sub(r'[-\s]+', '-', safe_title)

    # Create temporary files
    temp_dir = tempfile.mkdtemp()

    pdf_path = os.path.join(temp_dir, f"{safe_title}_brochure.pdf")

    outputs = {}

    # Generate PDF
    if generate_pdf_output(html_content, pdf_path):
        outputs['pdf'] = pdf_path

    return outputs


def app():
    """
    Streamlit web interface for Brochure Generation v2.
    """
    st.title("📄 Generate Brochure v2")
    st.markdown("Generate WSQ Course Brochures by web scraping course information from URLs")
    
    st.divider()
    
    # URL Input Section
    st.subheader("🔗 Course URL")
    course_url = st.text_input(
        "Enter the course URL to scrape information from:",
        placeholder="https://example.com/course-page",
        help="💡 Paste or type the course URL here"
    )

    st.divider()
    
    # Generation Section
    if st.button("🚀 Generate Brochure", type="primary"):
        if not course_url:
            st.error("❌ Please enter a course URL first")
            return

        if not course_url.startswith(('http://', 'https://')):
            st.error("❌ Please enter a valid URL starting with http:// or https://")
            return
        
        with st.spinner("Scraping course information..."):
            # Step 1: Web scrape course information
            course_data = web_scrape_course_info(course_url)
            
            if not course_data or not course_data.course_title:
                st.error("Failed to scrape course information from the provided URL")
                return
        
        with st.spinner("Generating brochure..."):
            # Step 2: Populate template
            html_content = populate_brochure_template(course_data)
            
            if not html_content:
                st.error("Failed to populate brochure template")
                return
        
        with st.spinner("Creating output files..."):
            # Step 3: Generate outputs
            outputs = generate_brochure_outputs(html_content, course_data.course_title)
            
            if not outputs:
                st.error("Failed to generate output files")
                return
        
        st.success("✅ Brochure generated successfully!")
        
        # Display extracted information
        with st.expander("📋 Extracted Course Information"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Course Title:**", course_data.course_title)
                st.write("**Course Code:**", course_data.tgs_reference_no)
                st.write("**Duration:**", f"{course_data.duration_hrs}hrs ({course_data.session_days} days)")
                st.write("**TSC Code:**", course_data.tsc_code)
            
            with col2:
                st.write("**Fee (Before GST):**", course_data.gst_exclusive_price)
                st.write("**Fee (With GST):**", course_data.gst_inclusive_price)
                tsc_framework = f"{course_data.tsc_title} {course_data.tsc_code} under {course_data.tsc_framework} Skills Framework".strip()
                st.write("**Skills Framework:**", tsc_framework[:100] + "..." if len(tsc_framework) > 100 else tsc_framework)
        
        # Show template preview
        with st.expander("🔍 Template Preview (First 500 characters)"):
            st.code(html_content[:500] + "..." if len(html_content) > 500 else html_content)
        
        # Download Section
        st.subheader("📥 Download Generated PDF")

        # PDF Download
        if 'pdf' in outputs:
            with open(outputs['pdf'], 'rb') as pdf_file:
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_file.read(),
                    file_name=f"{course_data.course_title.replace(' ', '_')}_brochure.pdf",
                    mime="application/pdf"
                )


if __name__ == "__main__":
    app()
