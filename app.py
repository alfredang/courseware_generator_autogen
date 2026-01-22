# app.py
import streamlit as st
from streamlit_option_menu import option_menu
from generate_ap_fg_lg_lp.utils.organizations import get_organizations, get_default_organization

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

# Custom CSS to increase sidebar width
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        min-width: 350px;
        max-width: 350px;
    }
    [data-testid="stSidebar"] > div:first-child {
        width: 350px;
    }
</style>
""", unsafe_allow_html=True)

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

        # Find Tertiary Infotech as default company
        default_company_idx = 0
        for i, name in enumerate(company_names):
            if "tertiary infotech" in name.lower():
                default_company_idx = i
                break

        # Use default on first load, then respect user selection
        if 'selected_company_idx' not in st.session_state:
            st.session_state['selected_company_idx'] = default_company_idx

        # Validate stored index to prevent out-of-range errors
        if st.session_state['selected_company_idx'] >= len(organizations):
            st.session_state['selected_company_idx'] = default_company_idx

        selected_company_idx = st.selectbox(
            "🏢 Select Company:",
            range(len(company_names)),
            format_func=lambda x: company_names[x],
            index=st.session_state['selected_company_idx']
        )

        # Store selection in session state
        st.session_state['selected_company_idx'] = selected_company_idx
        selected_company = organizations[selected_company_idx]
    else:
        selected_company = default_org
        st.session_state['selected_company_idx'] = 0

    # Store selected company in session state for other modules
    st.session_state['selected_company'] = selected_company

    # Model Selection
    st.markdown("---")
    from settings.api_manager import get_all_available_models
    all_models = get_all_available_models()
    model_names = list(all_models.keys())

    # Find default model index (DeepSeek-V3.1 or first available)
    default_model_idx = 0
    for i, name in enumerate(model_names):
        if "deepseek" in name.lower() and "v3" in name.lower():
            default_model_idx = i
            break

    # Use default on first load, then respect user selection
    if 'selected_model_idx' not in st.session_state:
        st.session_state['selected_model_idx'] = default_model_idx

    # Validate stored index
    if st.session_state['selected_model_idx'] >= len(model_names):
        st.session_state['selected_model_idx'] = default_model_idx

    selected_model_idx = st.selectbox(
        "🤖 Select Model:",
        range(len(model_names)),
        format_func=lambda x: model_names[x],
        index=st.session_state['selected_model_idx']
    )

    # Store selection in session state
    st.session_state['selected_model_idx'] = selected_model_idx
    st.session_state['selected_model'] = model_names[selected_model_idx]
    st.session_state['selected_model_config'] = all_models[model_names[selected_model_idx]]

    st.markdown("---")

    # Main features menu
    menu_options = [
        "Generate CP",
        "Generate AP/FG/LG/LP",
        "Generate Assessment",
        "Generate Brochure v2",
        "Add Assessment to AP",
        "Check Documents",
    ]

    menu_icons = [
        "filetype-doc",
        "file-earmark-richtext",
        "clipboard-check",
        "file-earmark-pdf",
        "folder-symlink",
        "search",
    ]

    selected = option_menu(
        "",  # Title of the sidebar
        menu_options,
        icons=menu_icons,
        menu_icon="boxes",  # Icon for the sidebar title
        default_index=0,  # Default selected item
    )

    # Separate Settings section
    st.markdown("---")
    st.markdown("##### Settings")

    settings_options = ["API & LLM Models", "Company Management"]
    settings_icons = ["cpu", "building"]

    settings_selected = option_menu(
        "",
        settings_options,
        icons=settings_icons,
        menu_icon="gear",
        default_index=None,
        key="settings_menu"
    )

    # If a settings option is selected, override main selection
    if settings_selected:
        selected = settings_selected

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

elif selected == "API & LLM Models":
    settings = lazy_import_settings()
    settings.llm_settings_app()  # Display only API & LLM Models page

elif selected == "Company Management":
    settings = lazy_import_settings()
    settings.company_management_app()  # Display only Company Management page