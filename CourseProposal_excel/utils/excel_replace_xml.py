import os
import re
import shutil
import tempfile
import zipfile
import json
import pandas as pd
from lxml import etree as ET

def load_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_relationship_mapping(rels_path):
    ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
    tree = ET.parse(rels_path)
    root = tree.getroot()
    rels = {}
    for rel in root.findall('r:Relationship', ns):
        rId = rel.attrib.get('Id')
        target = rel.attrib.get('Target')  # e.g., "worksheets/sheet1.xml"
        # Prepend "xl/" if needed
        rels[rId] = os.path.join('xl', target) if not target.startswith('/') else target[1:]
    return rels

def get_sheet_mapping(workbook_xml_path, rels_map):
    """
    Returns a mapping from sheet name to its full path (within the extracted directory)
    """
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    tree = ET.parse(workbook_xml_path)
    root = tree.getroot()
    mapping = {}
    for sheet in root.xpath('.//main:sheets/main:sheet', namespaces=ns):
        name = sheet.get('name')
        rId = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        if rId in rels_map:
            mapping[name] = rels_map[rId]
    return mapping

def col_idx_to_letter(n):
    """Converts a 1-indexed column number to an Excel column letter."""
    result = ""
    while n:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result

def update_cell_in_sheet(sheet_xml_path, cell_ref, new_value):
    """
    Updates the cell with reference cell_ref in the sheet XML using lxml.
    This version preserves namespaces and structure.
    If new_value is a list and contains only one element, that element is used.
    Otherwise, multiple items are joined with a newline.
    """
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    parser = ET.XMLParser(remove_blank_text=False)
    tree = ET.parse(sheet_xml_path, parser)
    root = tree.getroot()
    found = False

    # Flatten new_value if it's a list
    if isinstance(new_value, list):
        if len(new_value) == 1:
            new_value = new_value[0]
        else:
            new_value = "\n".join(map(str, new_value))

    # Find the <c> element with attribute r equal to cell_ref
    for cell in root.xpath('.//main:c[@r="%s"]' % cell_ref, namespaces=ns):
        # Skip cells that have a formula (we don’t want to overwrite them)
        if cell.xpath('main:f', namespaces=ns):
            print(f"Skipping formula cell {cell_ref}")
            return False

        # Remove any existing value elements (<v> or <is>)
        for child in list(cell):
            if child.tag in {f"{{{ns['main']}}}v", f"{{{ns['main']}}}is"}:
                cell.remove(child)
        # Set type attribute to inline string
        cell.set('t', 'inlineStr')
        is_elem = ET.Element(f"{{{ns['main']}}}is")
        t_elem = ET.Element(f"{{{ns['main']}}}t")
        t_elem.text = str(new_value)
        is_elem.append(t_elem)
        cell.append(is_elem)
        found = True
        break

    if not found:
        print(f"Cell {cell_ref} not found in {sheet_xml_path}. Skipping.")
        return False

    tree.write(sheet_xml_path, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    return True

def insert_dataframe_into_sheet(sheet_xml_path, start_row, start_col, df):
    """
    Inserts the DataFrame into the worksheet XML starting at the given row and column.
    For each cell, the value is stored as an inline string.
    """
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    parser = ET.XMLParser(remove_blank_text=False)
    tree = ET.parse(sheet_xml_path, parser)
    root = tree.getroot()

    # Locate the sheetData element
    sheetData = root.find(f"{{{ns['main']}}}sheetData")
    if sheetData is None:
        # Create one if not present.
        sheetData = ET.SubElement(root, f"{{{ns['main']}}}sheetData")

    # For each row in the DataFrame, create/update a row element.
    # Assume start_row and start_col are 1-indexed.
    for i, row_values in enumerate(df.values):
        current_row_number = start_row + i
        # Try to find an existing <row> element with attribute r=current_row_number
        row_elem = sheetData.find(f".//{{{ns['main']}}}row[@r='{current_row_number}']")
        if row_elem is None:
            row_elem = ET.SubElement(sheetData, f"{{{ns['main']}}}row", r=str(current_row_number))
        # For each cell in the row:
        for j, cell_value in enumerate(row_values):
            col_letter = col_idx_to_letter(start_col + j)
            cell_ref = f"{col_letter}{current_row_number}"

            # Check if a cell with this reference already exists in the row.
            cell_elem = None
            for cell in row_elem.findall(f"{{{ns['main']}}}c"):
                if cell.get('r') == cell_ref:
                    cell_elem = cell
                    break
            if cell_elem is None:
                cell_elem = ET.SubElement(row_elem, f"{{{ns['main']}}}c", r=cell_ref)
            # Remove any existing value or inline string
            for child in list(cell_elem):
                if child.tag in {f"{{{ns['main']}}}v", f"{{{ns['main']}}}is"}:
                    cell_elem.remove(child)
            # Set cell type to inline string
            cell_elem.set('t', 'inlineStr')
            is_elem = ET.Element(f"{{{ns['main']}}}is")
            t_elem = ET.Element(f"{{{ns['main']}}}t")
            t_elem.text = str(cell_value)
            is_elem.append(t_elem)
            cell_elem.append(is_elem)
            # (Optionally, you could set style attributes if needed.)

    # Optionally, update the dimension element if present.
    dimension_elem = root.find(f"{{{ns['main']}}}dimension")
    if dimension_elem is not None:
        # Compute new ref: from A1 to the bottom-right cell of the updated area.
        # (Here we assume that the updated block starts at start_row, start_col)
        max_col = col_idx_to_letter(start_col + df.shape[1] - 1)
        max_row = start_row + df.shape[0] - 1
        dimension_elem.set('ref', f"A1:{max_col}{max_row}")

    tree.write(sheet_xml_path, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    print(f"Inserted DataFrame into {sheet_xml_path}")

def process_excel_update(json_data_path, excel_template_path, output_excel_path, ensemble_output_path):
    """
    Updates specific cells in an Excel workbook (including inserting a DataFrame)
    by only modifying the worksheet XML parts. This approach unzips the .xlsx,
    updates cells, and then repackages it—preserving all other parts.
    """
    json_data = load_json_file(json_data_path)
    if not json_data:
        print("Failed to load JSON data.")
        return

    ensemble_output = load_json_file(ensemble_output_path)
    if not ensemble_output:
        print("Failed to load Ensemble Output JSON data.")
        return

    # Define cell mapping as before
    cell_replacement_map = {
        "#Company":      {"sheet": "1 - Course Particulars", "cell": "C2", "json_key": "#Company"},
        "#CourseTitle":   {"sheet": "1 - Course Particulars", "cell": "C3", "json_key": "#CourseTitle"},
        "#TCS_Code_Skill": {"sheet": "1 - Course Particulars", "cell": "C10", "json_key": "#TCS_Code_Skill"},
        "#Placeholder[0]": {"sheet": "2 - Background", "cell": "B4", "json_key": "#Placeholder[0]"},
        "#Placeholder[1]": {"sheet": "2 - Background", "cell": "B8", "json_key": "#Placeholder[1]"},
        "#Sequencing_rationale": {"sheet": "3 - Instructional Design", "cell": "B6", "json_key": "#Sequencing_rationale"},
        "#Combined_LO": {"sheet": "3 - Instructional Design", "cell": "B4", "json_key": "#Combined_LO"}
    }

    temp_dir = tempfile.mkdtemp()
    try:
        # Extract the entire workbook archive
        with zipfile.ZipFile(excel_template_path, 'r') as zin:
            zin.extractall(temp_dir)
        print(f"Extracted workbook to {temp_dir}")

        # Build mapping of sheet names to XML file paths
        rels_path = os.path.join(temp_dir, "xl", "_rels", "workbook.xml.rels")
        workbook_xml_path = os.path.join(temp_dir, "xl", "workbook.xml")
        rels_map = get_relationship_mapping(rels_path)
        sheet_mapping = get_sheet_mapping(workbook_xml_path, rels_map)

        # Update individual cells based on cell_replacement_map
        for key, mapping in cell_replacement_map.items():
            sheet_name = mapping.get("sheet")
            cell_ref = mapping.get("cell")
            json_key = mapping.get("json_key")
            new_value = json_data.get(json_key)
            if new_value is None:
                print(f"JSON key '{json_key}' not found. Skipping cell {cell_ref} in sheet {sheet_name}.")
                continue
            if sheet_name not in sheet_mapping:
                print(f"Sheet '{sheet_name}' not found in workbook. Skipping.")
                continue
            sheet_xml_path = os.path.join(temp_dir, sheet_mapping[sheet_name])
            if not re.match(r'^[A-Z]+[1-9][0-9]*$', cell_ref):
                print(f"Invalid cell reference '{cell_ref}'. Skipping.")
                continue

            updated = update_cell_in_sheet(sheet_xml_path, cell_ref, new_value)
            if updated:
                print(f"Updated {sheet_name} cell {cell_ref} with value: {new_value}")

        # Insert the DataFrame into a designated sheet (e.g., "3 - Instructional Design")
        if "3 - Instructional Design" in sheet_mapping:
            # Create the DataFrame using your helper function (provided separately)
            df = create_course_dataframe(ensemble_output)
            if not df.empty:
                sheet_xml_path = os.path.join(temp_dir, sheet_mapping["3 - Instructional Design"])
                # For example, insert starting at row 18 and column 2 (B18)
                insert_dataframe_into_sheet(sheet_xml_path, start_row=17, start_col=2, df=df)
            else:
                print("Warning: DataFrame is empty. Nothing to insert.")
        else:
            print("Sheet '3 - Instructional Design' not found. DataFrame not inserted.")

        # Repackage the updated directory into a new .xlsx file
        with zipfile.ZipFile(output_excel_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for foldername, subfolders, filenames in os.walk(temp_dir):
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zout.write(file_path, arcname)
        print(f"Repackaged updated workbook to {output_excel_path}")

    finally:
        shutil.rmtree(temp_dir)

# Example DataFrame creator (from your provided code)
def create_course_dataframe(json_data):
    """
    Creates a DataFrame from the provided JSON data, structured as requested.
    """
    learning_units = json_data["TSC and Topics"].get("Learning Units", [])
    learning_outcomes = json_data["Learning Outcomes"].get("Learning Outcomes", [])
    knowledge_statements = json_data["Learning Outcomes"].get("Knowledge", [])
    ability_statements = json_data["Learning Outcomes"].get("Ability", [])
    course_outline = json_data["Assessment Methods"].get("Course Outline", {}).get("Learning Units", {})
    tsc_code = json_data["TSC and Topics"].get("TSC Code", ["N/A"])[0]

    data = []
    for lu_index, lu_title in enumerate(learning_units):
        lu_num = f"LU{lu_index + 1}"
        # Split at ": " to remove the prefix (assumes format "LUx: title")
        lu_title_only = lu_title.split(": ", 1)[1] if ": " in lu_title else lu_title

        lo_title = learning_outcomes[lu_index] if lu_index < len(learning_outcomes) else "N/A"
        lo_num = f"LO{lu_index + 1}"
        lo_title_only = lo_title.split(": ", 1)[1] if (lo_title != "N/A" and ": " in lo_title) else lo_title

        lu_key = f"LU{lu_index + 1}"
        if lu_key in course_outline:
            topics = course_outline[lu_key].get("Description", [])
            for topic in topics:
                topic_title_full = topic.get("Topic", "N/A")
                topic_num = topic_title_full.split(":")[0].replace("Topic ", "T")
                topic_title = topic_title_full.split(': ', 1)[1] if ': ' in topic_title_full else topic_title_full
                topic_title_short = topic_title.split(' (')[0]

                ka_codes_str = topic_title_full.split('(')[-1].rstrip(')')
                ka_codes = [code.strip() for code in ka_codes_str.split(',')]
                for code in ka_codes:
                    if code.startswith('K'):
                        k_index = int(code[1:]) - 1
                        k_statement = f"{knowledge_statements[k_index]} ({tsc_code})" if 0 <= k_index < len(knowledge_statements) else f"{code}: N/A ({tsc_code})"
                        data.append([
                            lu_num,
                            lu_title_only,
                            lo_num,
                            lo_title_only,
                            f"{topic_num}: {topic_title_short}",
                            k_statement,
                            "Written Exam"
                        ])
                    elif code.startswith('A'):
                        a_index = int(code[1:]) - 1
                        a_statement = f"{ability_statements[a_index]} ({tsc_code})" if 0 <= a_index < len(ability_statements) else f"{code}: N/A ({tsc_code})"
                        data.append([
                            lu_num,
                            lu_title_only,
                            lo_num,
                            lo_title_only,
                            f"{topic_num}: {topic_title_short}",
                            a_statement,
                            "Practical Exam"
                        ])
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

if __name__ == "__main__":
    json_data_path = os.path.join('..', 'json_output', 'generated_mapping.json')
    excel_template_path = os.path.join('..', 'templates', 'CP_excel_template.xlsx')
    output_excel_path = os.path.join('..', 'output_docs', 'CP_template_updated_preserving_all_parts.xlsx')
    ensemble_output_path = os.path.join('..', 'json_output', 'ensemble_output.json')
    process_excel_update(json_data_path, excel_template_path, output_excel_path, ensemble_output_path)
