from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from CourseProposal.model_configs import get_model_config
from autogen_core.models import ChatCompletionClient


def tsc_agent_task(tsc_data):
    tsc_task = f"""
    1. Parse data from the following JSON file: {tsc_data}
    2. Ensure that the LOs (Learning Outcomes) are mapped.
    3. Ensure that the K (Knowledge) factors are mapped to the LOs.
    4. Ensure that the A (Ability) are mapped to the LOs.
    5. Ensure that the Course Title is mapped.
    6. Return a full JSON object with all the extracted data according to the schema.
    """
    return tsc_task

def create_tsc_agent(tsc_data, model_choice: str) -> RoundRobinGroupChat:
    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)

    tsc_parser_agent_message = f"""
        You are to parse and correct spelling mistakes from {tsc_data}:
        The requirements are as follows:
        1. Ensure that the LOs (Learning Outcomes) are mapped.
        2. Ensure that the K (Knowledge) factors are mapped to the LOs.
        3. Ensure that the A (Ability) are mapped to the LOs.
        4. Ensure that the Course Title is mapped.

        An example JSON schema looks like this, with the LUs as a key-value pair:
        {{
        "TSC_Form": {{
            "Learning Outcomes": [
                "LO1: Establish high-level structures and frameworks for Kubernetes solutions using appropriate processes and tools.",
                "LO2: Align technical, functional, and service requirements within Kubernetes-based solution architectures.",
                "LO3: Coordinate multiple Kubernetes solution components to ensure compatibility and meet design framework goals.",
                "LO4: Articulate the value of Kubernetes solutions by addressing coding standards, scalability, and reusability.",
                "LO5: Establish monitoring and testing processes to validate Kubernetes architectures against business requirements."
            ],
            "Knowledge": [
                "K1: Process for refining solution architecture",
                "K2: Applications of tools and modelling techniques for creation of solution architecture",
                "K3: Technical, functional and service considerations",
                "K4: Considerations for multiple aspects of the overall solution including performance, security, latency and other relevant aspect for the solution",
                "K5: Standards for coding, scalability, integration and reusability",
                "K6: Compatibility among multiple solution architecture components and design activities",
                "K7: Techniques to measure a solution's value-add"
            ],
            "Ability": [
                "A1: Establish high level structures and frameworks to guide the development of IT solutions incorporating various processes, hardware and software components",
                "A2: Determine relevant design tools or modelling techniques required to develop a solution architecture and blueprint",
                "A3: Align requirements of various internal and external stakeholders, as well as technical, functional and service requirements within a solution architecture",
                "A4: Coordinate multiple solution architecture components and design activities, ensuring consistency and compatibility within a target framework",
                "A5: Articulate value added by the solution to the business needs",
                "A6: Establish processes to regularly monitor, test and review solution architecture against business requirements"
            ],
            "Knowledge and Ability Mapping": {
            "KA1": [
                "K1",
                "K2",
                "A1",
                "A2"
            ],
            "KA2": [
                "K3",
                "A3"
            ],
            "KA3": [
                "K4",
                "K6",
                "A4"
            ],
            "KA4": [
                "K5",
                "A5"
            ],
            "KA5": [
                "K7",
                "A6"
            ]
        }
    },
        }}

        }}
        """

    tsc_parser_agent = AssistantAgent(
        name="tsc_agent",
        model_client=model_client,
        system_message=tsc_parser_agent_message,
    )

    tsc_agent_response = RoundRobinGroupChat([tsc_parser_agent], max_turns=1)

    return tsc_agent_response