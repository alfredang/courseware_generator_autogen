# agentic-workflow-cp

This project is a Python-based system designed to automate the extraction, transformation, and mapping of data into JSON files using AI-powered agents. It primarily utilizes the agentchat framework, initialising GPT and LLaMa models, to interactively process and organize data. The system handles multiple JSON inputs and outputs, ensuring data integrity and consistent formatting across the pipeline.

## Table of Contents

- [Installation](#installation)
- [Docker Setup](#docker-setup)
- [Usage](#usage)
  - [Executing JSON Document Replacement](#executing-json-document-replacement)
  - [JSON Content Extraction](#json-content-extraction)
  - [Term Mapping](#term-mapping)
  - [Interpretation and Final Mapping](#interpretation-and-final-mapping)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Installation

1. Clone this repository:
    ```bash
    git clone https://github.com/tertiaryinfotech/agentic-workflow-cp
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    
    Upgrade requirements
    pip install --upgrade -r requirements.txt
    ```

3. Set up environment variables by creating a `.env` file in the project root with the following keys:
    ```env
    OPENAI_API_KEY=your_openai_api_key
    GROQ_API_KEY=your_groq_api_key
    ```

## Docker Setup

To run this project in a Docker container, follow these steps:

1. **Install Docker Desktop**
   - Download and install Docker Desktop from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).
   - Ensure Docker Desktop is running before proceeding.
   - Make sure your project directory is accessible to Docker (check Docker Desktop's file sharing settings on Windows/Mac).

2. **Set up environment variables**
   - Ensure you have a `.env` file in the project root (see Installation step 3).
   - Alternatively, you can set environment variables directly in the `docker-compose.yml` or pass them via the command line.

3. **Build and run the container**
   - Using Docker Compose (recommended):
     ```bash
     docker-compose up --build
     ```
   - Or, using the provided batch scripts (on Windows):
     - `compose_build.bat` (builds and runs, starts Docker Desktop if needed)
     - `run_docker.bat` (runs without rebuilding)
   - **Note:**
     - You may need to edit the Docker pathway in the `.bat` files (`compose_build.bat` and `run_docker.bat`) to match your local project directory and Docker installation location.
     - Ensure that the path to `docker.exe` is included in your Windows environment `PATH` variable. This allows you to run Docker commands from any terminal window. If not, add the directory containing `docker.exe` (e.g., `C:\Program Files\Docker\Docker\resources\bin`) to your system `PATH`.

4. **Access the application**
   - The app will be available at [http://localhost:8502](http://localhost:8502) by default.

5. **Environment variables in Docker**
   - The container will automatically use the `.env` file if present in the project root.
   - For custom setups, you can add an `env_file` section to `docker-compose.yml` or use the `-e` flag with `docker run`.

## Executing Workflow Automation

To execute the `courseware_generation.py` script which handles the end-to-end content generation and final processing of the JSON document, run:
```bash
python courseware_generation.py
```

TSC Formatting to take into account:
LUs must be present on top of their respective group of topics.
Topics and LUs must follow this labelling convention:
Course Level and proficiency Level must be present 
eg. LU1: xxxx (K1, K2, A1, A2)
eg. Topic 1: xxxxx (K1, A1)

The colon character ( : ) is essential for the regex pattern in the code to detect what is needed for mapping, do not miss this out!

![plot](./agentic_chat_workflow.png)

## Notes
- **Railway deployment has been disabled**: This project is no longer deployed or maintained on Railway. Please use local or other cloud environments for running the workflow.
- **Recommended Model**: For best cost-effectiveness, use DeepSeek v3 as the default model. It is both cheap and efficient for most tasks.

## Roadmap
- [x] Parsing Function
- [x] Json Scanner Function
- [x] Json Replacement Function
- [x] Sequential Agentic Chat Framework
- [x] TCS Input Template
- [x] CP Output Template
- [x] 30% Task Accuracy
- [x] 50% Task Accuracy
- [x] Data Structure Sorting & Scanning Algorithm
- [x] 70% Task Accuracy
- [x] 90% Task Accuracy
- [x] Specialisation of Workflow Agents
- [x] Inclusion of Validator Agent
- [x] Asynchronous Agentic Chat Framework
- [x] Simple UI for easy usage (Possibly Gradio UI)

