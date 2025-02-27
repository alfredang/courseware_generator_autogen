# config_loader.py
import os
import yaml
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import logging

logging.basicConfig(level=logging.INFO)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)

def load_env():
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path, override=True)

def initialize_llm(gemini_api_key, llm_model):
    """Initializes the Gemini LLM."""
    return Gemini(api_key=gemini_api_key, model_name=llm_model)

def initialize_embedding_model(embedding_model, gemini_api_key=None):
    """Initializes the embedding model."""
    if embedding_model == "gemini": # Assuming "gemini" is a value in your config.yaml if you intend to use Gemini embeddings
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY must be provided when using Gemini Embedding Model.")
        return GeminiEmbedding(model_name="models/embedding-001", api_key=gemini_api_key) # or EMBEDDING_MODEL if you use a specific model name from config
    elif embedding_model == "huggingface":
        return HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5") # or EMBEDDING_MODEL if you intend to configure it
    else:
        raise ValueError(f"Unsupported embedding model type: {embedding_model}")


def setup_logging():
    """Sets up basic logging."""
    logging.basicConfig(level=logging.INFO)

def setup_settings(llm):
    """Sets up LlamaIndex settings."""
    Settings.llm = llm

def load_shared_resources():
    """Loads configurations, environment variables, and initializes shared resources."""
    config = load_config()
    load_env()
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    embedding_model_name = config.get("embedding_model") # get embedding model type (gemini/huggingface)
    llm_model_name = config.get("llm_model")

    llm = initialize_llm(gemini_api_key, llm_model_name)
    embed_model = initialize_embedding_model(embedding_model_name, gemini_api_key) # pass api_key only if needed

    setup_settings(llm) # Apply settings to llama-index
    setup_logging()

    return config, embed_model


if __name__ == "__main__":
    # Example usage (optional - for testing config loading)
    config, embed_model = load_shared_resources()
    print("Config:", config)
    print("Embedding Model:", embed_model)
    logging.info("Shared resources loaded successfully (from config_loader.py).")