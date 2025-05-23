# document_parser.py

from docx import Document
import json
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph
import re
from difflib import get_close_matches

# Canonical section headers and their normalized forms
SECTION_HEADERS = {
    "course title": ("Course Information", "Course Title"),
    "course level": ("Course Information", "Course Level"),
    "proficiency level": ("Course Information", "Proficiency Level"),
    "organization": ("Course Information", "Name of Organisation"),
    "learning outcomes": ("Learning Outcomes", None),
    "course mapping": ("TSC and Topics", None),
    "assessment methods": ("Assessment Methods", None),
    # Add more as needed
}

def normalize_header(text):
    # Lowercase, remove punctuation, and extra spaces
    return re.sub(r'[^a-z0-9 ]', '', text.lower().strip())

def get_section_key(text):
    norm = normalize_header(text)
    # Try exact match first
    for header_key, (section, key) in SECTION_HEADERS.items():
        if norm.startswith(header_key):
            return section, key, header_key
    # Fuzzy match if not found
    close = get_close_matches(norm, SECTION_HEADERS.keys(), n=1, cutoff=0.8)
    if close:
        section, key = SECTION_HEADERS[close[0]]
        return section, key, close[0]
    return None, None, None

def parse_document(input_docx, output_json):
    # Load the document
    doc = Document(input_docx)

    # Initialize containers
    data = {
        "Course Information": {
            "Course Level": "",
            "Proficiency Level": ""
        },
        "Learning Outcomes": {
            "Learning Outcomes": [],
            "Knowledge": [],
            "Ability": [],
            "Knowledge and Ability Mapping": {},
            "Course Duration": "",
            "Instructional Methods": "",
            "content": []
        },
        "TSC and Topics": {
            "TSC Title": "",
            "TSC Code": "",
            "Topics": [],
            "Learning Units": [],
            "content": []
        },
        "Assessment Methods": {
            "Assessment Methods": [],
            "Amount of Practice Hours": "",
            "Course Outline": {
                "Learning Units": {}
            },
            "content": [],
            "Assessment Details": {
                "Written Exam": "",
                "Practical Exam": "",
                "Total Assessment Hours": ""
            }
        }
    }

    # Ensure all keys from SECTION_HEADERS that map to Course Information are present
    for header_key_init, (section_init, sub_key_init) in SECTION_HEADERS.items():
        if section_init == "Course Information" and sub_key_init:
            if sub_key_init not in data["Course Information"]:
                 data["Course Information"][sub_key_init] = ""

    # Function to parse tables
    def parse_table(table):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        return rows

    # Function to add text and table content
    def add_content_to_section(section_name, content):
        # Ensure section_name exists in data, crucial if it's a new one not in initial struct
        if section_name not in data:
            data[section_name] = {"content": [], "bullet_points": []} # Default structure for new sections

        if isinstance(data.get(section_name), list): # Should not happen with current data structure for top-level sections
            # This case might be for appending to a list *within* a section, handle with care or disallow.
            # For now, assume section_name refers to a dict.
            pass
        elif isinstance(data.get(section_name), dict):
            if "content" not in data[section_name]:
                data[section_name]["content"] = []
            # Add content if not already present (simple duplication check for strings)
            if isinstance(content, dict) and "table" in content: # For tables, allow multiple tables
                 data[section_name]["content"].append(content)
            elif isinstance(content, str) and content not in data[section_name]["content"]:
                data[section_name]["content"].append(content)
            elif not isinstance(content, str): # For non-string, non-table content, append directly (could be other dicts)
                data[section_name]["content"].append(content)

    # Function to detect bullet points using regex
    def is_bullet_point(text):
        bullet_pattern = r"^[•−–●◦*]\s+.*" # Added '*' as a common bullet
        return bool(re.match(bullet_pattern, text))

    # Function to add bullet points under a list
    def add_bullet_point(section_name, bullet_point_text):
        if section_name not in data: 
            data[section_name] = {"bullet_points": [], "content": []} 
        if "bullet_points" not in data[section_name]:
            data[section_name]["bullet_points"] = []
        # Clean bullet prefix before adding
        cleaned_text = re.sub(r"^[•−–●◦*]\s*", "", bullet_point_text).strip()
        if cleaned_text and cleaned_text not in data[section_name]["bullet_points"]:
            data[section_name]["bullet_points"].append(cleaned_text)

    def parse_assessment_methods(text_line):
        # Track all assessment methods with hours
        all_methods_with_hours = {}
        total_hours = 0.0
        
        # Step 1: Extract the text after "Assessment Methods:" if present
        methods_text = text_line
        if "assessment methods" in text_line.lower():
            methods_text = re.sub(r"^.*?assessment methods[:\s-]*", "", text_line, flags=re.IGNORECASE).strip()
        
        # Step 2: Split by commas to get individual methods (handling "and" conjunction)
        individual_methods = re.split(r',|\s+and\s+', methods_text)
        
        # Step 3: Process each method
        for method in individual_methods:
            method = method.strip()
            if not method:
                continue
                
            # Extract method name and hours
            # Pattern matches both parentheses format and other formats
            hours_match = re.search(r'(.*?)(?:\s*\((\d+(?:\.\d+)?)\s*hr?s?\)|\s+(\d+(?:\.\d+)?)\s*hr?s?$)', method, re.IGNORECASE)
            
            if hours_match:
                method_name = hours_match.group(1).strip()
                # Check which group captured the hours (either in parentheses or directly after)
                hours_value = hours_match.group(2) if hours_match.group(2) else hours_match.group(3)
                
                if method_name and hours_value:
                    # Store the method with its hours
                    all_methods_with_hours[method_name] = f"{hours_value} hr"
                    total_hours += float(hours_value)
                    
                    # Special handling for Written and Practical Exams
                    if "written exam" in method_name.lower():
                        data["Assessment Methods"]["Assessment Details"]["Written Exam"] = f"{hours_value} hr"
                    elif "practical exam" in method_name.lower():
                        data["Assessment Methods"]["Assessment Details"]["Practical Exam"] = f"{hours_value} hr"
                    
                    # Add to assessment methods list (cleaned name only)
                    if method_name not in data["Assessment Methods"]["Assessment Methods"]:
                        data["Assessment Methods"]["Assessment Methods"].append(method_name)
            else:
                # If no hours found, just add the method name to the list
                if method not in data["Assessment Methods"]["Assessment Methods"]:
                    data["Assessment Methods"]["Assessment Methods"].append(method)
        
        # Store all_methods_with_hours in the data structure
        if "MethodsWithHours" not in data["Assessment Methods"]:
            data["Assessment Methods"]["MethodsWithHours"] = {}
        data["Assessment Methods"]["MethodsWithHours"].update(all_methods_with_hours)

        # Format total hours appropriately
        if total_hours == int(total_hours):
            data["Assessment Methods"]["Assessment Details"]["Total Assessment Hours"] = f"{int(total_hours)} hr"
        else:
            data["Assessment Methods"]["Assessment Details"]["Total Assessment Hours"] = f"{total_hours:.1f} hr"

    # Variables to track the current section
    current_section = None
    current_lo_subsection = None # Added for K/A within Learning Outcomes

    # Iterate through the elements of the document
    for element in doc.element.body:
        if isinstance(element, CT_P):  # It's a paragraph
            para = Paragraph(element, doc)
            text = para.text.strip()
            if not text: # Skip empty paragraphs
                continue

            is_major_section_header_line = False
            # Attempt to identify a major section header
            # `canonical_header_key` is the matched key from SECTION_HEADERS (e.g., "course title")
            section_from_header, key_in_data, canonical_header_key = get_section_key(text)

            if section_from_header:
                is_major_section_header_line = True
                current_section = section_from_header
                current_lo_subsection = None # Reset LO subsection when a major section changes
                
                # Ensure section exists in data structure
                if current_section not in data:
                    data[current_section] = {"content": [], "bullet_points": []}

                # Specific handling for "Assessment Methods" header line
                if current_section == "Assessment Methods":
                    parse_assessment_methods(text) # Parse hours from the header line itself
                
                if key_in_data: # If the header corresponds to a specific key like "Course Title"
                    value = ""
                    # Strategy 1: Colon splitting (most common and reliable if colon exists)
                    if ':' in text:
                        parts = text.split(':', 1)
                        potential_header_in_line = parts[0].strip()
                        if get_close_matches(normalize_header(potential_header_in_line), [canonical_header_key], n=1, cutoff=0.80): # slightly lower cutoff for colon match
                             value = parts[1].strip()
                    
                    # Strategy 2: If no colon or colon split wasn't confident, use flexible regex
                    if not value and canonical_header_key: 
                        flexible_pattern_parts = [re.escape(word) for word in canonical_header_key.split()]
                        flexible_header_regex = r"\s*".join(flexible_pattern_parts)
                        
                        # Regex to capture header and value:
                        # Group 1: The matched header text (flexible)
                        # Group 2: The value part (everything after header and separator)
                        header_match_re = re.match(rf"({flexible_header_regex})[\s:-]+(.+)", text, re.IGNORECASE | re.DOTALL)
                        if header_match_re:
                            matched_header_text_in_doc = header_match_re.group(1)
                            value_candidate = header_match_re.group(2).strip()
                            if normalize_header(matched_header_text_in_doc) == canonical_header_key:
                                value = value_candidate
                                
                    if value:
                        if current_section not in data: data[current_section] = {} # Should be handled by section init already
                        data[current_section][key_in_data] = value
            # End of `if section_from_header:`

            if current_section and text:
                is_line_consumed_by_specific_parser = False

                if current_section == "Learning Outcomes":
                    # Ensure sub-dictionaries/lists exist
                    if "Learning Outcomes" not in data[current_section]: data[current_section]["Learning Outcomes"] = []
                    if "Knowledge" not in data[current_section]: data[current_section]["Knowledge"] = []
                    if "Ability" not in data[current_section]: data[current_section]["Ability"] = []

                    lo_match = re.match(r"^(LO\d+[:\s.-]*)(.*)", text, re.IGNORECASE)
                    k_match = re.match(r"^(K\d+[:\s.-]*)(.*)", text, re.IGNORECASE)
                    a_match = re.match(r"^(A\d+[:\s.-]*)(.*)", text, re.IGNORECASE)
                    
                    norm_text_lower = text.lower() # For simple keyword checks
                    is_lo_knowledge_header = normalize_header(text).startswith("knowledge")
                    is_lo_ability_header = normalize_header(text).startswith("abilit") 

                    if lo_match:
                        item_content = lo_match.group(2).strip()
                        if item_content and item_content not in data[current_section]["Learning Outcomes"]:
                            data[current_section]["Learning Outcomes"].append(item_content)
                        current_lo_subsection = "Learning Outcomes Item" 
                        is_line_consumed_by_specific_parser = True
                    elif is_lo_knowledge_header:
                        current_lo_subsection = "Knowledge"
                        is_line_consumed_by_specific_parser = True 
                    elif is_lo_ability_header:
                        current_lo_subsection = "Ability"
                        is_line_consumed_by_specific_parser = True 
                    elif k_match and current_lo_subsection == "Knowledge": 
                        item_content = k_match.group(2).strip()
                        if item_content and item_content not in data[current_section]["Knowledge"]:
                            data[current_section]["Knowledge"].append(item_content)
                        is_line_consumed_by_specific_parser = True
                    elif a_match and current_lo_subsection == "Ability": 
                        item_content = a_match.group(2).strip()
                        if item_content and item_content not in data[current_section]["Ability"]:
                            data[current_section]["Ability"].append(item_content)
                        is_line_consumed_by_specific_parser = True
                    elif norm_text_lower.startswith("course duration:"):
                        data[current_section]["Course Duration"] = text.split(":", 1)[-1].strip()
                        is_line_consumed_by_specific_parser = True
                    elif norm_text_lower.startswith("instructional methods:"):
                        data[current_section]["Instructional Methods"] = text.split(":", 1)[-1].strip()
                        is_line_consumed_by_specific_parser = True
                    
                    if not is_line_consumed_by_specific_parser and is_bullet_point(text):
                        add_bullet_point(current_section, text)
                        is_line_consumed_by_specific_parser = True
                    
                    if not is_line_consumed_by_specific_parser and not (is_major_section_header_line and not key_in_data):
                         if not (is_lo_knowledge_header or is_lo_ability_header): 
                            add_content_to_section(current_section, text)
                
                elif current_section == "Assessment Methods":
                    if "Assessment Methods" not in data[current_section]: data[current_section]["Assessment Methods"] = []
                    
                    if not is_major_section_header_line: 
                        parse_assessment_methods(text) 
                    
                    if is_bullet_point(text):
                        method_text_cleaned = re.sub(r"^[•−–●◦*]\s*", "", text).strip()
                        # Update to check for hours in any method, not just exam details
                        has_hours = re.search(r"\(\d+(\.\d+)?\s*hr?s?\)", method_text_cleaned, re.IGNORECASE)
                        
                        # Only add the method name (without hours) to the list
                        if method_text_cleaned:
                            # Extract just the method name by removing the hours part
                            method_name_only = re.sub(r"\s*\(\d+(\.\d+)?\s*hr?s?\)", "", method_text_cleaned)
                            if method_name_only and method_name_only not in data[current_section]["Assessment Methods"]:
                                data[current_section]["Assessment Methods"].append(method_name_only)
                        
                        # Always parse hours from bullet points
                        if has_hours:
                            parse_assessment_methods(method_text_cleaned)
                            
                        is_line_consumed_by_specific_parser = True 
                    
                    if not is_line_consumed_by_specific_parser and not (is_major_section_header_line and not key_in_data):
                        if not text.lower().startswith("assessment methods"): 
                            add_content_to_section(current_section, text)

                else: # Generic content handling for other sections
                    if is_bullet_point(text):
                        add_bullet_point(current_section, text)
                        is_line_consumed_by_specific_parser = True
                    
                    if not is_line_consumed_by_specific_parser and not (is_major_section_header_line and not key_in_data):
                        add_content_to_section(current_section, text)

        elif isinstance(element, CT_Tbl):  # It's a table
            tbl = Table(element, doc)
            table_content = parse_table(tbl)
            if current_section: 
                if current_section not in data: data[current_section] = {"content": [], "bullet_points": []}
                if "content" not in data[current_section]: data[current_section]["content"] = [] # Ensure content list exists
                data[current_section]["content"].append({"table": table_content})
    
    # Convert to JSON
    json_output = json.dumps(data, indent=4, ensure_ascii=False)

    # Save the JSON to a file in the current working directory
    with open(output_json, "w", encoding="utf-8") as json_file:
        json_file.write(json_output)

    print(f"{input_docx} JSON output saved to {output_json}")

# if __name__ == "__main__":
#     # Get input and output file paths from command-line arguments
#     if len(sys.argv) != 3:
#         print("Usage: python document_parser.py <input_docx> <output_json>")
#         sys.exit(1)
#     input_docx = sys.argv[1]
#     output_json = sys.argv[2]
#     parse_document(input_docx, output_json)