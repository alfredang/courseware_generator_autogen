# app.py
import streamlit as st
from streamlit_option_menu import option_menu
from generate_ap_fg_lg_lp.utils.organizations import get_organizations, get_default_organization
import base64

# Lazy loading functions for better performance
def lazy_import_assessment():
    import generate_assessment.assessment_generation as assessment_generation
    return assessment_generation

def lazy_import_courseware():
    import generate_ap_fg_lg_lp.courseware_generation as courseware_generation
    return courseware_generation

def lazy_import_brochure_v2():
    import generate_brochure_v2.brochure_generation_v2 as brochure_generation_v2
    return brochure_generation_v2

def lazy_import_annex_v2():
    import add_assessment_to_ap.annex_assessment_v2 as annex_assessment_v2
    return annex_assessment_v2

def lazy_import_course_proposal():
    import generate_cp.app as course_proposal_app
    return course_proposal_app

def lazy_import_docs():
    import check_documents.sup_doc as sup_doc
    return sup_doc

def lazy_import_settings():
    import settings.settings as settings
    return settings


st.set_page_config(layout="wide")

@st.cache_data
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        # Fallback to default logo if file not found
        with open("common/logo/tertiary_infotech_pte_ltd.jpg", "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()

# Initialize API system - cached
@st.cache_resource
def initialize_apis():
    try:
        from settings.api_manager import initialize_api_system
        initialize_api_system()
    except ImportError:
        pass

initialize_apis()

# Get organizations and setup company selection - cached
@st.cache_data
def get_cached_organizations():
    return get_organizations()

@st.cache_data
def get_cached_default_organization():
    return get_default_organization()

organizations = get_cached_organizations()
default_org = get_cached_default_organization()

with st.sidebar:
    # Company Selection
    if organizations:
        company_names = [org["name"] for org in organizations]

        # Validate stored index to prevent out-of-range errors
        stored_idx = st.session_state.get('selected_company_idx', 0)
        if stored_idx >= len(organizations):
            stored_idx = 0

        selected_company_idx = st.selectbox(
            "🏢 Select Company:",
            range(len(company_names)),
            format_func=lambda x: company_names[x],
            index=stored_idx
        )

        # Store selection in session state
        st.session_state['selected_company_idx'] = selected_company_idx
        selected_company = organizations[selected_company_idx]
    else:
        selected_company = default_org
        st.session_state['selected_company_idx'] = 0

    # Store selected company in session state for other modules
    st.session_state['selected_company'] = selected_company
    
    # Convert the company logo to a base64 string
    logo_path = selected_company.get("logo", "common/logo/tertiary_infotech_pte_ltd.jpg")
    image_base64 = get_base64_image(logo_path)
    
    # Display company info
    company_display_name = selected_company["name"].replace(" Pte Ltd", "").replace(" LLP", "")
    company_uen = selected_company.get("uen", "N/A")
    st.markdown(
        f"""
        <div style="display: flex; justify-content: left;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="flex-shrink: 0;">
                    <img src="data:image/jpeg;base64,{image_base64}" width="70">
                </div>
                <div style="height:70px; display: flex; align-items: left; justify-content: flex-start;">
                    <h1 style="margin: 0; font-size: 1.5rem;">{company_display_name}</h1>
                </div>
            </div>
        </div>
        <div style="margin-top: 5px; margin-bottom: 15px;">
            <p style="margin: 0; font-size: 0.9rem; color: #666;">UEN: {company_uen}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    # Initialize settings expansion state
    if 'settings_expanded' not in st.session_state:
        st.session_state.settings_expanded = False

    # Build dynamic menu options based on settings expansion state
    menu_options = [
        "Generate CP",
        "Generate AP/FG/LG/LP",
        "Generate Assessment",
        "Generate Brochure v2",
        "Add Assessment to AP",
        "Check Documents",
        f"Settings {'▼' if not st.session_state.settings_expanded else '▲'}"
    ]

    menu_icons = [
        "filetype-doc",
        "file-earmark-richtext",
        "clipboard-check",
        "file-earmark-pdf",
        "folder-symlink",
        "search",
        "gear"
    ]

    # Add sub-options if Settings is expanded
    if st.session_state.settings_expanded:
        menu_options.extend(["    ├ API & LLM Models", "    └ Company Management"])
        menu_icons.extend(["", ""])

    # Custom CSS for menu styling
    st.markdown("""
    <style>
    /* General menu styling */
    div[data-testid="stSidebar"] .nav-link {
        font-size: 0.95rem !important;
    }

    /* Sub-menu items styling */
    div[data-testid="stSidebar"] .nav-link:has-text("├"),
    div[data-testid="stSidebar"] .nav-link:has-text("└") {
        font-size: 0.8rem !important;
        color: #777 !important;
        background-color: rgba(240, 240, 240, 0.3) !important;
        padding-left: 2rem !important;
        border-left: 2px solid #ddd !important;
        margin-left: 0.5rem !important;
    }

    /* Settings arrow positioning */
    .nav-link[data-option*="Settings"] .nav-link-text {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
    }
    </style>
    """, unsafe_allow_html=True)

    selected = option_menu(
        "",  # Title of the sidebar
        menu_options,
        icons=menu_icons,
        menu_icon="boxes",  # Icon for the sidebar title
        default_index=0,  # Default selected item
    )

    # Handle Settings expansion/collapse
    if "Settings" in selected:
        st.session_state.settings_expanded = not st.session_state.settings_expanded
        st.rerun()

# Display the selected app - using lazy loading for performance
if selected == "Generate CP":
    course_proposal_app = lazy_import_course_proposal()
    course_proposal_app.app()  # Display CP Generation app

elif selected == "Generate AP/FG/LG/LP":
    courseware_generation = lazy_import_courseware()
    courseware_generation.app()  # Display Courseware Generation app

elif selected == "Generate Assessment":
    assessment_generation = lazy_import_assessment()
    assessment_generation.app()

elif selected == "Check Documents":
    sup_doc = lazy_import_docs()
    sup_doc.app()

elif selected == "Generate Brochure v2":
    brochure_generation_v2 = lazy_import_brochure_v2()
    brochure_generation_v2.app()

elif selected == "Add Assessment to AP":
    annex_assessment_v2 = lazy_import_annex_v2()
    annex_assessment_v2.app()  # Display Annex Assessment app (local upload)

elif "Settings" in selected:
    settings = lazy_import_settings()
    settings.app()  # Display full Settings app

elif selected == "    ├ API & LLM Models":
    settings = lazy_import_settings()
    settings.llm_settings_app()  # Display only API & LLM Models page

elif selected == "    └ Company Management":
    settings = lazy_import_settings()
    settings.company_management_app()  # Display only Company Management page