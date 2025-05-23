# app.py
import streamlit as st
import os
import tempfile
from CourseProposal.main import main
import asyncio
from CourseProposal.utils.document_parser import parse_document
from CourseProposal.model_configs import MODEL_CHOICES

# Initialize session state variables
if 'processing_done' not in st.session_state:
    st.session_state['processing_done'] = False
if 'output_docx' not in st.session_state:
    st.session_state['output_docx'] = None
if 'cv_output_files' not in st.session_state:
    st.session_state['cv_output_files'] = []
if 'selected_model' not in st.session_state:
    st.session_state['selected_model'] = "DeepSeek-V3"
if 'ka_validation_results' not in st.session_state:
    st.session_state['ka_validation_results'] = {}
if 'validation_displayed' not in st.session_state:
    st.session_state['validation_displayed'] = False

def app():
    st.title("📄 Course Proposal File Processor")

    st.subheader("Model Selection")
    model_choice = st.selectbox(
        "Select LLM Model:",
        options=list(MODEL_CHOICES.keys()),
        index=list(MODEL_CHOICES.keys()).index("DeepSeek-V3")
    )
    st.session_state['selected_model'] = model_choice

    st.subheader("Course Proposal Type")
    cp_type_display = st.selectbox(
        "Select CP Type:",
        options=["Excel CP", "Docx CP"],
        index=0  # default: "Excel CP: New CP"
    )
    # Map display values to backend values
    cp_type_mapping = {
        "Excel CP": "New CP",
        "Docx CP": "Old CP"
    }
    st.session_state['cp_type'] = cp_type_mapping[cp_type_display]

    # Add a description of the page with improved styling
    st.markdown(
        """
        <style>
            .important-note {
                background-color: #000000;
                padding: 15px;
                border-radius: 10px;
                border-left: 6px solid #2196f3;
                font-size: 15px;
            }
            .header {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin-top: 20px;
            }
            .section-title {
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Descriptive section
    st.markdown(
        """
        <div class="important-note">
            This tool uses Agentic Process Automation to generate Course Proposals and Course Validation forms for Tertiary Infotech.
            The input TSC form must follow the below requirements, if not the generation might not work properly or might throw errors :(
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="header">📝 Important TSC Details to Look Out For:</div>',
        unsafe_allow_html=True
    )

    st.markdown("Instructional and Assessment method names in the TSC should be spelled out like the examples below (Case Sensitive)")
    st.markdown("Eg. Case studies ❌")
    st.markdown("Eg. Case Study ✅️")
    
    # Use columns to organize the content into sections
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            """
            <div class="section-title">Instructional Methods:</div>
            - Didactic Questioning <br>
            - Demonstration <br>
            - Practical <br>
            - Peer Sharing <br>
            - Role Play <br>
            - Group Discussion <br>
            - Case Study <br>
            """,
            unsafe_allow_html=True
        )
        
    with col2:
        st.markdown(
            """
            <div class="section-title">Assessment Methods:</div>
            - Written Assessment <br>
            - Practical Performance <br>
            - Case Study <br>
            - Oral Questioning <br>
            - Role Play <br>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="header">💡 Tips:</div>
        - Colons ( : ) should be included in every LU and Topic, e.g., LU1: xxx, Topic 1: xxx <br>
        - Ensure LUs are properly formatted using the naming conventions mentioned above. <br>
        - Double check the industry of the CV and background info of the CP, in case the wrong industry is mentioned! <br>
        - Ensure your TSC document is in .docx format <br>
        - Make sure your TSC document is properly formatted <br>
        - Check that all required sections are present <br>
        - Verify that the TSC code and title are correct <br>
        """,
        unsafe_allow_html=True
    )

    # Always display validation results here, if available
    if st.session_state.get('validation_displayed'):
        display_validation_results()

    # Add extra spacing after tips and validation results
    st.markdown("<div style='margin-bottom: 0.5em;'></div>", unsafe_allow_html=True)

    # Larger upload file label
    st.markdown("""
        <div style='font-size: 1.3em; font-weight: bold;'>Upload a TSC DOCX file</div>
    """, unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload a TSC DOCX file",
        type="docx",
        key='uploaded_file',
        label_visibility="collapsed"
    )

    if uploaded_file is not None:
        st.success(f"Uploaded file: {uploaded_file.name}")

        # 1) Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_input:
            tmp_input.write(uploaded_file.getbuffer())
            input_tsc_path = tmp_input.name

        # 2) Process button
        if st.button("🚀 Process File"):
            run_processing(input_tsc_path)
            st.session_state['processing_done'] = True

        # 3) Display download buttons after processing
        if st.session_state.get('processing_done'):
            st.subheader("Download Processed Files")
            
            # Get CP type to show relevant information
            cp_type = st.session_state.get('cp_type', "New CP")
            
            # Get file download data
            file_downloads = st.session_state.get('file_downloads', {})
            
            # Display CP Word document
            cp_docx = file_downloads.get('cp_docx')
            if cp_type == "Old CP":
                if cp_docx and os.path.exists(cp_docx['path']):
                    with open(cp_docx['path'], 'rb') as f:
                        data = f.read()
                    st.download_button(
                        label="📄 Download CP Document",
                        data=data,
                        file_name=cp_docx['name'],
                        mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    )
            
            # Display Excel file for New CP
            if cp_type == "New CP":
                excel_file = file_downloads.get('excel')
                if excel_file and os.path.exists(excel_file['path']):
                    with open(excel_file['path'], 'rb') as f:
                        data = f.read()
                    st.download_button(
                        label="📊 Download CP Excel",
                        data=data,
                        file_name=excel_file['name'],
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                elif cp_type == "New CP":
                    st.warning("Excel file was not generated. This may be normal if processing was interrupted.")
            
            # Display CV validation documents
            cv_docs = file_downloads.get('cv_docs', [])
            if cv_docs:
                st.markdown("### Course Validation Documents")
                
                # Use columns to organize multiple download buttons
                cols = st.columns(min(3, len(cv_docs)))
                for idx, doc in enumerate(cv_docs):
                    if os.path.exists(doc['path']):
                        with open(doc['path'], 'rb') as f:
                            data = f.read()
                        
                        # Extract name from the filename (e.g. extract "Bernard" from "CP_validation_template_bernard_updated.docx")
                        file_base = os.path.basename(doc['name'])
                        validator_name = file_base.split('_')[3].capitalize()
                        
                        col_idx = idx % len(cols)
                        with cols[col_idx]:
                            st.download_button(
                                label=f"📝 {validator_name}",
                                data=data,
                                file_name=doc['name'],
                                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                            )

def run_processing(input_file: str):
    """
    1. Runs your main pipeline, which writes docs to 'output_docs/' 
    2. Copies those docs into NamedTemporaryFiles and stores them in session state.
    """
    st.info("Running pipeline (this might take some time) ...")
    
    # Get CP type from session state
    cp_type = st.session_state.get('cp_type', "New CP")

    # 1) Run the pipeline (async), passing the TSC doc path
    asyncio.run(main(input_file))

    # Set validation as displayed
    st.session_state['validation_displayed'] = True

    # 2) Now copy the relevant docx files from 'output_docs' to NamedTemporaryFiles
    # Common files for both CP types
    cp_doc_path = "CourseProposal/output_docs/CP_output.docx"
    cv_doc_paths = [
        "CourseProposal/output_docs/CP_validation_template_bernard_updated.docx",
        "CourseProposal/output_docs/CP_validation_template_dwight_updated.docx",
        "CourseProposal/output_docs/CP_validation_template_ferris_updated.docx",
    ]
    
    # Excel file - only for "New CP"
    excel_path = "CourseProposal/output_docs/CP_template_metadata_preserved.xlsx"
    
    # Store file info based on CP type
    st.session_state['file_downloads'] = {
        'cp_docx': None,
        'cv_docs': [],
        'excel': None
    }

    # Copy CP doc into tempfile
    if os.path.exists(cp_doc_path):
        with open(cp_doc_path, 'rb') as infile, tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as outfile:
            outfile.write(infile.read())
            st.session_state['file_downloads']['cp_docx'] = {
                'path': outfile.name,
                'name': "CP_output.docx"
            }

    # Copy CV docs
    for doc_path in cv_doc_paths:
        if os.path.exists(doc_path):
            with open(doc_path, 'rb') as infile, tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as outfile:
                outfile.write(infile.read())
                desired_name = os.path.basename(doc_path)
                st.session_state['file_downloads']['cv_docs'].append({
                    'path': outfile.name,
                    'name': desired_name
                })

    # Copy Excel file - only for New CP
    if cp_type == "New CP" and os.path.exists(excel_path):
        with open(excel_path, 'rb') as infile, tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as outfile:
            outfile.write(infile.read())
            st.session_state['file_downloads']['excel'] = {
                'path': outfile.name,
                'name': "CP_Excel_output.xlsx"
            }

    st.success("Processing complete. Download your files below!")

def display_validation_results():
    """Display Knowledge and Ability validation results"""
    if 'ka_validation_results' in st.session_state and st.session_state['ka_validation_results']:
        validation_results = st.session_state['ka_validation_results'].get('validation_results', {})
        fix_results = st.session_state['ka_validation_results'].get('fix_results', {})
        
        if validation_results:
            with st.expander("Knowledge and Ability Validation Results", expanded=not validation_results.get('success', False)):
                # Show summary results
                if validation_results.get('success', False):
                    st.success("✅ SUCCESS: All Knowledge and Ability factors are accounted for.")
                else:
                    st.error(f"❌ FAIL: {len(validation_results.get('missing_factors', []))} missing factors, {len(validation_results.get('undefined_factors', []))} undefined factors")
                
                # Show coverage metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total K&A Factors", validation_results.get('total_factors', 0))
                with col2:
                    st.metric("Covered Factors", len(validation_results.get('covered_factors', [])))
                with col3:
                    st.metric("Coverage %", f"{validation_results.get('coverage_percentage', 0):.1f}%")
                
                # Show missing factors if any
                if validation_results.get('missing_factors'):
                    st.subheader("Missing Factors")
                    for factor in validation_results.get('missing_factors', []):
                        st.markdown(f"- {factor}")
                    
                    st.markdown("""
                    **How to fix:**
                    - Ensure all Knowledge and Ability statements are referenced in at least one topic
                    - Check if any Learning Units are missing their K&A factors in parentheses
                    """)
                
                # Show undefined factors if any
                if validation_results.get('undefined_factors'):
                    st.subheader("Undefined Factors")
                    for factor in validation_results.get('undefined_factors', []):
                        st.markdown(f"- {factor}")
                    
                    st.markdown("""
                    **How to fix:**
                    - Remove references to non-existent K&A factors from topics
                    - Or add these factors to the Knowledge/Ability lists
                    """)
        
        # Show fix results if any topics were fixed
        if fix_results and fix_results.get('fixed_count', 0) > 0:
            with st.expander("Knowledge and Ability Auto-Fix Results", expanded=True):
                st.success(f"✅ {fix_results.get('fixed_count', 0)} topics fixed with missing K&A references")
                
                # Show detailed fix information
                for i, fix in enumerate(fix_results.get('fixed_topics', []), 1):
                    st.markdown(f"**Fix {i}:**")
                    st.markdown(f"- Learning Unit: {fix.get('learning_unit')}")
                    st.markdown(f"- Original: {fix.get('original')}")
                    st.markdown(f"- Fixed: {fix.get('fixed')}")
                    st.markdown(f"- Added factors: {', '.join(fix.get('added_factors', []))}")
                    st.markdown("---")

if __name__ == "__main__":
    app()
