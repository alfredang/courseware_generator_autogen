import json
import sys
import os

def load_json_file(file_path):
    """
    Loads JSON data from a file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The loaded JSON data as a dictionary, or None if an error occurs.
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at '{file_path}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from file '{file_path}'. Please ensure it is valid JSON.")
        return None

def extract_and_concatenate_json_values(json_data, keys_to_extract, new_key_name):
    """
    Extracts values from JSON data based on keys, concatenates them into a string with newlines,
    and returns a dictionary containing the concatenated string under a new key.

    Args:
        json_data (dict): The JSON data as a dictionary.
        keys_to_extract (list of str): A list of keys to extract values from. Keys can include array indexing like "key[index]".
        new_key_name (str): The name of the new key for the concatenated string in the output.

    Returns:
        dict: A dictionary containing the new key and the concatenated string, or None if input json_data is None.
    """
    if json_data is None:
        return None

    concatenated_string = ""
    for key_path in keys_to_extract:
        try:
            # Handle potential array indexing in keys like "key[index]"
            base_key = key_path
            index = None
            if '[' in key_path and key_path.endswith(']'):
                base_key_parts = key_path.split('[')
                base_key = base_key_parts[0]
                index_str = base_key_parts[1][:-1] # Remove closing bracket
                try:
                    index = int(index_str)
                except ValueError:
                    print(f"Warning: Invalid array index format in key '{key_path}'. Ignoring index.")
                    index = None # Treat as no index if not an integer

            value = json_data.get(base_key)

            if value is None:
                print(f"Warning: Key '{base_key}' not found in JSON data.")
                continue # Skip to the next key if not found

            if isinstance(value, list):
                if index is not None: # Access list element by index
                    if 0 <= index < len(value):
                        list_value = value[index]
                        if isinstance(list_value, list): # Nested list handling - flatten if needed
                            concatenated_string += "\n".join(map(str, list_value)) + "\n"
                        else:
                            concatenated_string += str(list_value) + "\n"
                    else:
                        print(f"Warning: Index '{index}' out of range for key '{base_key}'. Skipping.")
                else: # Concatenate all list items if no index specified
                    concatenated_string += "\n".join(map(str, value)) + "\n" # Map to str to handle non-string list elements if any
            else: # If value is not a list (e.g., string, number)
                concatenated_string += str(value) + "\n" # Ensure it's a string

        except KeyError:
            print(f"Error: Key '{key_path}' not found in JSON data.")
        except IndexError:
            print(f"Error: Index out of range accessing value for key '{key_path}'.")
        except TypeError as e: # Handle cases where indexing might be attempted on non-list
            print(f"TypeError accessing key '{key_path}': {e}")


    output_data = {new_key_name: concatenated_string.rstrip('\n')} # rstrip to remove trailing newline
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
    tcs_code_skill_data = extract_and_concatenate_json_values(generated_mapping, tcs_keys, "#TCS_Code_Skill")

    if sequencing_rationale_data and tcs_code_skill_data: # Check if both data extractions were successful
        # **Update the existing data dictionary**
        existing_data.update(sequencing_rationale_data)
        existing_data.update(tcs_code_skill_data)

        # **Write the updated dictionary back to the output file**
        write_json_file(existing_data, output_json_file)
    else:
        print("Error during data extraction, not writing to output file.")




if __name__ == "__main__":
    map_new_key_names_excel()