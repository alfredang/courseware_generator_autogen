from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from model_configs import get_model_config
from autogen_core.models import ChatCompletionClient


def tsc_team_task(tsc_data):
    tsc_task = f"""
    1. Parse data from the following JSON file: {tsc_data}
    2. Return a full JSON object with all the extracted data according to the schema.
    """
    return tsc_task

def create_tsc_agent(tsc_data, model_choice: str) -> RoundRobinGroupChat:
    chosen_config = get_model_config(model_choice)
    model_client = ChatCompletionClient.load_component(chosen_config)

    tsc_parser_agent_message = f"""
        You are to parse and extract the given TSC form into the schema as specified below.
        The requirements are as follows:
        1. Ensure that the LOs (Learning Outcomes) are mapped.
        2. Ensure that the K (Knowledge) factors are mapped to the LOs.
        3. Ensure that the A (Ability) are mapped to the LOs.
        4. Return a full JSON object with all the extracted data according to the schema.

        An example JSON schema looks like this, with the LUs as a key-value pair:
        {{
        
            "LU1: Git and GitHub Fundamentals (A1, A2)": {{
            "LO": "LO1: Analyze Github components and coordinate release scheduling with collaborators to align processes.",
            "Abilities": {{
                "A1": "Analyse release components",
                "A2": "Coordinate with relevant stakeholders on release scheduling to align release processes and procedures"
            }},
            "Knowledge": {{}}
            }},
            "LU2: GitHub Repository Management (K1, A3)": {{
            "LO": "LO2: Select appropriate Git scripts for integrating and deploying software products.",
            "Abilities": {{
                "A3": "Select appropriate scripts and tools for integrating and deploying software products"
            }},
            "Knowledge": {{
                "K1": "Types and usage of scripts and tools for integrating and deploying software products"
            }}
            }},
            "LU3: Collaborative Workflows on GitHub (K2, K3, A4, A5)": {{
            "LO": "LO3: Configure software products and deploy releases using Git configuration tests.",
            "Abilities": {{
                "A4": "Configure software products to integrate and deploy software releases to various platforms",
                "A5": "Execute configuration tests on platform specific versions of software products in line with testing procedures"
            }},
            "Knowledge": {{
                "K2": "Software configuration procedures",
                "K3": "Configuration tests and their purposes"
            }}
            }},
            "LU4: Modern GitHub Development Practices (K4, A6)": {{
            "LO": "LO4: Diagnose issues identified during Github configuration testing by interpreting configuration test results.",
            "Abilities": {{
                "A6": "Diagnose issues surfaced from configuration testing"
            }},
            "Knowledge": {{
                "K4": "Interpretation of configuration test results"
            }}
            }},
            "LU5: GitHub Project Automation (K5, A7)": {{
            "LO": "LO5: Identify potential improvements to the software configuration, deployment processes, and code elements.",
            "Abilities": {{
                "A7": "Identify potential improvements and modifications to the software configuration and deployment process or the software code"
            }},
            "Knowledge": {{
                "K5": "Elements of the software configuration and deployment process"
            }}
            }},
            "LU6: GitHub Security and Administration (A8)": {{
            "LO": "LO6: Implement modifications to software products and processes for improved functionality.",
            "Abilities": {{
                "A8": "Implement modifications to platform-specific software products and processes"
            }},
            "Knowledge": {{}}
            }}
        
        }}
        """

    tsc_prepper_message = f"""
        You are to parse the response from the previous agent and ensure that the extracted data is correctly mapped to the LUs.
        You are to ensure that the response is in valid JSON format in order to prevent JSON parsing errors downstream.
        You are to return the parsed data (with modifications - if any) in your response as a full JSON object according to the schema.

        An example JSON schema looks like this, with the LUs as a key-value pair:
        {{
        
            "LU1: Git and GitHub Fundamentals (A1, A2)": {{
            "LO": "LO1: Analyze Github components and coordinate release scheduling with collaborators to align processes.",
            "Abilities": {{
                "A1": "Analyse release components",
                "A2": "Coordinate with relevant stakeholders on release scheduling to align release processes and procedures"
            }},
            "Knowledge": {{}}
            }},
            "LU2: GitHub Repository Management (K1, A3)": {{
            "LO": "LO2: Select appropriate Git scripts for integrating and deploying software products.",
            "Abilities": {{
                "A3": "Select appropriate scripts and tools for integrating and deploying software products"
            }},
            "Knowledge": {{
                "K1": "Types and usage of scripts and tools for integrating and deploying software products"
            }}
            }},
            "LU3: Collaborative Workflows on GitHub (K2, K3, A4, A5)": {{
            "LO": "LO3: Configure software products and deploy releases using Git configuration tests.",
            "Abilities": {{
                "A4": "Configure software products to integrate and deploy software releases to various platforms",
                "A5": "Execute configuration tests on platform specific versions of software products in line with testing procedures"
            }},
            "Knowledge": {{
                "K2": "Software configuration procedures",
                "K3": "Configuration tests and their purposes"
            }}
            }},
            "LU4: Modern GitHub Development Practices (K4, A6)": {{
            "LO": "LO4: Diagnose issues identified during Github configuration testing by interpreting configuration test results.",
            "Abilities": {{
                "A6": "Diagnose issues surfaced from configuration testing"
            }},
            "Knowledge": {{
                "K4": "Interpretation of configuration test results"
            }}
            }},
            "LU5: GitHub Project Automation (K5, A7)": {{
            "LO": "LO5: Identify potential improvements to the software configuration, deployment processes, and code elements.",
            "Abilities": {{
                "A7": "Identify potential improvements and modifications to the software configuration and deployment process or the software code"
            }},
            "Knowledge": {{
                "K5": "Elements of the software configuration and deployment process"
            }}
            }},
            "LU6: GitHub Security and Administration (A8)": {{
            "LO": "LO6: Implement modifications to software products and processes for improved functionality.",
            "Abilities": {{
                "A8": "Implement modifications to platform-specific software products and processes"
            }},
            "Knowledge": {{}}
            }}
        
        }}

        """

    tsc_parser_agent = AssistantAgent(
        name="tsc_parser_agent",
        model_client=model_client,
        system_message=tsc_parser_agent_message,
    )

    tsc_prepper_agent = AssistantAgent(
        name="tsc_prepper_agent",
        model_client=model_client,
        system_message=tsc_parser_agent_message,
    )

    tsc_agent_response = RoundRobinGroupChat([tsc_prepper_agent, tsc_parser_agent], max_turns=2)

    return tsc_agent_response