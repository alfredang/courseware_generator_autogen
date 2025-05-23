import json
import sys
import os
from CourseProposal.utils.helpers import load_json_file, extract_lo_keys, recursive_get_keys
import pandas as pd
import re


def extract_and_concatenate_json_values(json_data, keys_to_extract, new_key_name):
    """
    Extracts values from JSON data based on keys, concatenates them into a string with newlines,
    and returns a dictionary containing the concatenated string under a new key.

    Args:
        json_data (dict): The JSON data as a dictionary.
        keys_to_extract (list of str): A list of keys to extract values from. Keys are used directly as in JSON.
        new_key_name (str): The name of the new key for the concatenated string in the output.

    Returns:
        dict: A dictionary containing the new key and the concatenated string, or None if input json_data is None.
    """
    if json_data is None:
        return None

    concatenated_string = ""
    for key_path in keys_to_extract:  # Iterate through keys as they are, NO parsing needed
        try:
            value = json_data.get(key_path)  # Use key_path directly as the JSON key

            if value is None:
                print(f"Warning: Key '{key_path}' not found in JSON data.")
                continue  # Skip to the next key if not found

            if isinstance(value, list):
                concatenated_string += "\n\n".join(map(str, value)) + "\n\n"  # Map to str to handle non-string list elements if any
            else:  # If value is not a list (e.g., string, number)
                concatenated_string += str(value) + "\n\n"  # Ensure it's a string

        except KeyError:
            print(f"Error: Key '{key_path}' not found in JSON data.")
        except TypeError as e:  # Handle cases where indexing might be attempted on non-list
            print(f"TypeError accessing key '{key_path}': {e}")

    output_data = {new_key_name: concatenated_string.rstrip('\n\n')}  # rstrip to remove trailing newline
    return output_data

def extract_and_concatenate_json_values_singlenewline(json_data, keys_to_extract, new_key_name):
    """
    Extracts values from JSON data based on keys, concatenates them into a string with newlines,
    and returns a dictionary containing the concatenated string under a new key.

    Args:
        json_data (dict): The JSON data as a dictionary.
        keys_to_extract (list of str): A list of keys to extract values from. Keys are used directly as in JSON.
        new_key_name (str): The name of the new key for the concatenated string in the output.

    Returns:
        dict: A dictionary containing the new key and the concatenated string, or None if input json_data is None.
    """
    if json_data is None:
        return None

    concatenated_string = ""
    for key_path in keys_to_extract:  # Iterate through keys as they are, NO parsing needed
        try:
            value = json_data.get(key_path)  # Use key_path directly as the JSON key

            if value is None:
                print(f"Warning: Key '{key_path}' not found in JSON data.")
                continue  # Skip to the next key if not found

            if isinstance(value, list):
                concatenated_string += "\n".join(map(str, value)) + "\n"  # Map to str to handle non-string list elements if any
            else:  # If value is not a list (e.g., string, number)
                concatenated_string += str(value) + "\n"  # Ensure it's a string

        except KeyError:
            print(f"Error: Key '{key_path}' not found in JSON data.")
        except TypeError as e:  # Handle cases where indexing might be attempted on non-list
            print(f"TypeError accessing key '{key_path}': {e}")

    output_data = {new_key_name: concatenated_string.rstrip('\n')}  # rstrip to remove trailing newline
    return output_data

def extract_and_concatenate_json_values_space_seperator(json_data, keys_to_extract, new_key_name):
    """
    Extracts values from JSON data based on keys, concatenates them into a string with spaces, THIS METHOD IS DIFFERENT FROM THE ONE WITH NO SPACES
    and returns a dictionary containing the concatenated string under a new key.

    Args:
        json_data (dict): The JSON data as a dictionary.
        keys_to_extract (list of str): A list of keys to extract values from. Keys are used directly as in JSON.
        new_key_name (str): The name of the new key for the concatenated string in the output.

    Returns:
        dict: A dictionary containing the new key and the concatenated string, or None if input json_data is None.
    """
    if json_data is None:
        return None

    concatenated_string = ""
    for key_path in keys_to_extract: # Iterate through keys as they are, NO parsing needed
        try:
            value = json_data.get(key_path) # Use key_path directly as the JSON key

            if value is None:
                print(f"Warning: Key '{key_path}' not found in JSON data.")
                continue # Skip to the next key if not found

            if isinstance(value, list):
                concatenated_string += " ".join(map(str, value)) + " " # Map to str to handle non-string list elements if any
            else: # If value is not a list (e.g., string, number)
                concatenated_string += str(value) + " " # Ensure it's a string

        except KeyError:
            print(f"Error: Key '{key_path}' not found in JSON data.")
        except TypeError as e: # Handle cases where indexing might be attempted on non-list
            print(f"TypeError accessing key '{key_path}': {e}")


    output_data = {new_key_name: concatenated_string} # rstrip to remove trailing newline
    return output_data

