# app.py
import streamlit as st
from streamlit_option_menu import option_menu
import cp_generation as cp_generation
import Assessment.assessment_generation as assessment_generation
import Courseware.courseware_generation  as courseware_generation
import Brochure.brochure_generation as brochure_generation
import AnnexAssessment.annex_assessment as annex_assessment
# import Slides.slide_generation as slide_generation
# from Slides.slide_generation import render_slide_generation_ui

st.set_page_config(layout="wide")

# Sidebar navigation with streamlit-option-menu
with st.sidebar:
    selected = option_menu(
        "Tertiary Infotech",  # Title of the sidebar
        ["Generate CP", "Generate AP/FG/LG/LP", "Generate Assessment", "Generate Slides", "Generate Brochure","Add Assessment to AP"],  # Options
        icons=["filetype-doc", "file-earmark-richtext", "clipboard-check", "filetype-pptx", "files-alt", "folder-symlink"],  # Icon names
        menu_icon="boxes",  # Icon for the sidebar title
        default_index=0,  # Default selected item
    )

# Display the selected app
if selected == "Generate CP":
    cp_generation.app()  # Display CP Generation app

elif selected == "Generate AP/FG/LG/LP":
    courseware_generation.app()  # Display Courseware Generation app

elif selected == "Generate Assessment":
    assessment_generation.app()
    # Add Assessment Generation-specific functionality here

elif selected == "Generate Slides":
    # slide_generation.app()  # Display Courseware Generation app
    st.title("Generate Slides")
    st.write("Slides Generation not available.")

elif selected == "Generate Brochure":
    brochure_generation.app() # Display Brochure Generation app
    # Add Assessment Generation-specific functionality here

elif selected == "Add Assessment to AP":
    annex_assessment.app()  # Display Annex Assessment app