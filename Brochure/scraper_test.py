from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from typing import List, Optional
from pydantic import BaseModel

class CourseTopic(BaseModel):
    title: str
    subtopics: List[str]

class CourseData(BaseModel):
    course_description: List[str]
    learning_outcomes: List[str]
    tsc_title: str
    tsc_code: str
    wsq_funding: dict
    tgs_reference_no: str
    gst_exclusive_price: str
    gst_inclusive_price: str
    session_days: str
    duration_hrs: str
    course_details_topics: List[CourseTopic]

# Initialize WebDriver
driver = webdriver.Chrome()  # Ensure the correct path to your ChromeDriver

# Set the window size to a desktop resolution
driver.set_window_size(1366, 768)

course_details_url = "https://www.tertiarycourses.com.sg/building-powerful-e-commerce-stores-with-magento.html"

# Open the course details page
driver.get(course_details_url)

# Scroll to the bottom to ensure all content loads
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

try:
    # Wait for the page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "short-description"))
    )

    # Extract data from the "short-description" div
    short_description = driver.find_element(By.CLASS_NAME, "short-description")
    
    # Extract Course Description
    course_description = [p.text for p in short_description.find_elements(By.TAG_NAME, "p")[:2]]  # First 2 paragraphs

    # Extract Learning Outcomes
    try:
        # Find the h2 with text 'Learning Outcomes'
        learning_outcomes_h2 = short_description.find_element(By.XPATH, ".//h2[contains(text(), 'Learning Outcomes')]")
        # Find the ul that follows it
        learning_outcomes_ul = learning_outcomes_h2.find_element(By.XPATH, "./following-sibling::ul[1]")
        # Extract the li elements
        learning_outcomes = [li.text.strip() for li in learning_outcomes_ul.find_elements(By.TAG_NAME, 'li')]
    except Exception as e:
        learning_outcomes = []
        print(f"Error extracting learning outcomes: NOT APPLICABLE OR NOT FOUND")

    # Extract Skills Framework (TSC Title and TSC Code)
    try:
        skills_framework_text = driver.find_element(
            By.XPATH, "//h2[contains(text(), 'Skills Framework')]/following-sibling::p"
        ).text.strip()
        # Extract TSC Title and TSC Code using regex
        match = re.search(r"guideline of\s+(.*?)\s+(\S+)\s+under", skills_framework_text)
        if match:
            tsc_title = match.group(1).strip()
            tsc_code = match.group(2).strip()
        else:
            tsc_title = "Not Available"
            tsc_code = "Not Available"
    except Exception as e:
        tsc_title = "Not Applicable"
        tsc_code = "Not Applicable"
        print(f"Error extracting Skills Framework: NOT APPLICABLE OR NOT FOUND")

    # Extract WSQ Funding table, including Effective Date
    wsq_funding = {}
    try:
        wsq_funding_table = short_description.find_element(By.TAG_NAME, "table")
        # Extract Effective Date from the first row of the table
        first_row = wsq_funding_table.find_element(By.XPATH, ".//tr[1]")
        effective_date_text = first_row.text.strip()
        match_date = re.search(r"Effective for courses starting from\s*(.*)", effective_date_text)
        if match_date:
            wsq_funding["Effective Date"] = match_date.group(1).strip()
        else:
            wsq_funding["Effective Date"] = "Not Available"

        # Now extract the funding data
        # Headers are manually defined due to the table's complex structure
        headers = ['Full Fee', 'GST', 'Baseline', 'MCES / SME']
        # The data is in the last row of the table
        funding_rows = wsq_funding_table.find_elements(By.TAG_NAME, "tr")
        data_row = funding_rows[-1]
        data_cells = data_row.find_elements(By.TAG_NAME, "td")
        if len(data_cells) == len(headers):
            for i in range(len(headers)):
                wsq_funding[headers[i]] = data_cells[i].text.strip()
        else:
            print("Mismatch in number of headers and data cells")
    except Exception as e:
        wsq_funding = {}
        print(f"Error extracting WSQ funding: NOT APPLICABLE OR NOT FOUND")

    # Extract Course Code (TGS Reference no.)
    try:
        sku_div = driver.find_element(By.CLASS_NAME, "sku")
        tgs_reference = sku_div.text.strip().replace("Course Code:", "").strip()
    except:
        tgs_reference = "Not Applicable"

    # Extract Course Booking (GST-exclusive and GST-inclusive prices)
    try:
        price_box = driver.find_element(By.CLASS_NAME, "price-box")
        gst_exclusive = price_box.find_element(By.CSS_SELECTOR, ".regular-price .price").text.strip()
        gst_inclusive = price_box.find_element(By.ID, "gtP").text.strip()
    except:
        gst_exclusive = "Not Applicable"
        gst_inclusive = "Not Applicable"

    # Extract Course Information (Session days, Duration hrs)
    session_days = "Not Applicable"
    duration_hrs = "Not Applicable"
    try:
        course_info_div = driver.find_element(By.CLASS_NAME, "block-related")
        course_info_list = course_info_div.find_elements(By.CSS_SELECTOR, "#bs-pav li")
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
        pass  # Keep default values

    # Extract Course Details Topics
    course_details_topics = []
    try:
        # Wait for the Course Details section to be present
        course_details_section = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    # Updated XPath to match the desktop version
                    "//div[@class='tabs-panels']//h2[text()='Course Details']/following-sibling::div[@class='std']"
                )
            )
        )

        # Find all <p><strong>Topic X: ...</strong></p> elements
        topic_elements = course_details_section.find_elements(By.XPATH, ".//p[strong]")

        for idx, p_elem in enumerate(topic_elements):
            strong_elem = p_elem.find_element(By.TAG_NAME, "strong")
            # Get the topic title using textContent
            topic_title = strong_elem.get_attribute('textContent').strip()
            # Normalize spaces
            topic_title = ' '.join(topic_title.split())

            if topic_title.startswith('Topic'):
                # Get the following siblings
                subtopics = []
                next_siblings = p_elem.find_elements(By.XPATH, "following-sibling::*")
                for elem in next_siblings:
                    if elem.tag_name == 'ul':
                        subtopics.extend([li.get_attribute('textContent').strip() for li in elem.find_elements(By.TAG_NAME, "li")])
                    elif elem.tag_name == 'p':
                        # Check if the next <p> is another topic or "Final Assessment"
                        try:
                            next_strong = elem.find_element(By.TAG_NAME, "strong")
                            next_topic_title = next_strong.get_attribute('textContent').strip()
                            next_topic_title = ' '.join(next_topic_title.split())
                            if next_topic_title.startswith('Topic') or "Final Assessment" in next_topic_title:
                                break
                        except:
                            continue
                    else:
                        continue
                # Exclude any subtopics that contain "Assessment"
                subtopics = [st for st in subtopics if "Assessment" not in st]
                course_topic = CourseTopic(
                    title=topic_title,
                    subtopics=subtopics
                )
                course_details_topics.append(course_topic)
            else:
                continue  # Skip if not a topic title
    except Exception as e:
        print(f"Error extracting course topics: {e}")
        course_details_topics = []

    # Create CourseData object
    course_data = CourseData(
        course_description=course_description,
        learning_outcomes=learning_outcomes,
        tsc_title=tsc_title,
        tsc_code=tsc_code,
        wsq_funding=wsq_funding,
        tgs_reference_no=tgs_reference,
        gst_exclusive_price=gst_exclusive,
        gst_inclusive_price=gst_inclusive,
        session_days=session_days,
        duration_hrs=duration_hrs,
        course_details_topics=course_details_topics
    )

    # Print extracted data
    print("Course Description:", course_data.course_description)
    print("\nLearning Outcomes:", course_data.learning_outcomes)
    print("\nTSC Title:", course_data.tsc_title)
    print("TSC Code:", course_data.tsc_code)
    print("\nWSQ Funding:", course_data.wsq_funding)
    print("\nTGS Reference No.:", course_data.tgs_reference_no)
    print("\nCourse Booking:")
    print("  GST-Exclusive Price:", course_data.gst_exclusive_price)
    print("  GST-Inclusive Price:", course_data.gst_inclusive_price)
    print("\nCourse Information:")
    print("  Session (days):", course_data.session_days)
    print("  Duration (hrs):", course_data.duration_hrs)
    print("\nCourse Details Topics:")
    for topic in course_data.course_details_topics:
        print(f"Topic Title: {topic.title}")
        print("Subtopics:")
        for sub in topic.subtopics:
            print(f"- {sub}")
        print()

finally:
    driver.quit()
