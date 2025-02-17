# Courseware/utils/model_configs.py
import streamlit as st

# Retrieve API keys from Streamlit secrets
OPENAI_API_KEY = st.secrets['OPENAI_API_KEY']
DEEPSEEK_API_KEY = st.secrets['DEEPSEEK_API_KEY']
GEMINI_API_KEY = st.secrets['GEMINI_API_KEY']

# GPT-4o (Default)
default_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "gpt-4o",
        "api_key": OPENAI_API_KEY,
        "seed": 42,
        "temperature": 0.2,
    }
}

# GPT-4o-mini
gpt_4o_mini_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
        "seed": 42,
        "temperature": 0.2,
    }
}

# DeepSeek
deepseek_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "api_key": DEEPSEEK_API_KEY,
        "seed": 42,
        "temperature": 0.2,
        "model_info": {
            "family": "unknown",
            "function_calling": False,
            "json_output": False,
            "vision": False
        }
    }
}

# Gemini
gemini_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "gemini-2.0-flash-exp",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": GEMINI_API_KEY,
        "model_info": {
            "family": "unknown",
            "function_calling": False,
            "json_output": True,
            "vision": False
        }
    }
}

# Map user-friendly names to configs
MODEL_CHOICES = {
    "GPT-4o": default_config,
    "GPT-4o-mini": gpt_4o_mini_config,
    "DeepSeek": deepseek_config,
    "Gemini": gemini_config,
}

def get_model_config(choice: str) -> dict:
    """
    Return the chosen model config dict, or default_config if unknown.
    """
    return MODEL_CHOICES.get(choice, default_config)
