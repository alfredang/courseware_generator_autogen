from docxtpl import DocxTemplate
import os
import tempfile

def generate_documents(context: dict, type: int) -> dict:
    """
    Generate the question paper and answer paper for the given context and type.

    Parameters:
    - context (dict): The data for the assessment (course title, type, questions, etc.).
    - type (int): The assessment type (1 for Ability-based, 2 for Knowledge-based).

    Returns:
    - dict: Paths to the generated documents (question and answer papers).
    """
    # Define template paths
    TEMPLATES = {
        1: {
            "ANSWER": r"C:\Users\dljh1\Documents\courseware_autogen\Assessment\Templates\(Template) Answer to A Assessment - Course Title - v1.docx",
            "QUESTION": r"C:\Users\dljh1\Documents\courseware_autogen\Assessment\Templates\(Template) A Assessment - Course Title - v1.docx"
        },
        2: {
            "ANSWER": r"C:\Users\dljh1\Documents\courseware_autogen\Assessment\Templates\(Template) Answer to K Assessment - Course Title - v1.docx",
            "QUESTION": r"C:\Users\dljh1\Documents\courseware_autogen\Assessment\Templates\(Template) WA (SAQ) - Course Title - v1.docx"
        },
    }


    # Validate type
    if type not in TEMPLATES:
        raise ValueError("Invalid type. Must be 1 (Ability-based) or 2 (Knowledge-based).")

    # Load templates
    answer_template_path = TEMPLATES[type]["ANSWER"]
    question_template_path = TEMPLATES[type]["QUESTION"]
    answer_doc = DocxTemplate(answer_template_path)
    question_doc = DocxTemplate(question_template_path)

    # Prepare context for the question paper by excluding answers
    question_context = context.copy()
    for question in question_context.get("questions", []):
        question.pop("answer", None)  # Remove answers from the question context

    # Render both templates
    answer_doc.render(context)
    question_doc.render(question_context)

    # Save the documents to temporary files
    temp_files = {}
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        answer_doc.save(tmp_file.name)
        temp_files["ANSWER"] = tmp_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        question_doc.save(tmp_file.name)
        temp_files["QUESTION"] = tmp_file.name

    return temp_files  # Return paths to the generated documents


# Example Usage
if __name__ == "__main__":
    # Example context for testing
    context = [
        {
            "course_title": "Mastering Multi-Agent AI Workflows and Agentic Process Automation (APA)",
            "type": "Written Assessment (SAQ)",
            "code": "SAQ",
            "duration": "1 hr",
            "scenario": "",
            "questions": [
                {
                    "question_statement": "Your company is planning to develop a multi-agent AI system to improve its hiring process. As part of the project, the team needs to explore the use of different types of AI agents for various tasks, such as filtering resumes, communicating with candidates, and gathering candidate information. Analyze and identify three types of AI agents that would be suitable for this purpose. Explain how each agent contributes to the hiring process.", 
                    "know_abil_no": "K1", 
                    "answer": "Search the internet: An AI agent that gathers information about potential candidates from public domains, such as professional networks or websites.\n Read websites: An AI agent that screens candidate profiles on various job boards or professional networking sites\n Read resumes: An AI agent that reviews and categorizes resumes based on predefined criteria.\n Perform RAG: An AI agent that retrieves, augments, and generates data to help make informed decisions about candidate selection."
                },
                {
                    "question_statement": "A new AI-based decision support system is being developed to assist customer service agents in providing accurate and timely responses. The system uses agentic components like memory, tool calling, and planning to enhance its decision-making capability. Analyze these three components and explain their roles in ensuring the effectiveness of the system.", 
                    "know_abil_no": "K2", 
                    "answer": "Tool calling: The system's ability to use external tools (like knowledge bases or APIs) helps in providing accurate information to customers.\n Action taking: The system triggers specific actions, such as sending responses or escalating issues, based on the analysis of customer queries.\n Memory: Memory allows the system to retain information from past interactions, ensuring continuity and context in customer conversations.\n Planning: Planning involves creating steps and strategies to resolve customer issues effectively, which ensures high-fidelity decision-making."
                },
                {
                    "question_statement": "A retail company is using the ReAct Framework to improve its recommendation engine, which suggests products to customers based on their browsing and purchasing behavior. Analyze how the ReAct Framework functions in this scenario and discuss the methods you would use to evaluate its effectiveness.", 
                    "know_abil_no": "K3", 
                    "answer": "Thought: The recommendation engine continuously processes customer behavior data to refine its decision-making process.\nAction: The engine generates and displays product recommendations to customers.\nObservation: The system monitors customer interactions with the recommendations to assess engagement and adjust the recommendations accordingly.\nEvaluation methods could include metrics like conversion rates, click-through rates, and customer feedback."
                },
                {
                    "question_statement": "You are tasked with developing a new AI-driven workflow automation tool for a software development team using LangGraph. To ensure the tool’s design meets the team’s requirements, analyze the steps involved in creating the LangGraph and explain how each step contributes to building an efficient workflow.", 
                    "know_abil_no": "K4", 
                    "answer": "Initialize the model and tools: Set up the AI models and tools required to perform specific tasks.\nInitialize graph with state: Define the initial state of the workflow, including parameters and variables.\nDefine graph nodes: Create nodes representing different tasks or decision points within the workflow.\nDefine entry point and graph edges: Specify starting points and the connections between different nodes.\nCompile the graph: Validate the graph's structure to ensure all nodes and connections are correctly defined.\nExecute the graph: Run the workflow and monitor its performance."
                },
                {
                    "question_statement": "A technology startup is managing multiple AI agents for different projects. The team needs a software solution to efficiently handle and monitor the performance of these agents. Analyze and suggest two software tools suitable for managing multiple AI agents and justify your choices.", 
                    "know_abil_no": "K5", 
                    "answer": "LangGraph: Suitable for managing complex AI workflows by providing a graphical interface to visualize and control agent interactions\nAutogen: Helps automate the generation and testing of AI models, reducing the time and effort required for model development.\nCrew AI: Facilitates the deployment, monitoring, and scaling of AI agents, making it easier to handle multiple projects concurrently."
                },
                {
                    "question_statement": "A content management company is looking to integrate AI to enhance its content delivery and user engagement strategies. They are considering the use of Retrieval-Augmented Generation (RAG) techniques. Analyze three potential use cases for RAG in this context and explain how they would benefit the company's operations.", 
                    "know_abil_no": "K6", 
                    "answer": "Content Recommendation: RAG can be used to provide personalized content recommendations based on user preferences and behavior.\nInformation Retrieval: It can efficiently retrieve relevant information from vast datasets to support content creation and curation.\nData Enrichment: RAG can augment existing content with additional data and context, improving the overall quality and relevance of the content delivered to users."
                },
            ],
        },
    ]


    # Generate documents for Ability-based assessment
    files = []
    for item in context:
        files = generate_documents(item, type=item["format"])
        print(f"Assessment Type: {item['code']}Documents generated:", files)
