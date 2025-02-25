import json
import sys
import os
from helpers import load_json_file, extract_lo_keys
import pandas as pd


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
    for key_path in keys_to_extract: # Iterate through keys as they are, NO parsing needed
        try:
            value = json_data.get(key_path) # Use key_path directly as the JSON key

            if value is None:
                print(f"Warning: Key '{key_path}' not found in JSON data.")
                continue # Skip to the next key if not found

            if isinstance(value, list):
                concatenated_string += "\n".join(map(str, value)) + "\n" # Map to str to handle non-string list elements if any
            else: # If value is not a list (e.g., string, number)
                concatenated_string += str(value) + "\n" # Ensure it's a string

        except KeyError:
            print(f"Error: Key '{key_path}' not found in JSON data.")
        except TypeError as e: # Handle cases where indexing might be attempted on non-list
            print(f"TypeError accessing key '{key_path}': {e}")


    output_data = {new_key_name: concatenated_string.rstrip('\n')} # rstrip to remove trailing newline
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

    # Initialize lists to hold the data for each row in the DataFrame
    data = []

    # Iterate through Learning Units (LU)
    for lu_index, lu_title in enumerate(learning_units):
        lu_num = f"LU{lu_index + 1}"  # LU1, LU2, etc.
        lu_title_only = lu_title.split(": ", 1)[1]  # Extract title after "LUx: "

        # Get Learning Outcome (LO) for the current LU
        lo_title = learning_outcomes[lu_index] if lu_index < len(learning_outcomes) else "N/A"
        lo_num = f"LO{lu_index + 1}"
        lo_title_only = lo_title.split(": ", 1)[1] if lo_title != "N/A" else "N/A" # Extract title after "LOx: "

        # Get Topics for the current LU from Course Outline
        lu_key = f"LU{lu_index + 1}"
        if lu_key in course_outline:
            topics = course_outline[lu_key].get("Description", [])
            for topic in topics:
                topic_title_full = topic.get("Topic", "N/A")
                topic_num = topic_title_full.split(":")[0].replace("Topic ", "T") # "Topic 1" -> "T1"
                topic_title = topic_title_full.split(': ', 1)[1]  # Get the title only, after the first ': '
                topic_title_short = topic_title.split(' (')[0]  # extract the topic title without KA

                # Extract K and A statements from the topic title
                ka_codes_str = topic_title_full.split('(')[-1].rstrip(')')  # Everything inside (...)
                ka_codes = [code.strip() for code in ka_codes_str.split(',')]


                # Create rows for EACH K and A statement
                for code in ka_codes:
                    if code.startswith('K'):
                        k_index = int(code[1:]) - 1
                        # Correct K statement formatting:  Remove the duplicate "Kx: " prefix
                        k_statement = f"{knowledge_statements[k_index]} ({tsc_code})" if 0 <= k_index < len(knowledge_statements) else f"{code}: N/A ({tsc_code})"
                        data.append([
                            lu_num,
                            lu_title_only,
                            lo_num,
                            lo_title_only,
                            f"{topic_num}: {topic_title_short}",
                            k_statement,
                            "Written Exam"  # Mode of Assessment for K
                        ])
                    elif code.startswith('A'):
                        a_index = int(code[1:]) - 1
                        # Correct A statement formatting: Remove the duplicate "Ax: " prefix
                        a_statement = f"{ability_statements[a_index]} ({tsc_code})" if 0 <= a_index < len(ability_statements) else f"{code}: N/A ({tsc_code})"
                        data.append([
                            lu_num,
                            lu_title_only,
                            lo_num,
                            lo_title_only,
                            f"{topic_num}: {topic_title_short}",
                            a_statement,
                            "Practical Exam"  # Mode of Assessment for A
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

    return df

def create_assessment_dataframe(json_data):
    """
    Creates a DataFrame for assessment output based on the provided JSON data,
    including assessment duration in minutes as integers.

    Args:
        json_data (dict): The JSON data containing course information.

    Returns:
        pandas.DataFrame: A DataFrame representing the assessment schema with integer duration.
    """

    # --- Assessment Duration Logic (from generate_assessment_output) ---
    assessment_methods_list = json_data["Assessment Methods"].get("Assessment Methods", [])

    assessment_method_abbreviations = {
        "Written Assessment": "WA-SAQ",
        "Practical Performance": "PP",
        "Case Study": "CS",
        "Oral Questioning": "OQ",
        "Role Play": "RP"
    }

    normalized_assessment_methods = [assessment_method_abbreviations.get(method, method) for method in assessment_methods_list]

    assessment_method_names = {
        "WA-SAQ": "Written Exam", # Changed to match desired MOA in dataframe
        "PP": "Practical Exam",    # Changed to match desired MOA in dataframe
        "CS": "Case Study",
        "OQ": "Oral Questioning",
        "Written Assessment - Short-Answer Questions (WA-SAQ) - Individual, Summative, Open book": "Written Assessment - Short-Answer Questions",
        "RP": "Role Play"
    }

    num_assessment_hours = json_data["Course Information"].get("Number of Assessment Hours", 0)
    total_assessment_minutes = num_assessment_hours * 60

    learning_units = json_data["TSC and Topics"]["Learning Units"]
    num_lus = len(learning_units)

    ka_mapping = json_data["Learning Outcomes"].get("Knowledge and Ability Mapping", {})
    lu_ka_mapping = {} # Create LU-based KA mapping
    for idx in range(num_lus):
        ka_key = f"KA{idx + 1}"
        if ka_key in ka_mapping:
            lu_ka_mapping[f"LU{idx+1}"] = ka_mapping[ka_key]

    lu_assessment_methods = {}
    methods_used = set()

    for i, lu in enumerate(learning_units):
        lu_key = f"LU{i+1}"
        lu_data_ka = lu_ka_mapping.get(lu_key, []) # Get KA for LU

        methods_in_lu = []
        k_codes_in_lu = [item for item in lu_data_ka if item.startswith('K')]
        a_codes_in_lu = [item for item in lu_data_ka if item.startswith('A')]

        if k_codes_in_lu:
            if "WA-SAQ" in normalized_assessment_methods: # Check if WA-SAQ is available
                 methods_in_lu.append('WA-SAQ')
            elif "Written Assessment" in assessment_methods_list: # Fallback to full name if abbr. not found
                 methods_in_lu.append('Written Assessment') # Use full name

        if a_codes_in_lu:
            available_methods_for_a = [method for method in ['PP', 'CS', 'OQ', 'RP'] if method in normalized_assessment_methods]
            if available_methods_for_a:
                methods_in_lu.append(available_methods_for_a[0])

        lu_assessment_methods[lu_key] = methods_in_lu
        methods_used.update(methods_in_lu)


    num_methods_used = len(methods_used)
    method_total_duration = total_assessment_minutes // num_methods_used if num_methods_used > 0 else 0

    method_lu_map = {method: [] for method in methods_used}
    for lu_key, methods_in_lu in lu_assessment_methods.items():
        for method in methods_in_lu:
            method_lu_map[method].append(lu_key)

    method_durations_per_lu = {}
    for method, lus in method_lu_map.items():
        num_lus_using_method = len(lus)
        duration_per_lu = method_total_duration // num_lus_using_method if num_lus_using_method > 0 else 0
        for lu_key in lus:
            if lu_key not in method_durations_per_lu:
                method_durations_per_lu[lu_key] = {}
            method_durations_per_lu[lu_key][method] = duration_per_lu

    # --- DataFrame Creation Logic (modified to include duration as integer) ---
    learning_outcomes_list = json_data["Learning Outcomes"].get("Learning Outcomes", [])
    knowledge_statements = json_data["Learning Outcomes"].get("Knowledge", [])
    ability_statements = json_data["Learning Outcomes"].get("Ability", [])
    tsc_code = json_data["TSC and Topics"].get("TSC Code", ["N/A"])[0]

    data = []

    for lo_index, lo_title in enumerate(learning_outcomes_list):
        lo_num = f"LO{lo_index + 1}"
        lu_num = f"LU{lo_index + 1}" # Assuming LO index corresponds to LU index

        ka_key = f"KA{lo_index + 1}"
        if ka_key in ka_mapping:
            ka_values = ka_mapping[ka_key]
            for code in ka_values:
                if code.startswith('K'):
                    k_index = int(code[1:]) - 1
                    k_statement = f"{knowledge_statements[k_index]} ({tsc_code})" if 0 <= k_index < len(knowledge_statements) else f"{code}: N/A ({tsc_code})"
                    moa = "Written Exam"
                    duration_minutes = method_durations_per_lu.get(lu_num, {}).get('WA-SAQ', 0) # Get duration for WA-SAQ for this LU, default 0


                    data.append([
                        lo_num,
                        moa,
                        duration_minutes, # Insert duration in minutes as integer
                        1,
                        20,
                        k_statement
                    ])
                elif code.startswith('A'):
                    a_index = int(code[1:]) - 1
                    a_statement = f"{ability_statements[a_index]} ({tsc_code})" if 0 <= a_index < len(ability_statements) else f"{code}: N/A ({tsc_code})"
                    moa = "Practical Exam"
                    duration_minutes = method_durations_per_lu.get(lu_num, {}).get('PP', 0) # Get duration for PP for this LU, default 0


                    data.append([
                        lo_num,
                        moa,
                        duration_minutes, # Insert duration in minutes as integer
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
    return df


# main function for this script
def map_new_key_names_excel():
    generated_mapping_path = os.path.join('..', 'json_output', 'generated_mapping.json')
    generated_mapping = load_json_file(generated_mapping_path)

    output_json_file = os.path.join('..', 'json_output', 'generated_mapping.json')

    # **Load existing JSON file first**
    existing_data = load_json_file(output_json_file) # Load existing data, returns {} if file not found or invalid JSON

    if existing_data is None: # Error loading existing data
        print("Failed to load existing output JSON, cannot append. Exiting.")
        return

    # sequencing rationale
    sequencing_keys = ["#Rationale[0]", "#Sequencing", "#Conclusion[0]"]
    sequencing_rationale_data = extract_and_concatenate_json_values(generated_mapping, sequencing_keys, "#Sequencing_rationale")

    # tcs code combined with skill name
    tcs_keys = ["#TCS[1]", "#TCS[0]"]
    tcs_code_skill_data = extract_and_concatenate_json_values_space_seperator(generated_mapping, tcs_keys, "#TCS_Code_Skill")

    combined_lo = ["#LO[0]", "#LO[1]", "#LO[2]", "#LO[3]", "#LO[4]", "#LO[5]", "#LO[6]", "#LO[7]"]
    lo_data = extract_and_concatenate_json_values(generated_mapping, combined_lo, "#Combined_LO")

    if sequencing_rationale_data and tcs_code_skill_data: # Check if both data extractions were successful
        # **Update the existing data dictionary**
        existing_data.update(sequencing_rationale_data)
        existing_data.update(tcs_code_skill_data)
        existing_data.update(lo_data)

        # **Write the updated dictionary back to the output file**
        write_json_file(existing_data, output_json_file)
    else:
        print("Error during data extraction, not writing to output file.")

def create_instructional_dataframe(json_data):
    """
    Creates a DataFrame for instructional methods and durations, ensuring total duration
    matches "Course Duration" - "Assessment Hours".

    Args:
        json_data (dict): The JSON data containing course information.

    Returns:
        pandas.DataFrame: A DataFrame representing the instructional schema.
    """

    course_info = json_data["Course Information"]
    learning_units = json_data["TSC and Topics"]["Learning Units"]
    instructional_methods_input = json_data["Assessment Methods"]["Instructional Methods"]
    ka_mapping = json_data["Learning Outcomes"].get("Knowledge and Ability Mapping", {})
    classroom_hours = course_info.get("Classroom Hours", 0)
    practical_hours = course_info.get("Practical Hours", 0) if "Practical Hours" in course_info else 0
    assessment_hours = course_info.get("Number of Assessment Hours", 0)
    course_duration_hours = course_info.get("Course Duration (Number of Hours)", 0)

    # Calculate total instructional hours
    total_instructional_hours = course_duration_hours - assessment_hours
    total_instructional_minutes = total_instructional_hours * 60

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
    practical_rows_count = 0

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
                if method.strip() == "Practical":
                    practical_rows_count += 1

    df = pd.DataFrame(data, columns=["LU#", "Instructional Methods", "Instructional Duration", "MOT"])

    classroom_minutes_total = classroom_hours * 60
    practical_minutes_total = practical_hours * 60

    classroom_duration_per_row = 0
    practical_duration_per_practical_row = 0

    if total_rows > 0:
        classroom_duration_per_row = classroom_minutes_total // total_rows

    if practical_rows_count > 0:
        practical_duration_per_practical_row = practical_minutes_total // practical_rows_count if practical_minutes_total > 0 else 0

    # Assign initial durations based on Classroom and Practical Hours
    for index, row in df.iterrows():
        if row["Instructional Methods"] == "Practical":
            df.loc[index, "Instructional Duration"] = int(practical_duration_per_practical_row) if practical_duration_per_practical_row > 0 else 0
        else:
            df.loc[index, "Instructional Duration"] = int(classroom_duration_per_row)

    # Recalculate total duration and adjust to match total_instructional_minutes
    current_total_duration_minutes = df["Instructional Duration"].sum()
    duration_difference_minutes = total_instructional_minutes - current_total_duration_minutes

    if duration_difference_minutes != 0:
        rows_to_adjust = len(df) # Distribute across all rows
        duration_increment_per_row = duration_difference_minutes // rows_to_adjust
        remainder_duration = duration_difference_minutes % rows_to_adjust

        for index in range(len(df)):
            df.loc[index, "Instructional Duration"] += duration_increment_per_row
            if remainder_duration > 0:
                df.loc[index, "Instructional Duration"] += 1
                remainder_duration -= 1

    return df

def create_instruction_description_dataframe(ensemble_json_path, methods_json_path):
    """
    Creates a DataFrame mapping instructional methods to their descriptions.

    Args:
        ensemble_json_path (str): Path to the ensemble_output.json file.
        methods_json_path (str): Path to the instructional_methods.json file.

    Returns:
        pandas.DataFrame: A DataFrame with "Instructional Method" and "Description" columns.
                         Returns an empty DataFrame if there's an error loading the JSON files.
    """
    try:
        with open(ensemble_json_path, 'r') as f_ensemble:
            ensemble_data = json.load(f_ensemble)
        with open(methods_json_path, 'r') as f_methods:
            methods_data = json.load(f_methods)
    except FileNotFoundError:
        print("Error: One or both JSON files not found. Please check file paths.")
        return pd.DataFrame()  # Return empty DataFrame in case of file error

    instructional_methods_input = ensemble_data.get("Assessment Methods", {}).get("Instructional Methods", [])

    if isinstance(instructional_methods_input, str):
        instructional_methods_list = [method.strip() for method in instructional_methods_input.split(',')]
    elif isinstance(instructional_methods_input, list):
        instructional_methods_list = [method.strip() for method in instructional_methods_input]
    else:
        print(f"Warning: Unexpected type for 'Instructional Methods' in ensemble_output.json: {type(instructional_methods_input)}. Defaulting to empty list.")
        instructional_methods_list = []

    methods_description_map = {}
    for method_item in methods_data.get("Instructional_Methods", []):
        method_name = method_item.get("Method")
        description = method_item.get("Description")
        if method_name and description:
            methods_description_map[method_name] = description

    data = []
    for method in instructional_methods_list:
        description = methods_description_map.get(method, "Description not found.") # Default description if not found
        data.append([method, description])

    df = pd.DataFrame(data, columns=["Instructional Method", "Description"])
    return df

if __name__ == "__main__":
    # map_new_key_names_excel()

    # Load your JSON data
    ensemble_output_path = os.path.join('..', 'json_output', 'ensemble_output.json')
    ensemble_output = load_json_file(ensemble_output_path)

    instructional_methods_path = os.path.join('..', 'json_output', 'instructional_methods.json')
    instructional_methods_output = load_json_file(ensemble_output_path)

    # Create the DataFrame
    # df = create_course_dataframe(ensemble_output)
    # df = create_instructional_dataframe(ensemble_output)
    df = create_instruction_description_dataframe(ensemble_output_path, instructional_methods_path)
    # Print the DataFrame (optional)
    print(df)
    df.to_csv("instructional_methods_dataframe.csv", index=False)

