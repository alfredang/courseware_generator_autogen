"""
WSQ Course Brochure Generation Module

Generates professional WSQ course brochures by scraping course information from URLs
and populating standardized templates. Supports multiple PDF generation backends
for cross-platform compatibility.

Author: Wong Xin Ping
Date: 18 September 2025
"""

# Standard library imports
import asyncio
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import requests
import streamlit as st
from bs4 import BeautifulSoup
from pydantic import BaseModel

# Optional imports with fallbacks
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from pyppeteer import launch
    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from xhtml2pdf import pisa
    PDF_GENERATOR = 'xhtml2pdf'
except ImportError:
    try:
        import pdfkit
        PDF_GENERATOR = 'pdfkit'
    except ImportError:
        PDF_GENERATOR = None


# =============================================================================
# CONSTANTS
# =============================================================================

TEMPLATE_ASSET_DIR = (Path(__file__).resolve().parent / "brochure_template").resolve()

TSC_CODE_FRAMEWORK_MAPPING = {
    'AGR': 'Agriculture',
    'BCA': 'Built Environment',
    'CHE': 'Chemical',
    'DAT': 'Data',
    'ELE': 'Electronics',
    'ENE': 'Energy & Chemicals',
    'ENV': 'Environmental Services',
    'FIN': 'Financial Services',
    'FMT': 'Facilities Management',
    'FNB': 'Food & Beverage',
    'ICT': 'Information & Communications Technology',
    'LNF': 'Land & Infrastructure',
    'LOG': 'Logistics',
    'MAN': 'Manufacturing',
    'MAR': 'Marine & Offshore',
    'MED': 'Media',
    'PRC': 'Precision Engineering',
    'RET': 'Retail',
    'SEC': 'Security',
    'SMD': 'Social Media',
    'TOU': 'Tourism',
    'TRA': 'Transportation',
    'WST': 'Waste Management'
}

DEFAULT_COURSE_DATA = {
    "course_title": "WSQ - Professional Course Training",
    "course_description": [
        "This advanced course is designed for professionals eager to dive deep into the realm of building sophisticated systems.",
        "As the course progresses, participants will delve into practical aspects and implementation strategies."
    ],
    "learning_outcomes": [
        "Evaluate core concepts and methodologies",
        "Analyze advanced implementation techniques",
        "Assess practical application scenarios"
    ],
    "tsc_title": "Skills Development",
    "tsc_code": "ICT-INT-0047-1.1",
    "tsc_framework": "ICT",
    "wsq_funding": {
        "Full Fee": "$900",
        "GST": "$81.00",
        "Baseline": "$531.00",
        "MCES / SME": "$351.00"
    },
    "tgs_reference_no": "TGS-2025097470",
    "gst_exclusive_price": "$900.00",
    "gst_inclusive_price": "$981.00",
    "session_days": "2",
    "duration_hrs": "16",
    "course_details_topics": []
}


# =============================================================================
# DATA MODELS
# =============================================================================

class CourseTopic(BaseModel):
    """Represents a course topic with its subtopics."""
    title: str
    subtopics: List[str]


class CourseData(BaseModel):
    """Complete course data structure for brochure generation."""
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

    def to_dict(self) -> Dict:
        """Convert to dictionary for template rendering."""
        return self.dict()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _xhtml2pdf_link_callback(uri: str, rel: str) -> str:
    """
    Helper for xhtml2pdf to resolve relative asset URIs.

    Args:
        uri: The URI to resolve
        rel: Relative path context

    Returns:
        Resolved file path or original URI
    """
    try:
        if uri.startswith(("http://", "https://", "data:")):
            return uri
        resolved = (TEMPLATE_ASSET_DIR / uri).resolve()
        return str(resolved)
    except Exception:
        return uri


def get_framework_from_tsc_code(tsc_code: str) -> str:
    """
    Extract framework from TSC code prefix.

    Args:
        tsc_code: TSC code (e.g., 'ICT-INT-0047-1.1')

    Returns:
        Framework name or 'Not Applicable'
    """
    if not tsc_code or '-' not in tsc_code:
        return "Not Applicable"

    prefix = tsc_code.split('-')[0].upper()
    return TSC_CODE_FRAMEWORK_MAPPING.get(prefix, "Not Applicable")


def create_default_course_data(url: str = "") -> CourseData:
    """
    Create default CourseData object for fallback scenarios.

    Args:
        url: Course URL

    Returns:
        CourseData with default values
    """
    data = DEFAULT_COURSE_DATA.copy()
    data["course_url"] = url
    return CourseData(**data)


