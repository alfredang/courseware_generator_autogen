import os
import re
import shutil
import tempfile
import zipfile
import json
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

def process_excel_update(json_data_path, excel_template_path, output_excel_path):
    """
    Updates specific cells in an Excel workbook by only modifying the worksheet XML parts.
    This approach unzips the .xlsx, updates cells, and then repackages it—preserving all other parts.
    """
    json_data = load_json_file(json_data_path)
    if not json_data:
        print("Failed to load JSON data.")
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

        # For each mapping, update the corresponding cell in the correct sheet XML
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

if __name__ == "__main__":
    json_data_path = os.path.join('..', 'json_output', 'generated_mapping.json')
    excel_template_path = os.path.join('..', 'templates', 'CP_excel_template.xlsx')
    output_excel_path = os.path.join('..', 'output_docs', 'CP_template_updated_preserving_all_parts.xlsx')
    process_excel_update(json_data_path, excel_template_path, output_excel_path)
