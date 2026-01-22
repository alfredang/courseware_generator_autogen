"""
Dynamic API Key and Model Management

This module handles dynamic storage and retrieval of API keys and custom LLM models.
Keys are stored in session state and can be managed through the Settings UI.
"""

import streamlit as st
import json
import os
from typing import Dict, Any, List

# File to store persistent API keys (outside of session state)
API_KEYS_FILE = "settings/config/api_keys.json"

def load_api_keys() -> Dict[str, str]:
    """Load API keys from file or session state"""
    # First try session state
    if 'api_keys' in st.session_state:
        return st.session_state['api_keys']
    
    # Then try file
    if os.path.exists(API_KEYS_FILE):
        try:
            with open(API_KEYS_FILE, 'r') as f:
                keys = json.load(f)
                st.session_state['api_keys'] = keys
                return keys
        except Exception as e:
            print(f"Error loading API keys from file: {e}")
    
    # Fallback to secrets.toml
    fallback_keys = {
        "OPENAI_API_KEY": st.secrets.get("OPENAI_API_KEY", ""),
        "DEEPSEEK_API_KEY": st.secrets.get("DEEPSEEK_API_KEY", ""),
        "GEMINI_API_KEY": st.secrets.get("GEMINI_API_KEY", ""),
        "OPENROUTER_API_KEY": st.secrets.get("OPENROUTER_API_KEY", ""),
        "GROQ_API_KEY": st.secrets.get("GROQ_API_KEY", ""),
        "GROK_API_KEY": st.secrets.get("GROK_API_KEY", "")
    }
    st.session_state['api_keys'] = fallback_keys
    return fallback_keys

def save_api_keys(keys: Dict[str, str]) -> bool:
    """Save API keys to session state and file"""
    try:
        # Save to session state
        st.session_state['api_keys'] = keys
        
        # Save to file for persistence
        os.makedirs(os.path.dirname(API_KEYS_FILE), exist_ok=True)
        with open(API_KEYS_FILE, 'w') as f:
            json.dump(keys, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving API keys: {e}")
        return False

def get_api_key(provider: str) -> str:
    """Get API key for specific provider"""
    keys = load_api_keys()
    key_name = f"{provider.upper()}_API_KEY"
    return keys.get(key_name, "")

def delete_api_key(key_name: str) -> bool:
    """Delete an API key"""
    try:
        keys = load_api_keys()
        if key_name in keys:
            del keys[key_name]
            return save_api_keys(keys)
        else:
            st.warning(f"API key '{key_name}' not found!")
            return False
    except Exception as e:
        st.error(f"Error deleting API key: {e}")
        return False

def load_custom_models() -> List[Dict[str, Any]]:
    """Load custom LLM models from session state or file"""
    if 'custom_models' in st.session_state:
        return st.session_state['custom_models']
    
    # Try loading from file
    models_file = "settings/config/custom_models.json"
    if os.path.exists(models_file):
        try:
            with open(models_file, 'r') as f:
                models = json.load(f)
                st.session_state['custom_models'] = models
                return models
        except Exception as e:
            print(f"Error loading custom models: {e}")
    
    # Default empty list
    st.session_state['custom_models'] = []
    return []

def save_custom_models(models: List[Dict[str, Any]]) -> bool:
    """Save custom models to session state and file"""
    try:
        st.session_state['custom_models'] = models
        
        # Save to file
        models_file = "settings/config/custom_models.json"
        os.makedirs(os.path.dirname(models_file), exist_ok=True)
        with open(models_file, 'w') as f:
            json.dump(models, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving custom models: {e}")
        return False

def add_custom_model(name: str, provider: str, model_id: str, base_url: str = "", temperature: float = 0.2, api_provider: str = "", custom_api_key: str = "") -> bool:
    """Add a new custom model"""
    models = load_custom_models()

    # Check if exact same model display name already exists
    for model in models:
        if model['name'] == name:
            st.error(f"❌ Model Display Name '{name}' already exists!")
            st.error("Please use a different name to distinguish between models.")
            st.info("💡 **Naming Examples:**")
            st.info("• 'GPT-4o', 'GPT-4 Turbo', 'GPT-4o Mini'")
            st.info("• 'Anthropic Sonnet', 'Anthropic Haiku'")
            st.info("• 'Gemini Pro', 'Gemini Flash', 'Gemini 2.0'")
            return False

    # Determine API key to use
    if api_provider == "CUSTOM" and custom_api_key:
        api_key = custom_api_key
    elif api_provider:
        # Use the selected API provider
        api_key = get_api_key(api_provider)
    else:
        # Fallback to automatic mapping
        api_key = get_api_key(provider.replace("ChatCompletionClient", "").replace("OpenAI", "OPENAI"))

    new_model = {
        "name": name,
        "provider": provider,
        "config": {
            "model": model_id,
            "api_key": api_key,
            "temperature": temperature
        }
    }
    
    if base_url:
        new_model["config"]["base_url"] = base_url
    
    models.append(new_model)
    return save_custom_models(models)

def remove_custom_model(name: str) -> bool:
    """Remove a custom model"""
    models = load_custom_models()
    models = [m for m in models if m['name'] != name]
    return save_custom_models(models)

def get_all_available_models() -> Dict[str, Dict[str, Any]]:
    """Get all available models (built-in + custom) with current API keys"""
    from settings.model_configs import MODEL_CHOICES
    
    # Get current API keys
    current_keys = load_api_keys()
    
    # Update built-in models with current API keys
    updated_models = {}
    for name, config in MODEL_CHOICES.items():
        # Create a copy to avoid modifying the original
        updated_config = json.loads(json.dumps(config))
        
        # Update API key based on model type and base_url
        base_url = config["config"].get("base_url", "").lower()
        model_name = config["config"]["model"].lower()
        
        # Order matters - check more specific URLs first
        if "generativelanguage.googleapis.com" in base_url or "gemini" in model_name:
            updated_config["config"]["api_key"] = current_keys.get("GEMINI_API_KEY", "")
        elif "openrouter" in base_url:
            updated_config["config"]["api_key"] = current_keys.get("OPENROUTER_API_KEY", "")
        elif "groq" in base_url:
            updated_config["config"]["api_key"] = current_keys.get("GROQ_API_KEY", "")
        elif "x.ai" in base_url or "grok" in model_name:
            updated_config["config"]["api_key"] = current_keys.get("GROK_API_KEY", "")
        elif "deepseek" in base_url or ("deepseek" in model_name and "openrouter" not in base_url):
            updated_config["config"]["api_key"] = current_keys.get("DEEPSEEK_API_KEY", "")
        elif "openai" in base_url or "gpt" in model_name or base_url == "":
            updated_config["config"]["api_key"] = current_keys.get("OPENAI_API_KEY", "")
        else:
            # Default fallback
            updated_config["config"]["api_key"] = current_keys.get("OPENAI_API_KEY", "")
        
        updated_models[name] = updated_config
    
    # Add custom models
    custom_models = load_custom_models()
    for model in custom_models:
        updated_models[model["name"]] = model
    
    return updated_models

def initialize_api_system():
    """Initialize the API system on app startup"""
    # Load API keys into session state
    load_api_keys()
    
    # Load custom models into session state
    load_custom_models()