# =============================================================================
# WEB SCRAPING FUNCTIONS
# =============================================================================

def scrape_with_browserless(url: str) -> BeautifulSoup:
    """
    Scrape URL using Selenium with Chrome options.

    Args:
        url: URL to scrape

    Returns:
        BeautifulSoup object of the parsed HTML

    Raises:
        Exception: If scraping fails
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        html_content = driver.page_source
        return BeautifulSoup(html_content, 'html.parser')

    finally:
        driver.quit()


def scrape_with_requests(url: str) -> BeautifulSoup:
    """
    Scrape URL using requests library with proper headers.

    Args:
        url: URL to scrape

    Returns:
        BeautifulSoup object of the parsed HTML

    Raises:
        Exception: If request fails
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return BeautifulSoup(response.content, 'html.parser')


def web_scrape_course_info(url: str) -> CourseData:
    """
    Web scrape course information from the provided URL.

    Args:
        url: The URL to scrape course information from

    Returns:
        CourseData object with extracted information
    """
    try:
        # Choose scraping method based on availability
        if SELENIUM_AVAILABLE:
            soup = scrape_with_browserless(url)
        else:
            soup = scrape_with_requests(url)

        # Extract TSC code first to determine framework
        tsc_code = extract_tsc_code(soup)

        # Extract framework directly or use mapping
        extracted_framework = extract_tsc_framework(soup)
        if extracted_framework != "Not Applicable":
            framework = extracted_framework
        else:
            framework = get_framework_from_tsc_code(tsc_code)

        # Build course data object
        course_data = CourseData(
            course_title=extract_course_title_wsq_format(soup),
            course_description=extract_course_description_paragraphs(soup),
            learning_outcomes=extract_learning_outcomes_list(soup),
            tsc_title=extract_tsc_title(soup),
            tsc_code=tsc_code,
            tsc_framework=framework,
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
        return create_default_course_data(url)


# =============================================================================
# CONTENT EXTRACTION FUNCTIONS
# =============================================================================

def extract_course_title_wsq_format(soup: BeautifulSoup) -> str:
    """Extract course title with WSQ prefix formatting."""
    try:
        # Look for title in common locations
        title_selectors = [
            'h1',
            '.course-title',
            '.title',
            '[class*="title"]',
            'title'
        ]

        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title and len(title) > 5:
                    # Ensure WSQ prefix
                    if not title.startswith('WSQ'):
                        title = f"WSQ - {title}"
                    return title

        return "WSQ - Professional Course Training"

    except Exception:
        return "WSQ - Professional Course Training"


def extract_course_description_paragraphs(soup: BeautifulSoup) -> List[str]:
    """Extract course description as list of paragraphs."""
    try:
        descriptions = []

        # Look for description in common containers
        desc_selectors = [
            '.course-description p',
            '.description p',
            '.overview p',
            '.content p'
        ]

        for selector in desc_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:3]:  # Limit to first 3 paragraphs
                    text = elem.get_text().strip()
                    if text and len(text) > 20:
                        descriptions.append(text)

                if descriptions:
                    break

        # Fallback to default if nothing found
        if not descriptions:
            descriptions = [
                "This advanced course is designed for professionals eager to dive deep into the realm of building sophisticated systems.",
                "As the course progresses, participants will delve into practical aspects and implementation strategies."
            ]

        return descriptions

    except Exception:
        return [
            "This advanced course is designed for professionals eager to dive deep into the realm of building sophisticated systems.",
            "As the course progresses, participants will delve into practical aspects and implementation strategies."
        ]


def extract_learning_outcomes_list(soup: BeautifulSoup) -> List[str]:
    """Extract learning outcomes as formatted list."""
    try:
        outcomes = []

        # Look for learning outcomes in various formats
        outcome_selectors = [
            '.learning-outcomes li',
            '.outcomes li',
            '.objectives li',
            '[class*="outcome"] li',
            '[class*="objective"] li'
        ]

        for selector in outcome_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    text = elem.get_text().strip()
                    if text and len(text) > 10:
                        # Clean and format outcome
                        text = re.sub(r'^[•\-\*]\s*', '', text)
                        if not text[0].isupper():
                            text = text.capitalize()
                        outcomes.append(text)

                if outcomes:
                    break

        # Fallback to default outcomes
        if not outcomes:
            outcomes = [
                "Evaluate core concepts and methodologies",
                "Analyze advanced implementation techniques",
                "Assess practical application scenarios"
            ]

        return outcomes[:6]  # Limit to 6 outcomes

    except Exception:
        return [
            "Evaluate core concepts and methodologies",
            "Analyze advanced implementation techniques",
            "Assess practical application scenarios"
        ]


