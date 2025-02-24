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


if __name__ == "__main__":
    # map_new_key_names_excel()

    # Load your JSON data
    ensemble_output_path = os.path.join('..', 'json_output', 'ensemble_output.json')
    ensemble_output = load_json_file(ensemble_output_path)

    # Create the DataFrame
    df = create_course_dataframe(ensemble_output)

    # Print the DataFrame (optional)
    print(df)
    df.to_csv("course_dataframe.csv", index=False)