def write_json_file(data, output_file_path):
    """
    Writes JSON data to a file.

    Args:
        data (dict): The JSON data to write.
        output_file_path (str): The path to the output JSON file.
    """
    try:
        with open(output_file_path, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        print(f"Successfully wrote data to '{output_file_path}'")
    except Exception as e:
        print(f"Error writing to '{output_file_path}': {e}")

def create_course_dataframe(json_data):
    """
    Creates a DataFrame from the provided JSON data, structured as requested.

    Args:
        json_data (dict): The JSON data containing course information.

    Returns:
        pandas.DataFrame: A DataFrame representing the course schema.
    """

    # Extract relevant data sections (with defaults for safety)
    learning_units = json_data["TSC and Topics"].get("Learning Units", [])
    learning_outcomes = json_data["Learning Outcomes"].get("Learning Outcomes", [])
    knowledge_statements = json_data["Learning Outcomes"].get("Knowledge", [])
    ability_statements = json_data["Learning Outcomes"].get("Ability", [])
    course_outline = json_data["Assessment Methods"].get("Course Outline", {}).get("Learning Units", {})
    tsc_code = json_data["TSC and Topics"].get("TSC Code", ["N/A"])[0]
    assessment_methods = json_data["Assessment Methods"].get("Assessment Methods", [])

    # Initialize lists to hold the data for each row in the DataFrame
    data = []
    # Dictionary to track topics already processed for each LU
    processed_topics = {}

    # Iterate through Learning Units (LU)
    for lu_index, lu_title in enumerate(learning_units):
        lu_num = f"LU{lu_index + 1}"  # LU1, LU2, etc.
        # Extract title after "LUx: " and REMOVE any KA references in parentheses
        lu_title_full = lu_title.split(": ", 1)[1] if ": " in lu_title else lu_title
        lu_title_only = lu_title_full.split(" (")[0] if " (" in lu_title_full else lu_title_full

        # Get Learning Outcome (LO) for the current LU
        lo_title = learning_outcomes[lu_index] if lu_index < len(learning_outcomes) else "N/A"
        lo_num = f"LO{lu_index + 1}"
        lo_title_only = lo_title.split(": ", 1)[1] if lo_title != "N/A" and ": " in lo_title else "N/A" # Extract title after "LOx: "

        # Get Topics for the current LU from Course Outline
        lu_num = f"LU{lu_index + 1}"
        processed_topics[lu_num] = {}
        
        # Look for the matching LU in course_outline by either exact match or start-with match
        matching_lu_key = None
        for lu_key in course_outline:
            # Check if the key is exactly lu_num or starts with lu_num followed by ':'
            if lu_key == lu_num or lu_key.startswith(f"{lu_num}:"):
                matching_lu_key = lu_key
                break
                
        if matching_lu_key and matching_lu_key in course_outline:
            topics = course_outline[matching_lu_key].get("Description", [])
            
            for topic in topics:
                topic_title_full = topic.get("Topic", "N/A")
                topic_num = topic_title_full.split(":")[0].replace("Topic ", "T") # "Topic 1" -> "T1"
                topic_title = topic_title_full.split(': ', 1)[1] if ": " in topic_title_full else topic_title_full  # Get the title only, after the first ': '
                topic_title_short = topic_title.split(' (')[0] if " (" in topic_title else topic_title  # extract the topic title without KA

                # Create a unique identifier for this topic in this LU
                topic_key = f"{topic_num}: {topic_title_short}"
                
                # Extract K and A statements from the topic title
                ka_codes_str = topic_title_full.split('(')[-1].rstrip(')') if "(" in topic_title_full else ""
                # Extract just the codes, not the full descriptions
                ka_codes = []
                if ka_codes_str:
                    # Handle both simple codes "K1, A2" and complex formats "K1: description"
                    parts = [part.strip() for part in ka_codes_str.split(',')]
                    for part in parts:
                        if ':' in part:
                            # If it contains a colon, extract just the code before it (e.g. "K1: desc" -> "K1")
                            code = part.split(':', 1)[0].strip()
                        else:
                            code = part.strip()
                        if code.startswith('K') or code.startswith('A'):
                            ka_codes.append(code)

                # Group K and A statements for the same topic
                k_statements = []
                a_statements = []
                
                for code in ka_codes:
                    if code.startswith('K'):
                        try:
                            k_index = int(code[1:]) - 1
                            k_statement = f"{knowledge_statements[k_index]} ({tsc_code})" if 0 <= k_index < len(knowledge_statements) else f"{code}: N/A ({tsc_code})"
                            k_statements.append(k_statement)
                        except ValueError:
                            # Skip this code if we can't parse the index
                            print(f"Warning: Could not parse knowledge index from code: {code}")
                    elif code.startswith('A'):
                        try:
                            a_index = int(code[1:]) - 1
                            a_statement = f"{ability_statements[a_index]} ({tsc_code})" if 0 <= a_index < len(ability_statements) else f"{code}: N/A ({tsc_code})"
                            a_statements.append(a_statement)
                        except ValueError:
                            # Skip this code if we can't parse the index
                            print(f"Warning: Could not parse ability index from code: {code}")
                
                # Determine assessment methods
                if "Oral Questioning" in assessment_methods:
                    moa_k = "Oral Questioning"
                else:
                    moa_k = "Written Exam"
                    
                if "Case Study" in assessment_methods:
                    moa_a = "Others: [Please elaborate]"
                elif "Role Play" in assessment_methods:
                    moa_a = "Role Play"
                else:
                    moa_a = "Practical Exam"
                
                # Add K statements row
                if k_statements:
                    if topic_key not in processed_topics[lu_num]:
                        processed_topics[lu_num][topic_key] = {'k': k_statements, 'a': []}
                    else:
                        processed_topics[lu_num][topic_key]['k'].extend(k_statements)
                
                # Add A statements row
                if a_statements:
                    if topic_key not in processed_topics[lu_num]:
                        processed_topics[lu_num][topic_key] = {'k': [], 'a': a_statements}
                    else:
                        processed_topics[lu_num][topic_key]['a'].extend(a_statements)

            # Now create rows from the processed data
            for topic_key, statements in processed_topics[lu_num].items():
                # Add K statements row
                if statements['k']:
                    # Join all K statements with newlines
                    k_combined = "\n".join(statements['k'])
                    data.append([
                        lu_num,
                        lu_title_only,
                        lo_num,
                        lo_title_only,
                        topic_key,
                        k_combined,
                        moa_k
                    ])
                
                # Add A statements row
                if statements['a']:
                    # Join all A statements with newlines
                    a_combined = "\n".join(statements['a'])
                    data.append([
                        lu_num,
                        lu_title_only,
                        lo_num,
                        lo_title_only,
                        topic_key,
                        a_combined,
                        moa_a
                    ])

    # Create the DataFrame
    df = pd.DataFrame(data, columns=[
        "LU#",
        "Learning Unit Title",
        "LO#",
        "Learning Outcome",
        "Topic (T#: Topic title)",
        "Applicable K&A Statement",
        "Mode of Assessment"
    ])

    # Post-process Mode of Assessment for unknown/other methods
    DROPDOWN_OPTIONS = [
        "Written Exam",
        "Online Test",
        "Project",
        "Assignments",
        "Oral Interview",
        "Demonstration",
        "Practical Exam",
        "Role Play",
        "Oral Questioning",
        "Others: [Please elaborate]"
    ]
    def robust_mode_of_assessment(x):
        if x == "Others: [Please elaborate]":
            # If Case Study present, prefer that
            if "Case Study" in assessment_methods:
                return "Others: Case Study"
            # Otherwise, find the first method not in the dropdown
            for method in assessment_methods:
                if method not in DROPDOWN_OPTIONS and method != "Case Study":
                    return f"Others: {method}"
        return x
    if "Mode of Assessment" in df.columns:
        df["Mode of Assessment"] = df["Mode of Assessment"].apply(robust_mode_of_assessment)

    return clean_tsc_code_and_assessment_methods(df)

def combine_los_and_topics(ensemble_output):
    """
    Combines all Learning Outcomes (LOs) and Topics from the ensemble_output into a formatted string
    with Learning Outcomes section followed by Course Outline section organized by Learning Units.

    Args:
        ensemble_output (dict): The ensemble output JSON data.

    Returns:
        str: A string containing the combined LOs and Topics in the specified format.
    """

    # Start with Learning Outcomes header
    result = "Learning Outcomes\n"
    
    # Extract Learning Outcomes
    learning_outcomes = ensemble_output["Learning Outcomes"]["Learning Outcomes"]
    result += "\n".join(learning_outcomes) + "\n\n"
    
    # Add Course Outline header
    result += "Course Outline:\n"
    
    # Extract Learning Units
    learning_units = ensemble_output["TSC and Topics"].get("Learning Units", [])
    
    # Get the topics for each Learning Unit from the Course Outline
    course_outline = ensemble_output["Assessment Methods"]["Course Outline"]["Learning Units"]
    
    # Process each Learning Unit
    for lu_index, lu_title in enumerate(learning_units):
        lu_num = f"LU{lu_index + 1}"
        
        # Extract the title after "LUx: "
        lu_title_clean = lu_title.split(": ", 1)[1] if ": " in lu_title else lu_title
        # Remove any KA references in parentheses
        lu_title_clean = lu_title_clean.split(" (")[0] if " (" in lu_title_clean else lu_title_clean
        
        # Add the Learning Unit header
        result += f"{lu_num}: {lu_title_clean} \n"
        result += "Topics:\n"
        
        # Look for the matching LU in course_outline by either exact match or start-with match
        matching_lu_key = None
        for lu_key in course_outline:
            # Check if the key is exactly lu_num or starts with lu_num followed by ':'
            if lu_key == lu_num or lu_key.startswith(f"{lu_num}:"):
                matching_lu_key = lu_key
                break
        
        # Get topics for this Learning Unit using the matching key
        if matching_lu_key and matching_lu_key in course_outline:
            topics = course_outline[matching_lu_key].get("Description", [])
            
            for topic in topics:
                topic_title = topic.get("Topic", "")
                
                # Extract topic number (e.g., "Topic 1" -> "T1")
                topic_num = topic_title.split("Topic ")[1].split(":")[0] if "Topic " in topic_title else ""
                
                # Extract topic name without the KA references
                topic_name = topic_title.split(': ', 1)[1] if ": " in topic_title else topic_title
                topic_name = topic_name.split(' (')[0] if " (" in topic_name else topic_name
                
                # Add the topic without KA references
                result += f"•\tT{topic_num}: {topic_name} \n"
        
        result += "\n"
    
    return result

def create_assessment_dataframe(json_data):
    """
    Creates a DataFrame for assessment output based on the provided JSON data,
    with assessment durations distributed equally among all K and A factors.

    Args:
        json_data (dict): The JSON data containing course information.

    Returns:
        pandas.DataFrame: A DataFrame representing the assessment schema with integer duration.
    """

    # --- Assessment Duration Logic ---
    assessment_methods_list = json_data["Assessment Methods"].get("Assessment Methods", [])

    assessment_method_abbreviations = {
        "Written Exam": "WE",
        "Online Test": "OT",
        "Project": "P",
        "Assignments": "A",
        "Oral Interview": "OI",
        "Demonstration": "D",
        "Practical Exam": "PE",
        "Role Play": "RP",
        "Oral Questioning": "OQ",
        "Written Assessment": "WA-SAQ",
        "Practical Performance": "PP",
        "Case Study": "CS"
    }

    normalized_assessment_methods = [assessment_method_abbreviations.get(method, method) for method in assessment_methods_list]

    assessment_method_names = {
        "WE": "Written Exam",
        "OT": "Online Test", 
        "P": "Project",
        "A": "Assignments",
        "OI": "Oral Interview",
        "D": "Demonstration",
        "PE": "Practical Exam",
        "RP": "Role Play",
        "OQ": "Oral Questioning",
        "WA-SAQ": "Written Exam", # Maps to Written Exam in output
        "PP": "Practical Exam",   # Maps to Practical Exam in output
        "CS": "Others: [Please elaborate]",
        "Written Assessment - Short-Answer Questions (WA-SAQ) - Individual, Summative, Open book": "Written Assessment - Short-Answer Questions"
    }

    # Get total assessment duration from Course Information
    num_assessment_hours = json_data["Course Information"].get("Number of Assessment Hours", 0)
    total_assessment_minutes = num_assessment_hours * 60
    print(f"Total assessment minutes from ensemble output: {total_assessment_minutes}")
    
    # Ensure this is a reasonable value (at least 30 minutes if not specified)
    if total_assessment_minutes < 30:
        print("Warning: Assessment hours too low or missing, defaulting to minimum of 30 minutes")
        total_assessment_minutes = 30

    # --- Count total number of KA statements ---
    learning_outcomes_list = json_data["Learning Outcomes"].get("Learning Outcomes", [])
    knowledge_statements = json_data["Learning Outcomes"].get("Knowledge", [])
    ability_statements = json_data["Learning Outcomes"].get("Ability", [])
    tsc_code = json_data["TSC and Topics"].get("TSC Code", ["N/A"])[0]
    assessment_methods = json_data["Assessment Methods"].get("Assessment Methods", [])
    
    # Get K and A factors for each LO
    ka_mapping = json_data["Learning Outcomes"].get("Knowledge and Ability Mapping", {})
    
    # Count total KA statements
    total_ka_statements = 0
    ka_statements_list = []
    
    for lo_index, _ in enumerate(learning_outcomes_list):
        ka_key = f"KA{lo_index + 1}"
        if ka_key in ka_mapping:
            ka_values = ka_mapping[ka_key]
            total_ka_statements += len(ka_values)
            for code in ka_values:
                ka_statements_list.append((lo_index, code))
    
    # Ensure we have at least one KA statement
    if total_ka_statements == 0:
        print("Warning: No KA statements found. Creating a placeholder.")
        total_ka_statements = 1
        ka_statements_list = [(0, "K1")]
    
    print(f"Total KA statements: {total_ka_statements}")
    
    # --- Calculate duration per KA statement ---
    # Divide total assessment minutes evenly between all KA statements
    # and ensure each duration is a multiple of 5
    base_duration = total_assessment_minutes // total_ka_statements
    
    # Round base duration to nearest multiple of 5 (floor)
    base_duration = (base_duration // 5) * 5
    
    # Ensure minimum duration of 5 minutes per assessment
    if base_duration < 5:
        base_duration = 5
    
    # Calculate total allocated and remaining minutes
    total_allocated = base_duration * total_ka_statements
    remaining_minutes = total_assessment_minutes - total_allocated
    
    print(f"Base duration per KA statement: {base_duration} minutes")
    print(f"Remaining minutes to distribute: {remaining_minutes} minutes")
    
    # Create list of durations for each KA statement
    durations = [base_duration] * total_ka_statements
    
    # Distribute remaining minutes (if any) in increments of 5
    while remaining_minutes >= 5:
        # Try to distribute evenly
        increment = min(5, remaining_minutes)
        statements_to_increment = min(total_ka_statements, remaining_minutes // increment)
        
        for i in range(statements_to_increment):
            durations[i] += increment
            remaining_minutes -= increment
            
        # If we've allocated to all statements but still have minutes left,
        # start over from the beginning
        if statements_to_increment == total_ka_statements and remaining_minutes >= 5:
            continue
            
        # If we can't distribute evenly anymore, break
        if statements_to_increment == 0 or remaining_minutes < 5:
            break
    
    # If there are still remaining minutes, add them to the first assessment
    if remaining_minutes > 0 and total_ka_statements > 0:
        durations[0] += remaining_minutes
    
    # --- Create DataFrame ---
    data = []
    
    for idx, (lo_index, code) in enumerate(ka_statements_list):
        lo_num = f"LO{lo_index + 1}"
        duration_minutes = durations[idx] if idx < len(durations) else base_duration
        
        if code.startswith('K'):
            k_index = int(code[1:]) - 1
            k_statement = f"{knowledge_statements[k_index]} ({tsc_code})" if 0 <= k_index < len(knowledge_statements) else f"{code}: N/A ({tsc_code})"
            
            # For K factors: Use Oral Questioning if available, otherwise use Written Exam
            if "Oral Questioning" in assessment_methods:
                moa = "Oral Questioning"
            else:
                moa = "Written Exam"
            
            data.append([
                lo_num,
                moa,
                duration_minutes,
                1,
                20,
                k_statement
            ])
            
        elif code.startswith('A'):
            a_index = int(code[1:]) - 1
            a_statement = f"{ability_statements[a_index]} ({tsc_code})" if 0 <= a_index < len(ability_statements) else f"{code}: N/A ({tsc_code})"
            
            # For A factors: Prioritize in this order: Role Play, Case Study, Practical Exam
            if "Role Play" in assessment_methods:
                moa = "Role Play"
            elif "Case Study" in assessment_methods:
                moa = "Others: [Please elaborate]"
            else:
                moa = "Practical Exam"
            
            data.append([
                lo_num,
                moa,
                duration_minutes,
                1,
                20,
                a_statement
            ])
    
    df = pd.DataFrame(data, columns=[
        "LO#",
        "MOA",
        "Assessment Duration",
        "Assessors",
        "Candidates",
        "KA"
    ])
    
    # Robust post-processing for Mode of Assessment (MOA)
    DROPDOWN_OPTIONS = [
        "Written Exam",
        "Online Test",
        "Project",
        "Assignments",
        "Oral Interview",
        "Demonstration",
        "Practical Exam",
        "Role Play",
        "Oral Questioning",
        "Others: [Please elaborate]"
    ]
    def robust_mode_of_assessment(x):
        if x == "Others: [Please elaborate]":
            # If Case Study present, prefer that
            if "Case Study" in assessment_methods:
                return "Others: Case Study"
            # Otherwise, find the first method not in the dropdown
            for method in assessment_methods:
                if method not in DROPDOWN_OPTIONS and method != "Case Study":
                    return f"Others: {method}"
        return x
    if "MOA" in df.columns:
        df["MOA"] = df["MOA"].apply(robust_mode_of_assessment)
    
    return clean_tsc_code_and_assessment_methods(df)

def enrich_assessment_dataframe_ka_descriptions(df, excel_data_json_path):
    """
    Enriches the 'KA' column of an assessment DataFrame with descriptions from excel_data.json.

    Args:
        df (pd.DataFrame): The assessment DataFrame created by create_assessment_dataframe.
        excel_data_json_path (str): Path to the excel_data.json file.

    Returns:
        pd.DataFrame: The DataFrame with enriched 'KA' column values.
    """
    try:
        with open(excel_data_json_path, 'r', encoding='utf-8') as f:
            excel_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: excel_data.json file not found at: {excel_data_json_path}")
        return df  # Return original DataFrame if JSON not found

    ka_analysis_data = excel_data[1].get("KA_Analysis", {}) # Access KA_Analysis data

    enriched_ka_values = []
    for index, row in df.iterrows():
        ka_value = row['KA']
        ka_code_match = re.match(r'([KA]\d+):', ka_value) # Regex to extract KA code (e.g., K1, A2)

        if ka_code_match:
            ka_code = ka_code_match.group(1)
            ka_description = ka_analysis_data.get(ka_code, "Description not found") # Get description from JSON
            enriched_ka_value = f"{ka_description}\n{ka_value}" # Combine description and original KA value
        else:
            enriched_ka_value = ka_value # If KA code not found, keep original value

        enriched_ka_values.append(enriched_ka_value)

    df['KA'] = enriched_ka_values # Update the KA column with enriched values
    return df

def format_sequencing_rationale(rationale: str) -> str:
    """
    Ensures the sequencing rationale starts with the required phrase or a reasonable variant.
    If not, prepends a generic multi-sentence rationale and the required intro.
    Handles edge cases: if rationale is empty, or starts with LU1, or is missing the intro, etc.
    """
    rationale = (rationale or '').strip()
    # Flexible regex: matches 'For this course, the step[- ]?by[- ]?step sequencing helps' or 'For this course, the step-by-step sequencing helps', case-insensitive
    intro_pattern = re.compile(r"^for this course, the step[- ]?by[- ]?step sequencing helps", re.IGNORECASE)
    lu_pattern = re.compile(r"^lu\s*1[:\.]", re.IGNORECASE)
    required_intro = "For this course, the step-by-step sequencing helps learners build from foundational concepts to advanced applications in the subject area."
    generic_rationale = (
        "This framework begins with foundational principles, ensuring learners acquire essential knowledge and skills before progressing to more advanced topics and applications. "
        "Each learning unit is carefully sequenced to build on the previous one, supporting mastery at every stage and enabling real-world application. "
        "This structure ensures alignment with the course's learning outcomes and supports a comprehensive, logical progression from basic to advanced competencies."
    )
    if not rationale:
        return f"{required_intro}\n\n{generic_rationale}"
    if intro_pattern.match(rationale):
        return rationale
    if lu_pattern.match(rationale):
        return f"{required_intro}\n\n{generic_rationale}\n\n{rationale}"
    # If rationale is a short phrase or doesn't start with intro or LU1, prepend intro and rationale
    return f"{required_intro}\n\n{generic_rationale}\n\n{rationale}"

# main function for this script
def map_new_key_names_excel(generated_mapping_path, generated_mapping, output_json_file, excel_data_path, ensemble_output):
    # generated_mapping_path = os.path.join('..', 'json_output', 'generated_mapping.json')
    # generated_mapping = load_json_file(generated_mapping_path)

    # output_json_file = os.path.join('..', 'json_output', 'generated_mapping.json')
    # excel_data_path = os.path.join('..', 'json_output', 'excel_data.json')

    # generated_mapping_path = "CourseProposal/json_output/generated_mapping.json"
    # generated_mapping = load_json_file(generated_mapping_path)

    # output_json_file = "CourseProposal/json_output/generated_mapping.json"
    # excel_data_path = "CourseProposal/json_output/excel_data.json"
    excel_data = load_json_file(excel_data_path)

    # **Load existing JSON file first**
    existing_data = load_json_file(output_json_file) # Load existing data, returns {} if file not found or invalid JSON

    if existing_data is None: # Error loading existing data
        print("Failed to load existing output JSON, cannot append. Exiting.")
        return

    # sequencing rationale
    sequencing_keys = ["#Rationale[0]", "#Sequencing", "#Conclusion[0]"]
    sequencing_rationale_data = extract_and_concatenate_json_values(generated_mapping, sequencing_keys, "#Sequencing_rationale")
    # Format the sequencing rationale for Excel (backwards compatible)
    if sequencing_rationale_data and sequencing_rationale_data.get("#Sequencing_rationale"):
        sequencing_rationale_data["#Sequencing_rationale"] = format_sequencing_rationale(sequencing_rationale_data["#Sequencing_rationale"])

    # tcs code combined with skill name
    tcs_keys = ["#TCS[1]", "#TCS[0]"]
    tcs_code_skill_data = extract_and_concatenate_json_values_space_seperator(generated_mapping, tcs_keys, "#TCS_Code_Skill")

    combined_lo = ["#LO[0]", "#LO[1]", "#LO[2]", "#LO[3]", "#LO[4]", "#LO[5]", "#LO[6]", "#LO[7]"]
    lo_data = extract_and_concatenate_json_values_singlenewline(generated_mapping, combined_lo, "#Combined_LO")

    course_background = extract_and_concatenate_json_values(
        excel_data[0]["course_overview"],
        ["course_description"],
        "#Course_Background1",
    )

    print(f"COURSE BACKGROUND:{course_background}" )

    # include declarations mapping, standard Not Applicable, and We Agree (do this in the excel template bah)
    # improve formatting of sequencing rationale
    # course type should be WSQ Course Accreditation Singular (as the standard)
    # course outline should be all the LOs on top first, then the topics (without the A and K factors)
    # course_outline_keys = recursive_get_keys(generated_mapping, "#Topics[")
    # print(course_outline_keys)
    # course_outline = extract_and_concatenate_json_values(generated_mapping, course_outline_keys, "#Course_Outline")

    course_outline = combine_los_and_topics(ensemble_output)
    # Wrap the course_outline string in a dictionary
    course_outline_data = {"#Course_Outline": course_outline}

    # --- ADD COURSE LEVEL TO OUTPUT ---
    # Try to get course level from ensemble_output, fallback to excel_data if needed
    course_level = None
    if "Course Information" in ensemble_output and "Course Level" in ensemble_output["Course Information"]:
        course_level = ensemble_output["Course Information"]["Course Level"]
    elif "Course Information" in excel_data[0] and "Course Level" in excel_data[0]["Course Information"]:
        course_level = excel_data[0]["Course Information"]["Course Level"]
    # Add to output if found
    if course_level:
        existing_data["Course Level"] = course_level

    if sequencing_rationale_data and tcs_code_skill_data: # Check if both data extractions were successful
        # **Update the existing data dictionary**
        existing_data.update(sequencing_rationale_data)
        existing_data.update(tcs_code_skill_data)
        existing_data.update(lo_data)
        existing_data.update(course_outline_data)
        existing_data.update(course_background)

        # **Write the updated dictionary back to the output file**
        write_json_file(existing_data, output_json_file)
    else:
        print("Error during data extraction, not writing to output file.")

def create_instructional_dataframe(json_data):
    """
    Creates a DataFrame for instructional methods and durations, ensuring total duration
    matches "Course Duration" - "Assessment Hours" and all durations are in multiples of 5.
    Treats all instructional methods equally with no special handling for practical hours.

    Args:
        json_data (dict): The JSON data containing course information.

    Returns:
        pandas.DataFrame: A DataFrame representing the instructional schema with durations in multiples of 5.
    """

    course_info = json_data["Course Information"]
    learning_units = json_data["TSC and Topics"]["Learning Units"]
    instructional_methods_input = json_data["Assessment Methods"]["Instructional Methods"]
    ka_mapping = json_data["Learning Outcomes"].get("Knowledge and Ability Mapping", {})
    
    # We'll use the total instructional time from course duration minus assessment hours
    assessment_hours = course_info.get("Number of Assessment Hours", 0)
    course_duration_hours = course_info.get("Course Duration (Number of Hours)", 0)

    # Calculate total instructional hours
    total_instructional_hours = course_duration_hours - assessment_hours
    total_instructional_minutes = total_instructional_hours * 60
    
    # Round to nearest multiple of 5
    total_instructional_minutes = round(total_instructional_minutes / 5) * 5

    if isinstance(instructional_methods_input, str):
        instructional_methods_list = [method.strip() for method in instructional_methods_input.split(',')]
    elif isinstance(instructional_methods_input, list):
        instructional_methods_list = [method.strip() for method in instructional_methods_input]
    else:
        print(f"Warning: Unexpected type for 'Instructional Methods': {type(instructional_methods_input)}. Defaulting to empty list.")
        instructional_methods_list = []

    lu_ka_mapping = {}
    for idx in range(len(learning_units)):
        ka_key = f"KA{idx + 1}"
        if ka_key in ka_mapping:
            lu_ka_mapping[f"LU{idx+1}"] = ka_mapping[ka_key]

    data = []
    total_rows = 0

    for lu_index, lu_title in enumerate(learning_units):
        lu_num = f"LU{lu_index + 1}"
        ka_values = lu_ka_mapping.get(lu_num, [])
        k_codes_in_lu = [item for item in ka_values if item.startswith('K')]
        a_codes_in_lu = [item for item in ka_values if item.startswith('A')]

        if k_codes_in_lu and not a_codes_in_lu: # Only K factors
            data.append([lu_num, "Classroom", 0, "Classroom Facilitated Training"]) # Initial duration 0
            total_rows += 1
        elif k_codes_in_lu and a_codes_in_lu or not k_codes_in_lu and a_codes_in_lu: # Both K and A or only A factors
            for method in instructional_methods_list:
                data.append([lu_num, method.strip(), 0, "Classroom Facilitated Training"]) # Initial duration 0
                total_rows += 1

    df = pd.DataFrame(data, columns=["LU#", "Instructional Methods", "Instructional Duration", "MOT"])

    # Calculate duration per row (evenly distributed)
    if total_rows > 0:
        base_duration_per_row = total_instructional_minutes // total_rows
        # Round to multiple of 5
        base_duration_per_row = (base_duration_per_row // 5) * 5
        
        # Calculate remainder to distribute
        remaining_minutes = total_instructional_minutes - (base_duration_per_row * total_rows)
        
        # Assign base duration to all rows
        df["Instructional Duration"] = base_duration_per_row
        
        # Distribute remaining minutes in increments of 5
        remaining_to_distribute = remaining_minutes
        row_index = 0
        
        while remaining_to_distribute >= 5 and row_index < len(df):
            df.loc[row_index, "Instructional Duration"] += 5
            remaining_to_distribute -= 5
            row_index += 1
    
    # Final verification
    total_actual_minutes = df["Instructional Duration"].sum()
    
    # If there's a discrepancy with total instructional minutes, make adjustments
    if total_actual_minutes != total_instructional_minutes:
        diff = total_instructional_minutes - total_actual_minutes
        print(f"Final adjustment of {diff} minutes needed to match total instructional time")
        
        # Only apply adjustment if it's small (less than 5 minutes per row)
        if abs(diff) <= len(df) * 5:
            # Distribute the difference as evenly as possible
            indices = df.index.tolist()
            remaining_diff = diff
            
            # Sort by duration (largest first for subtraction, smallest first for addition)
            if diff < 0:
                indices = sorted(indices, 
                               key=lambda idx: df.loc[idx, "Instructional Duration"],
                               reverse=True)
            else:
                indices = sorted(indices, 
                               key=lambda idx: df.loc[idx, "Instructional Duration"])
                
            # Apply adjustment in multiples of 5
            adjustment_per_row = 5 if diff > 0 else -5
            for idx in indices:
                if abs(remaining_diff) >= 5 and (df.loc[idx, "Instructional Duration"] + adjustment_per_row) >= 0:
                    df.loc[idx, "Instructional Duration"] += adjustment_per_row
                    remaining_diff -= adjustment_per_row
                if abs(remaining_diff) < 5:
                    break
        
    # Final verification
    print(f"Final total instructional duration: {df['Instructional Duration'].sum()} minutes")
    
    # Check if all durations are multiples of 5
    all_multiples_of_5 = all(duration % 5 == 0 for duration in df["Instructional Duration"])
    print(f"All durations are multiples of 5: {all_multiples_of_5}")

    if "Instructional Methods" in df.columns:
        df["Instructional Methods"] = df["Instructional Methods"].apply(map_instructional_method)
    return clean_tsc_code_and_assessment_methods(df)

def create_instruction_description_dataframe(ensemble_json_path, im_agent_json_path):
    """
    Creates a DataFrame mapping instructional methods to their descriptions from im_agent_data.json.

    Args:
        ensemble_json_path (str): Path to the ensemble_output.json file.
        im_agent_json_path (str): Path to the im_agent_data.json file.

    Returns:
        pandas.DataFrame: A DataFrame with "Instructional Method" and "Description" columns.
                         Returns an empty DataFrame if there's an error loading the JSON files.
    """
    try:
        with open(ensemble_json_path, 'r', encoding='utf-8') as f_ensemble:
            ensemble_data = json.load(f_ensemble)
        with open(im_agent_json_path, 'r', encoding='utf-8') as f_im_agent:
            im_agent_data = json.load(f_im_agent)
    except FileNotFoundError as e:
        print(f"Error: One or both JSON files not found. {e}")
        return pd.DataFrame()  # Return empty DataFrame in case of file error
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in one of the files. {e}")
        return pd.DataFrame()  # Return empty DataFrame for invalid JSON

    instructional_methods_input = ensemble_data.get("Assessment Methods", {}).get("Instructional Methods", [])

    if isinstance(instructional_methods_input, str):
        instructional_methods_list = [method.strip() for method in instructional_methods_input.split(',')]
    elif isinstance(instructional_methods_input, list):
        instructional_methods_list = [method.strip() for method in instructional_methods_input]
    else:
        print(f"Warning: Unexpected type for 'Instructional Methods' in ensemble_output.json: {type(instructional_methods_input)}. Defaulting to empty list.")
        instructional_methods_list = []

    # Extract method descriptions from im_agent_data.json structure
    methods_description_map = {}
    instructional_methods_data = im_agent_data.get("Instructional_Methods", {})
    
    # Process each method entry in the Instructional_Methods dictionary
    for method_name, description in instructional_methods_data.items():
        if description:
            methods_description_map[method_name] = description

    data = []
    for method in instructional_methods_list:
        # Extract the base method name without duration (e.g., "Classroom: 7 hrs" -> "Classroom")
        base_method = method.split(":")[0].strip()
        
        # Look for the most closely matching key in methods_description_map
        matching_key = None
        for key in methods_description_map.keys():
            if key.lower() in base_method.lower() or base_method.lower() in key.lower():
                matching_key = key
                break
        
        # If no match found, check if the exact method exists
        if matching_key is None and base_method in methods_description_map:
            matching_key = base_method
        
        # Get description for the method
        description = methods_description_map.get(matching_key, "Description not found.")
        
        data.append([method, description])

    df = pd.DataFrame(data, columns=["Instructional Method", "Description"])
    if "Instructional Method" in df.columns:
        df["Instructional Method"] = df["Instructional Method"].apply(map_instructional_method)
    return df


def create_summary_dataframe(course_df, instructional_df, assessment_df):
    """
    Derives a summary dataframe from supporting dataframes:
      - course_df: contains LU, LO, topics, and applicable K&A statements
      - instructional_df: contains instructional methods, their durations, and mode of training (MOT)
      - assessment_df: contains assessment modes, duration, assessor-to-candidate info, and LO#
      
    Returns a dataframe with the following columns:
      LU#, Learning Unit Title, Learning Outcome(s), Topic(s),
      Instructional Methods (modes of training, duration in minutes),
      Instructional Duration (in minutes),
      Modes of Assessment (Assessor-to-candidate Ratio, duration in minutes),
      Assessment Duration (in minutes)
    """
    
    # --- Process Course DataFrame ---
    def extract_codes(statements_series):
        """
        Given a series of "Applicable K&A Statement" strings,
        extract and return a list of KA codes (e.g., A1, K1) in order of appearance.
        """
        codes = []
        for text in statements_series:
            m = re.match(r"^(A\d+|K\d+):", text.strip()) if isinstance(text, str) else None
            if m:
                codes.append(m.group(1))
        # Deduplicate while preserving order.
        seen = set()
        codes_unique = []
        for code in codes:
            if code not in seen:
                codes_unique.append(code)
                seen.add(code)
        return codes_unique

    # Group by LU# and aggregate relevant fields.
    course_agg = course_df.groupby("LU#").agg({
        "Learning Unit Title": "first",
        "LO#": "first",  # Assuming all rows for a given LU share the same LO#
        "Learning Outcome": "first",
        "Topic (T#: Topic title)": lambda x: "\n".join(["- " + str(item) for item in x]),
        "Applicable K&A Statement": lambda x: extract_codes(x)
    }).reset_index()

    # Create the formatted Learning Outcome(s) column.
    course_agg["Learning Outcome(s)"] = course_agg.apply(
        lambda row: f"{row['LO#']}: {row['Learning Outcome']} ({', '.join(list(row['Applicable K&A Statement']) if isinstance(row['Applicable K&A Statement'], (list, tuple)) else [str(row['Applicable K&A Statement'])])})",
        axis=1
    )
    # Rename topics column to "Topic(s)" for clarity.
    course_agg.rename(columns={"Topic (T#: Topic title)": "Topic(s)"}, inplace=True)

    # --- Process Instructional Methods DataFrame ---
    # For each LU, concatenate each instructional method row into a string and sum durations.
    instr_agg = instructional_df.groupby("LU#").apply(lambda g: pd.Series({
        "Instructional Methods (modes of training, duration in minutes)":
            "\n".join([f"- {row['Instructional Methods']} ({row['MOT']}: {row['Instructional Duration']})"
                       for _, row in g.iterrows()]),
        "Instructional Duration (in minutes)": g["Instructional Duration"].sum()
    })).reset_index()

    # --- Process Assessment DataFrame ---
    # Normalize the LU# key using regex so that, for example, "LO04" becomes "LU4"
    assessment_df = assessment_df.copy()
    # Ensure LO# column exists and has string values
    if "LO#" not in assessment_df.columns:
        print("Warning: LO# column missing from assessment dataframe. Adding default column.")
        assessment_df["LO#"] = "LO1"
    
    assessment_df["LU#"] = assessment_df["LO#"].apply(
        lambda x: re.sub(r'^LO0*', 'LU', x) if isinstance(x, str) else f"LU{x}" if isinstance(x, int) else "LU1"
    )

    def agg_assessment(g):
        """
        For each group (LU), create a string of assessment modes.
        Each line is formatted as: "- MOA (Assessors:Candidates, Assessment Duration)"
        """
        lines = []
        for _, row in g.iterrows():
            ratio = f"{row['Assessors']}:{row['Candidates']}"
            duration = row["Assessment Duration"]
            lines.append(f"- {row['MOA']} ({ratio}, {duration})")
        return "\n".join(lines) if lines else "- No assessment methods specified"

    # Check if assessment dataframe has data
    if assessment_df.empty:
        print("Warning: Assessment dataframe is empty. Using placeholder data.")
        # Create dummy assessment aggregation with zeros
        assess_agg = pd.DataFrame({
            "LU#": course_agg["LU#"].unique(),
            "Modes of Assessment (Assessor-to-candidate Ratio, duration in minutes)": "- No assessment methods specified",
            "Assessment Duration (in minutes)": 0
        })
    else:
        assess_agg = assessment_df.groupby("LU#").apply(lambda g: pd.Series({
            "Modes of Assessment (Assessor-to-candidate Ratio, duration in minutes)": agg_assessment(g),
            "Assessment Duration (in minutes)": g["Assessment Duration"].sum()
        })).reset_index()

    # --- Merge Aggregated Data ---
    # First merge course and instructional data
    summary_df = course_agg[["LU#", "Learning Unit Title", "Learning Outcome(s)", "Topic(s)"]].merge(
        instr_agg, on="LU#", how="left"
    )
    
    # Handle nulls in instructional data
    summary_df["Instructional Methods (modes of training, duration in minutes)"] = summary_df["Instructional Methods (modes of training, duration in minutes)"].fillna(
        "- No instructional methods specified")
    summary_df["Instructional Duration (in minutes)"] = summary_df["Instructional Duration (in minutes)"].fillna(0)
    
    # Now merge assessment data
    summary_df = summary_df.merge(
        assess_agg, on="LU#", how="left"
    )
    
    # Handle nulls in assessment data
    summary_df["Modes of Assessment (Assessor-to-candidate Ratio, duration in minutes)"] = summary_df["Modes of Assessment (Assessor-to-candidate Ratio, duration in minutes)"].fillna(
        "- No assessment methods specified")
    summary_df["Assessment Duration (in minutes)"] = summary_df["Assessment Duration (in minutes)"].fillna(0)
    
    # Convert duration columns to integers
    summary_df["Instructional Duration (in minutes)"] = summary_df["Instructional Duration (in minutes)"].astype(int)
    summary_df["Assessment Duration (in minutes)"] = summary_df["Assessment Duration (in minutes)"].astype(int)

    # --- Order Columns as Specified ---
    summary_df = summary_df[[
        "LU#",
        "Learning Unit Title",
        "Learning Outcome(s)",
        "Topic(s)",
        "Instructional Methods (modes of training, duration in minutes)",
        "Instructional Duration (in minutes)",
        "Modes of Assessment (Assessor-to-candidate Ratio, duration in minutes)",
        "Assessment Duration (in minutes)"
    ]]
    
    print(f"Summary dataframe created with {len(summary_df)} rows")
    print(f"Total instructional duration: {summary_df['Instructional Duration (in minutes)'].sum()} minutes")
    print(f"Total assessment duration: {summary_df['Assessment Duration (in minutes)'].sum()} minutes")

    return summary_df

INSTRUCTIONAL_METHODS_DROPDOWN = [
    "Brainstorming",
    "Case studies",
    "Concept formation",
    "Debates",
    "Demonstrations / Modelling",
    "Didactic questions",
    "Discussions",
    "Drill and Practice",
    "Experiments",
    "Explicit teaching (Lecture) & Homework",
    "Field trips",
    "Games",
    "Independent reading",
    "Interactive presentation",
    "Peer teaching / Peer practice",
    "Problem solving",
    "Reflection",
    "Role-play",
    "Simulations",
    "Others: [Please elaborate]"
]

# Mapping from raw instructional method names to dropdown values
INSTRUCTIONAL_METHODS_MAPPING = {
    "Peer Sharing": "Peer teaching / Peer practice",
    "Peer sharing": "Peer teaching / Peer practice",
    "Group Discussion": "Discussions",
    "Group discussion": "Discussions",
    "Interactive Presentation": "Interactive presentation",
    "Case Study": "Case studies",
    "Case study": "Case studies",
    # Add more mappings as needed
}

def map_instructional_method(value):
    if not isinstance(value, str):
        return value
    # Use mapping if available
    if value in INSTRUCTIONAL_METHODS_MAPPING:
        return INSTRUCTIONAL_METHODS_MAPPING[value]
    value_clean = value.strip().lower()
    for option in INSTRUCTIONAL_METHODS_DROPDOWN:
        if value_clean == option.strip().lower():
            return option  # Use dropdown value as-is
    # If already in the form 'Others: ...' (but not [Please elaborate]), keep as-is
    if value_clean.startswith("others:") and value_clean != "others: [please elaborate]":
        return f"Others: {value[7:].strip().capitalize()}"
    # Special case: map 'Others: Case Study' or 'Case Study' to 'Case studies' if present
    if value_clean in ["others: case study", "case study", "case studies"]:
        for option in INSTRUCTIONAL_METHODS_DROPDOWN:
            if option.lower() == "case studies":
                return option
    return f"Others: {value.strip()}"

def clean_tsc_code_and_assessment_methods(df):
    """
    Post-processes a DataFrame to:
    1. Remove duplicate TSC codes in the TSC code/skill field (e.g., 'CODE CODE Skill' -> 'CODE Skill').
    2. Map assessment methods to dropdown, or to 'Others: [value]' if not present.
    """
    import re
    # Clean TSC code/skill field
    if 'TSC Code Skill' in df.columns:
        def clean_tsc(val):
            if isinstance(val, str):
                # Remove duplicate code at the start
                match = re.match(r'^(\w+-\w+-\d+\.\d+) \1 (.+)$', val)
                if match:
                    return f"{match.group(1)} {match.group(2)}"
            return val
        df['TSC Code Skill'] = df['TSC Code Skill'].apply(clean_tsc)
    # Clean assessment method field
    if 'Assessment Methods' in df.columns:
        df['Assessment Methods'] = df['Assessment Methods'].apply(map_assessment_method)
    return df