def extract_tsc_code(soup: BeautifulSoup) -> str:
    """Extract TSC code from Skills Framework text."""
    try:
        text = soup.get_text()
        patterns = [
            r'([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s+Level\s+[0-9]+\s*TSC',
            r'([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s*TSC',
            r'([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "ICT-INT-0047-1.1"  # Default fallback

    except Exception:
        return "ICT-INT-0047-1.1"


def extract_tsc_title(soup: BeautifulSoup) -> str:
    """Extract TSC title from Skills Framework text."""
    try:
        text = soup.get_text()
        patterns = [
            r'guideline of\s+([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+):\s+(.*?)\s+under\s+[A-Z]+\s+Skills',
            r'(?:and\s+proficiency\s+level:\s*)?([A-Za-z\s&-]+?)\s+([A-Z]{3}-[A-Z]{3}-[0-9]+-[0-9\.]+)\s+Level\s+[0-9]+\s*TSC\s+under',
            r'([\w\s&-]+?)\s+Level\s+[0-9]+\s*TSC\s+under\s+[\w\s]+Skills\s+Framework'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'guideline of' in pattern:
                    if ':' in match.group(0) and len(match.groups()) >= 2:
                        return match.group(2).strip()
                    else:
                        return match.group(1).strip()
                elif 'Level.*TSC.*under.*Skills.*Framework' in pattern:
                    return match.group(1).strip()
                elif len(match.groups()) >= 2:
                    return match.group(1).strip()
                else:
                    return match.group(1).strip()

        return "Skills Development"  # Default fallback

    except Exception:
        return "Skills Development"


def extract_tsc_framework(soup: BeautifulSoup) -> str:
    """Extract TSC framework from Skills Framework text."""
    try:
        text = soup.get_text()

        # Look for framework patterns
        framework_patterns = [
            r'under\s+([A-Za-z\s&]+)\s+Skills\s+Framework',
            r'Skills\s+Framework\s+for\s+([A-Za-z\s&]+)',
            r'([A-Za-z\s&]+)\s+Skills\s+Framework'
        ]

        for pattern in framework_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                framework = match.strip()
                if len(framework) > 2 and framework.lower() not in ['the', 'and', 'or']:
                    return framework.title()

        return "Not Applicable"

    except Exception:
        return "Not Applicable"


def extract_wsq_funding_table(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract WSQ funding information from tables."""
    try:
        funding = {}

        # Look for funding tables
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip()
                    value = cells[1].get_text().strip()

                    # Match common funding categories
                    if any(term in key.lower() for term in ['fee', 'gst', 'baseline', 'mces', 'sme']):
                        funding[key] = value

        # Fallback to default funding structure
        if not funding:
            funding = {
                "Full Fee": "$900",
                "GST": "$81.00",
                "Baseline": "$531.00",
                "MCES / SME": "$351.00"
            }

        return funding

    except Exception:
        return {
            "Full Fee": "$900",
            "GST": "$81.00",
            "Baseline": "$531.00",
            "MCES / SME": "$351.00"
        }


def extract_tgs_reference_number(soup: BeautifulSoup) -> str:
    """Extract TGS reference number."""
    try:
        text = soup.get_text()

        # Look for TGS patterns
        patterns = [
            r'TGS[- ]?([0-9]{10})',
            r'TGS[- ]?([0-9]{7,12})',
            r'Reference[:\s]*TGS[- ]?([0-9]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"TGS-{match.group(1)}"

        return "TGS-2025097470"  # Default fallback

    except Exception:
        return "TGS-2025097470"


def extract_fee_before_gst_format(soup: BeautifulSoup) -> str:
    """Extract course fee before GST."""
    try:
        text = soup.get_text()

        # Look for fee patterns
        patterns = [
            r'Fee[:\s]*\$([0-9,]+\.?[0-9]*)',
            r'Price[:\s]*\$([0-9,]+\.?[0-9]*)',
            r'Cost[:\s]*\$([0-9,]+\.?[0-9]*)',
            r'\$([0-9,]+\.?[0-9]*)\s*(?:before|excluding|ex)\s*GST'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '')
                return f"${amount}.00" if '.' not in amount else f"${amount}"

        return "$900.00"  # Default fallback

    except Exception:
        return "$900.00"


def extract_fee_with_gst_format(soup: BeautifulSoup) -> str:
    """Extract course fee including GST."""
    try:
        fee_before_gst = extract_fee_before_gst_format(soup)

        # Calculate GST (9% in Singapore)
        base_amount = float(fee_before_gst.replace('$', '').replace(',', ''))
        gst_amount = base_amount * 0.09
        total_amount = base_amount + gst_amount

        return f"${total_amount:.2f}"

    except Exception:
        return "$981.00"


def extract_session_days(soup: BeautifulSoup) -> str:
    """Extract number of session days."""
    try:
        text = soup.get_text()

        # Look for session/day patterns
        patterns = [
            r'([0-9]+)\s*days?',
            r'([0-9]+)\s*sessions?',
            r'Duration[:\s]*([0-9]+)\s*days?'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return "2"  # Default fallback

    except Exception:
        return "2"


def extract_duration_hrs(soup: BeautifulSoup) -> str:
    """Extract course duration in hours."""
    try:
        text = soup.get_text()

        # Look for hour patterns
        patterns = [
            r'([0-9]+)\s*hours?',
            r'([0-9]+)\s*hrs?',
            r'Duration[:\s]*([0-9]+)\s*hours?'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return "16"  # Default fallback

    except Exception:
        return "16"


def extract_course_topics_with_subtopics(soup: BeautifulSoup) -> List[CourseTopic]:
    """Extract course topics with their subtopics."""
    try:
        topics = []

        # Look for structured content (headers + lists)
        headers = soup.find_all(['h2', 'h3', 'h4'])

        for header in headers:
            title = header.get_text().strip()

            # Skip irrelevant headers
            if any(skip in title.lower() for skip in ['contact', 'register', 'about', 'footer']):
                continue

            subtopics = []

            # Look for lists after this header
            next_elem = header.find_next_sibling()
            while next_elem and next_elem.name not in ['h1', 'h2', 'h3', 'h4']:
                if next_elem.name in ['ul', 'ol']:
                    items = next_elem.find_all('li')
                    for item in items:
                        text = item.get_text().strip()
                        if text and len(text) > 5:
                            subtopics.append(text)
                next_elem = next_elem.find_next_sibling()

            # Add topic if it has content
            if title and (subtopics or len(title) > 10):
                if not subtopics:
                    subtopics = [f"Key concepts in {title.lower()}"]

                topics.append(CourseTopic(
                    title=title,
                    subtopics=subtopics[:5]  # Limit subtopics
                ))

        # Ensure we have at least one topic
        if not topics:
            topics = [CourseTopic(
                title="Core Training Modules",
                subtopics=[
                    "Fundamental concepts and principles",
                    "Practical application techniques",
                    "Advanced implementation strategies"
                ]
            )]

        return topics[:4]  # Limit to 4 main topics

    except Exception:
        return [CourseTopic(
            title="Core Training Modules",
            subtopics=[
                "Fundamental concepts and principles",
                "Practical application techniques",
                "Advanced implementation strategies"
            ]
        )]


# =============================================================================
# TEMPLATE PROCESSING FUNCTIONS
# =============================================================================

def populate_brochure_template(course_data: CourseData) -> str:
    """
    Populate the brochure template with course data.

    Args:
        course_data: Course information to populate

    Returns:
        HTML content with populated template
    """
    try:
        # Read template file
        template_path = TEMPLATE_ASSET_DIR / "brochure.html"

        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # Convert course data to dictionary
        data = course_data.to_dict()

        # Add additional computed fields
        data['current_date'] = datetime.now().strftime("%B %Y")
        data['course_description_formatted'] = "\n".join([
            f"<p>{desc}</p>" for desc in data['course_description']
        ])
        data['learning_outcomes_formatted'] = "\n".join([
            f"<li>{outcome}</li>" for outcome in data['learning_outcomes']
        ])

        # Format WSQ funding table
        funding_rows = ""
        for category, amount in data['wsq_funding'].items():
            funding_rows += f"<tr><td>{category}</td><td>{amount}</td></tr>\n"
        data['wsq_funding_rows'] = funding_rows

        # Format course topics
        topics_html = ""
        for i, topic in enumerate(data['course_details_topics'], 1):
            topics_html += f"<h4>{i}. {topic['title']}</h4>\n<ul>\n"
            for subtopic in topic['subtopics']:
                topics_html += f"<li>{subtopic}</li>\n"
            topics_html += "</ul>\n"
        data['course_topics_formatted'] = topics_html

        # Replace placeholders in template
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in template_content:
                template_content = template_content.replace(placeholder, str(value))

        return template_content

    except Exception as e:
        st.error(f"Error populating template: {e}")
        return "<html><body><h1>Error generating brochure content</h1></body></html>"


# =============================================================================
# PDF GENERATION FUNCTIONS
# =============================================================================

def generate_pdf_output(html_content: str, output_path: str) -> bool:
    """
    Generate PDF output from HTML content using multiple backends.

    Args:
        html_content: HTML content to convert
        output_path: Output file path for PDF

    Returns:
        Success status
    """
    try:
        # Try Playwright first (best quality)
        if PLAYWRIGHT_AVAILABLE:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()

                    # Create temporary HTML file
                    temp_html = TEMPLATE_ASSET_DIR / "temp_brochure.html"

                    with open(temp_html, 'w', encoding='utf-8') as f:
                        f.write(html_content)

                    page.goto(f'file://{temp_html}', wait_until='networkidle')

                    page.pdf(
                        path=output_path,
                        format='A4',
                        margin={
                            'top': '25px',
                            'right': '20px',
                            'bottom': '0px',
                            'left': '20px'
                        },
                        print_background=True,
                        prefer_css_page_size=True,
                    )

                    browser.close()

                    # Clean up
                    try:
                        os.remove(temp_html)
                    except:
                        pass

                return True
            except Exception as e:
                st.warning(f"Playwright failed: {e}")

        # Try WeasyPrint (good quality)
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

        # Try pdfkit (requires wkhtmltopdf)
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

        # Try xhtml2pdf (basic quality)
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

        # Final fallback - text-only PDF
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4

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


def generate_brochure_outputs(html_content: str, course_title: str) -> Dict[str, str]:
    """
    Generate PDF output for the brochure.

    Args:
        html_content: Populated HTML content
        course_title: Course title for file naming

    Returns:
        Dictionary with file paths of generated outputs
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


# =============================================================================
# STREAMLIT APPLICATION
# =============================================================================

def display_course_preview(course_data: CourseData) -> None:
    """Display a preview of the extracted course data."""
    st.subheader("📋 Extracted Course Information")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Course Title:**")
        st.write(course_data.course_title)

        st.write("**TSC Information:**")
        st.write(f"Code: {course_data.tsc_code}")
        st.write(f"Title: {course_data.tsc_title}")
        st.write(f"Framework: {course_data.tsc_framework}")

        st.write("**Pricing:**")
        st.write(f"Before GST: {course_data.gst_exclusive_price}")
        st.write(f"After GST: {course_data.gst_inclusive_price}")

    with col2:
        st.write("**Course Duration:**")
        st.write(f"Days: {course_data.session_days}")
        st.write(f"Hours: {course_data.duration_hrs}")

        st.write("**Reference:**")
        st.write(f"TGS: {course_data.tgs_reference_no}")

        st.write("**Topics Count:**")
        st.write(f"{len(course_data.course_details_topics)} main topics")


def display_download_section(outputs: Dict[str, str]) -> None:
    """Display download buttons for generated files."""
    if not outputs:
        st.warning("No files were generated successfully.")
        return

    st.subheader("📥 Download Generated PDF")

    if 'pdf' in outputs:
        with open(outputs['pdf'], 'rb') as pdf_file:
            st.download_button(
                label="📄 Download PDF",
                data=pdf_file.read(),
                file_name=os.path.basename(outputs['pdf']),
                mime="application/pdf"
            )


def app() -> None:
    """Main Streamlit application function."""
    st.title("🎓 WSQ Course Brochure Generator v2")
    st.write("Generate professional WSQ course brochures from course URLs")

    # URL input section
    st.subheader("🔗 Course URL Input")
    url = st.text_input(
        "Enter the course URL:",
        placeholder="https://example.com/course-page",
        help="Paste the URL of the course page you want to create a brochure for"
    )

    if st.button("🚀 Generate Brochure", type="primary"):
        if not url:
            st.warning("Please enter a course URL first.")
            return

        if not url.startswith(('http://', 'https://')):
            st.error("Please enter a valid URL starting with http:// or https://")
            return

        with st.spinner("Scraping course information..."):
            course_data = web_scrape_course_info(url)

        # Display extracted data preview
        display_course_preview(course_data)

        with st.spinner("Generating brochure template..."):
            html_content = populate_brochure_template(course_data)

        # Preview section
        with st.expander("👁️ Preview Generated Content", expanded=False):
            st.components.v1.html(html_content, height=600, scrolling=True)

        with st.spinner("Creating PDF output..."):
            outputs = generate_brochure_outputs(html_content, course_data.course_title)

        # Download section
        display_download_section(outputs)

        st.success("✅ Brochure generation completed!")


if __name__ == "__main__":
    app()