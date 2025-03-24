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
    st.session_state['selected_model'] = "GPT-4o Mini (Default)"

def app():
    st.title("📄 Course Proposal File Processor")

    st.subheader("Model Selection")
    model_choice = st.selectbox(
        "Select LLM Model:",
        options=list(MODEL_CHOICES.keys()),
        index=4  # default: "GPT-4o Mini (Default)"
    )
    st.session_state['selected_model'] = model_choice

    # Add a description of the page with improved styling
    st.markdown(
        """
        <style>
            .important-note {
                background-color: #f0f8ff;
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
        - Double check the industry of the CV and background info of the CP, in case the wrong industry is mentioned!
        """,
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader("Upload a TSC DOCX file", type="docx", key='uploaded_file')

    if uploaded_file is not None:
        st.success(f"Uploaded file: {uploaded_file.name}")

        # 1) Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_input:
            tmp_input.write(uploaded_file.getbuffer())
            input_tsc_path = tmp_input.name

        # 2) Process button
        if st.button("🚀 Process File"):
            # Optional: parse_document before the main pipeline if you want:
            # parse_document(input_tsc_path, "json_output/output_TSC_TEST.json")
            run_processing(input_tsc_path)
            st.session_state['processing_done'] = True

    # 3) Display download buttons after processing
    if st.session_state.get('processing_done'):
        st.subheader("Download Processed Files")

        # CP docx
        cp_docx_temp = st.session_state.get('cp_docx_temp')
        if cp_docx_temp and os.path.exists(cp_docx_temp):
            with open(cp_docx_temp, 'rb') as f:
                data = f.read()
            st.download_button(
                label="Download CP Output",
                data=data,
                file_name="CP_output.docx",
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            st.warning("No CP docx found in session state.")

        # CV docs
        cv_docx_temps = st.session_state.get('cv_docx_temps', [])
        # Now cv_docx_temps is a list of tuples: (temp_path, final_filename)
        for idx, (temp_path, final_name) in enumerate(cv_docx_temps, start=1):
            if os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    data = f.read()
                st.download_button(
                    label=f"Download CV Output {idx}",
                    data=data,
                    file_name=final_name,  # Show user the actual name we want
                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            else:
                st.warning(f"No CV docx found at {temp_path}")

def run_processing(input_file: str):
    """
    1. Runs your main pipeline, which writes docs to 'output_docs/' 
    2. Copies those docs into NamedTemporaryFiles and stores them in session state.
    """
    st.info("Running pipeline (this might take some time) ...")

    # 1) Run the pipeline (async), passing the TSC doc path
    asyncio.run(main(input_file))

    # 2) Now copy the relevant docx files from 'output_docs' to NamedTemporaryFiles
    cp_doc_path = "CourseProposal/output_docs/CP_output.docx"
    cv_doc_paths = [
        "CourseProposal/output_docs/CP_validation_template_bernard_updated.docx",
        "CourseProposal/output_docs/CP_validation_template_dwight_updated.docx",
        "CourseProposal/output_docs/CP_validation_template_ferris_updated.docx",
        # "CourseProposal/output_docs/CP_template_metadata_preserved.xlsx"
    ]

    # Copy CP doc into tempfile
    if os.path.exists(cp_doc_path):
        with open(cp_doc_path, 'rb') as infile, tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as outfile:
            outfile.write(infile.read())
            st.session_state['cp_docx_temp'] = outfile.name

    # Copy CV docs
    cv_temp_paths = []
    for doc_path in cv_doc_paths:
        if os.path.exists(doc_path):
            with open(doc_path, 'rb') as infile, tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as outfile:
                outfile.write(infile.read())
                # The final file name we want to present to the user:
                desired_name = os.path.basename(doc_path)  
                # e.g. "CP_validation_template_bernard_updated.docx"

                # Store tuple: (tempfile_path, final_file_name)
                cv_temp_paths.append((outfile.name, desired_name))

    st.session_state['cv_docx_temps'] = cv_temp_paths

    st.success("Processing complete. Download your files below!")

if __name__ == "__main__":
    app()
