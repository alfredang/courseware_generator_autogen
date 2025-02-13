# app.py
import streamlit as st
import os
import subprocess
import sys
import tempfile
from main import main

# Initialize session state variables
if 'processing_done' not in st.session_state:
    st.session_state['processing_done'] = False
if 'output_docx' not in st.session_state:
    st.session_state['output_docx'] = None
if 'cv_output_files' not in st.session_state:
    st.session_state['cv_output_files'] = []

def app():
    st.title("📄 Course Proposal File Processor")

    # Add a description of the page with improved styling
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # Descriptive section
    st.markdown("""
    <div class="important-note">
        This tool uses Agentic Process Automation to generate Course Proposals and Course Validation forms for Tertiary Infotech.
        The input TSC form must follow the below requirements, if not the generation might not work properly or might throw errors :(
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="header">📝 Important TSC Details to Look Out For:</div>', unsafe_allow_html=True)

    st.markdown("Instructional and Assessment method names in the TSC should be spelled out like the examples below (Case Sensitive)")
    st.markdown("Eg. Case studies ❌")
    st.markdown("Eg. Case Study ✅️")
    
    # Use columns to organize the content into sections
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="section-title">Instructional Methods:</div>
        - Didactic Questioning <br>
        - Demonstration <br>
        - Practical <br>
        - Peer Sharing <br>
        - Role Play <br>
        - Group Discussion <br>
        - Case Study <br>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="section-title">Assessment Methods:</div>
        - Written Assessment <br>
        - Practical Performance <br>
        - Case Study <br>
        - Oral Questioning <br>
        - Role Play <br>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="header">💡 Tips:</div>
    - Colons ( : ) should be included in every LU and Topic, e.g., LU1: xxx, Topic 1: xxx <br>
    - Ensure LUs are properly formatted using the naming conventions mentioned above. <br>
    - Double check the industry of the CV and background info of the CP, in case the wrong industry is mentioned!
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("📁 Upload a DOCX file", type="docx", key='uploaded_file')

    if uploaded_file is not None:
        st.success(f"📄 Uploaded file: {uploaded_file.name}")

        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            temp_input_file = tmp_file.name

        if st.button("🚀 Process File"):
            run_processing(temp_input_file)
            st.session_state['processing_done'] = True

    # After processing, check if outputs are in session_state and display download buttons
    if st.session_state.get('processing_done'):
        st.markdown('<div class="header">📦 Download Processed Files:</div>', unsafe_allow_html=True)

        # Download button for the output from root's main.py
        output_docx = st.session_state.get('output_docx')
        if output_docx and os.path.exists(output_docx):
            with open(output_docx, 'rb') as f:
                output_data = f.read()
            st.download_button(
                label=f"⬇️ Download {os.path.basename(output_docx)}",
                data=output_data,
                file_name=os.path.basename(output_docx),
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            st.warning("⚠️ Processed output file not found.")

        # Download buttons for the CV output files
        output_files = st.session_state.get('cv_output_files', [])
        # Provide download buttons for each processed file
        for output_file in output_files:
            if os.path.exists(output_file):
                with open(output_file, 'rb') as f:
                    output_data = f.read()
                st.download_button(
                    label=f"⬇️ Download {os.path.basename(output_file)}",
                    data=output_data,
                    file_name=os.path.basename(output_file),
                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            else:
                st.warning(f"⚠️ Expected output {os.path.basename(output_file)} not found.")
def run_processing(input_file):
    try:
        st.info("Processing...")
        main(input_file)

        # Use a temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        output_json = os.path.join(temp_dir, 'json_output/output_TSC.json')
        output_docx = os.path.join(temp_dir, 'Updated_CP_Document2.docx')



        st.success("Processing complete for CP generation. Starting CV generation now.")

        # Save the output_docx in session state
        st.session_state['output_docx'] = output_docx

        # Save the output files in session state
        st.session_state['cv_output_files'] = output_files

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

# if __name__ == "__main__":
#     main()
