# Courseware AutoGen Codebase Documentation

This document provides a comprehensive overview of the `courseware_autogen 4` codebase, detailing the purpose and functionality of each file and module.

## 1. Project Overview
**Courseware AutoGen 4** is an AI-powered platform for automating the creation of workforce training documents. It leverages Large Language Models (LLMs) via **AutoGen** and **Streamlit** to generate:
- **Course Proposals (CP)**: Detailed course structures and justifications.
- **Assessment Plans (AP)**: Assessment strategies and matrices.
- **Learner Guides (LG)**: Educational content for students.
- **Lesson Plans (LP)**: Instructor guides for delivery.
- **Facilitator Guides (FG)**: Comprehensive guides for trainers.
- **Assessments**: Question papers (SAQ), Suggested Answers (WA), Presentation/Project (PP) briefs, and Case Studies (CS).
- **Brochures**: Information pamphlets derived from web content.

## 2. Top-Level Structure

### `app.py`
The main entry point for the Streamlit application.
- **Navigation**: Uses `streamlit_option_menu` to switch between modules.
- **Lazy Loading**: Imports modules (e.g., `generate_assessment`, `generate_cp`) only when selected to optimize startup time.
- **Company Context**: Manages the selected company in `st.session_state` (defaulting to "Tertiary Infotech") and displays the corresponding logo.

### `README.md`
The primary user guide.
- **Installation**: Instructions for `pip` and `uv` setup.
- **Configuration**: How to set API keys and secrets.
- **Usage**: Step-by-step guides for generating each document type.

## 3. Core Modules Deep Dive

### 3.1 Common Utilities (`common/`)
Shared resources used across the application.
- **`common.py`**: General utilities.
    - `parse_json_content(content)`: Robustly extracts JSON from LLM responses (handles markdown blocks).
    - `save_uploaded_file(uploaded_file)`: Saves Streamlit uploads to disk.
- **`company_manager.py`**: Handles multi-tenancy for company branding.
    - `get_company_template()`: finding company-specific templates or valid fallbacks.
    - `apply_company_branding()`: Injecting company details into documents.
- **`prompt_loader.py`**: Centralized prompt management system.
    - Loads `.txt` prompts from `prompts/`.
    - Supports variable substitution (`{{ variable }}`).
    - Caches prompts for performance.

### 3.2 Settings (`settings/`)
Configuration and API management.
- **`settings.py`**: The UI for the Settings page.
    - **API Keys**: Manage keys for OpenAI, Gemini, DeepSeek, etc.
    - **Models**: Add/Edit/Remove custom LLM models (via OpenRouter).
    - **Company**: CRUD operations for client companies (Logo, UEN, Address).
- **`api_manager.py`**: Backend logic for API keys and models.
    - Persists keys/models to `settings/config/` JSON files.
    - Dynamically updates `st.session_state`.

### 3.3 Course Proposal (`generate_cp/`)
Generates the foundational Course Proposal document.
- **`main.py`**: The orchestration engine.
    - Takes a TSC (Technical Skills Competency) document.
    - Runs a chain of AutoGen agents:
        1.  Inital Analysis (TSC Agent)
        2.  Information Extraction (Extraction Team)
        3.  Content Research (Research Team)
        4.  Validation (Course Validation Team)
- **`app.py`**: The Streamlit UI for CP generation.
    - Handles file uploads (TSC DOCX).
    - Toggles between "New CP" (Excel-based) and "Old CP" (Word-based).
- **`agents/`**: Specific AutoGen agent implementations.
    - `tsc_agent.py`: Analyzes the input TSC PDF/DOCX.
    - `extraction_team.py`: Extracts key parameters (Duration, Cost, TGS Code).

### 3.4 Courseware Suite (`generate_ap_fg_lg_lp/`)
Generates the core teaching materials based on the Course Proposal.
- **`courseware_generation.py`**: The main logic hub.
    - Parses the uploaded CP (Word or Excel).
    - Scrapes TGS data from MySkillsFuture if needed.
    - Orchestrates the generation of LG, AP, LP, and FG.
- **`utils/`**: Specialized generators.
    - `agentic_LG.py`: Generates Learner Guides using content expansion agents.
    - `agentic_AP.py`: Creates Assessment Plans, mapping assessment methods to learning outcomes.
    - `timetable_generator.py`: Calculates course schedules and durations.

### 3.5 Assessments (`generate_assessment/`)
Creates the actual test papers.
- **`assessment_generation.py`**: The UI and Controller.
    - Inputs: Facilitator Guide (FG) and Slides (PDF).
    - Logic: Parses FG to understand what to test. Generates questions matching the LO (Learning Outcome) requirements.
- **`utils/`**:
    - `agentic_SAQ.py`: Agents specifically for Short Answer Questions.
    - `agentic_PP.py`: Agents for Project/Presentation assessments.
    - `Templates/`: `.docx` templates for question/answer papers.

### 3.6 Brochure (`generate_brochure_v2/`)
Generates marketing brochures.
- **`brochure_generation_v2.py`**:
    - **Web Scraping**: Uses Selenium/Browserless to scrape course details from a URL.
    - **Template Filling**: Populates a brochure template with course title, fees, funding, and modules.
    - **PDF Generation**: Converts the result to PDF.

### 3.7 Document Verification (`check_documents/`)
A compliance tool.
- **`sup_doc.py`**:
    - Reads uploaded PDFs/Images (NRIC, Company content).
    - Extracts entities (Name, UEN, ID) using Gemini.
    - Matches against a Google Sheet (SSG API data) to verify trainee funding eligibility.

### 3.8 Tools (`add_assessment_to_ap/`)
- **`annex_assessment_v2.py`**: A utility to physically merge generated Assessment Question/Answer papers into the main Assessment Plan DOCX as Annexes.

## 4. Key Architectures

### Lazy Loading
Streamlit apps can be slow if everything is imported at start. This project uses local imports inside `app()` functions.
*Example*: `generate_cp` is only imported when the user clicks the "Course Proposal" menu item.

### Agentic Workflow (AutoGen)
Complex tasks are broken down into agents.
- **UserProxy**: Acts as the requester.
- **Assistant**: The LLM that generates content.
- **GroupChat**: Coordinates multiple experts (e.g., a "Research Team" and a "Writer").

### Data Handling
- **Pydantic**: Used extensively to force LLMs to output structured JSON data (e.g., `CourseData` model).
- **Jinja2 / DocxTpl**: Used to render extracted data into Word templates, ensuring consistent formatting.

### Configuration
- **Secrets**: API keys are stored in `.streamlit/secrets.toml` or managed via the UI (saved to local JSON in `settings/config/`).
- **Model Abstraction**: The system supports OpenAI, Gemini, Anthropic, etc., abstracted via `api_manager.py` so the rest of the code just asks for a "completion".
