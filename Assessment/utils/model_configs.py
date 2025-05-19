"""
File: model_configs.py

===============================================================================
Model Configurations Module
===============================================================================
Description:
    This module defines and manages model configurations for the Courseware system.
    It retrieves necessary API keys from Streamlit secrets and constructs configuration
    dictionaries for different language models including Gemini-Pro-2.5, GPT-4o, GPT-4o-mini,
    and DeepSeek-V3. Each configuration specifies parameters such as the model name, API key,
    base URL, temperature, seed, and additional model-specific settings.

Main Functionalities:
    • Defines configuration dictionaries for supported models:
          - Gemini-Pro-2.5-Exp-03-25 (default)
          - GPT-4o
          - GPT-4o-mini
          - DeepSeek-V3
    • Provides a mapping (MODEL_CHOICES) from user-friendly model names to their corresponding
      configuration dictionaries.
    • Implements get_model_config(choice: str) to return the configuration dictionary for a given
      model choice, defaulting to the Gemini-Pro configuration if the choice is unknown.

Dependencies:
    - Streamlit: Utilized to access API keys from st.secrets.

Usage:
    - Ensure that the required API keys (OPENAI_API_KEY, DEEPSEEK_API_KEY, GEMINI_API_KEY) are set in
      st.secrets.
    - Import and call the get_model_config function to retrieve the desired model configuration.
      Example:
          from Courseware.utils.model_configs import get_model_config
          config = get_model_config("GPT-4o-mini")

Author:
    Derrick Lim
Date:
    3 March 2025
===============================================================================
"""

import streamlit as st

# Retrieve API keys from Streamlit secrets
OPENAI_API_KEY = st.secrets['OPENAI_API_KEY']
DEEPSEEK_API_KEY = st.secrets['DEEPSEEK_API_KEY']
GEMINI_API_KEY = st.secrets['GEMINI_API_KEY']

# Gemini (Default)
default_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "gemini-2.5-pro-exp-03-25",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": GEMINI_API_KEY,
        "model_info": {
            "family": "unknown",
            "function_calling": False,
            "json_output": True,
            "vision": False,
            "structured_output": True
        },
        "llama_name": "gemini-2.0-flash-001",
        "text_embedding_model": "model/text-embedding-005"
    }
}

# GPT-4o
gpt_4o_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "gpt-4o",
        "api_key": OPENAI_API_KEY,
        "seed": 42,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "llama_name": "openai-gpt4o",
        "text_embedding_model": "text-embedding-3-large",
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
        "response_format": {"type": "json_object"},
        "llama_name": "openai-gpt-4o-mini",
        "text_embedding_model": "text-embedding-3-large",
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
            "vision": False,
            "structured_output": True
        }
    }
    # Deepseek does not supported in multimodal mode
    # Deepseek does not provide text embedding models
}
# Map user-friendly names to configs
MODEL_CHOICES = {
    "Gemini-Pro-2.5-Exp-03-25": default_config,
    "GPT-4o": gpt_4o_config,
    "GPT-4o-mini": gpt_4o_mini_config,
    "DeepSeek-V3": deepseek_config,
}

def get_model_config(choice: str) -> dict:
    """
    Return the chosen model config dict, or default_config if unknown.
    """
    return MODEL_CHOICES.get(choice, default_config)
