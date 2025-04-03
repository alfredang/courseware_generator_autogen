"""
File: model_configs.py

===============================================================================
Model Configurations Module
===============================================================================
Description:
    This module defines and manages configuration settings for various AI models used in the
    Courseware system. It retrieves the necessary API keys from Streamlit secrets and sets up
    configuration dictionaries for supported models including Gemini-Pro-2.5-Exp-03-25 (default),
    GPT-4o, GPT-4o-mini, and DeepSeek-V3. Each configuration dictionary includes parameters such
    as the model name, API key, base URL, temperature, seed, response format, and additional model-specific
    settings.

Main Functionalities:
    • Defines configuration dictionaries for supported AI models:
          - Gemini-Pro-2.5-Exp-03-25 (default)
          - GPT-4o
          - GPT-4o-mini
          - DeepSeek-V3
    • Provides a mapping (MODEL_CHOICES) from user-friendly model names to their respective configuration dictionaries.
    • Implements get_model_config(choice: str) to retrieve the configuration for a specified model, defaulting
      to the Gemini configuration if the provided choice is not found.

Dependencies:
    - Streamlit: Used to access API keys stored in st.secrets.

Usage:
    - Ensure that the required API keys (OPENAI_API_KEY, DEEPSEEK_API_KEY, GEMINI_API_KEY) are set in st.secrets.
    - Import and call get_model_config() to obtain the configuration for a desired model.
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
            "vision": False
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
            "vision": False
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
    Retrieves the configuration dictionary for the specified AI model.

    This function returns the configuration settings for a selected model 
    from the `MODEL_CHOICES` dictionary. If the model is not found, it 
    defaults to the Gemini-Flash-2.0-Exp configuration.

    Args:
        choice (str): 
            The name of the AI model as selected by the user.

    Returns:
        dict: 
            A dictionary containing the model's configuration settings, 
            including model type, API key, response format, and additional parameters.
    """
    return MODEL_CHOICES.get(choice, default_config)
