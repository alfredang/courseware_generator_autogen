"""
File: utils.py

===============================================================================
Utilities Module for File Handling and Text Node Creation
===============================================================================
Description:
    This module provides utility functions to support file operations and the creation of TextNode
    objects for content processing within the LlamaIndex framework. The functions in this module
    facilitate saving uploaded files, extracting page numbers from image filenames, sorting image files
    based on page numbers, and converting JSON documents into TextNode objects enriched with metadata,
    such as page numbers and image paths.

Main Functionalities:
    • save_uploaded_file(uploaded_file, save_dir):
          Saves an uploaded file to the specified directory, creating the directory if it does not exist.
    • get_page_number(file_name):
          Extracts a page number from an image filename using a predefined regex pattern.
    • _get_sorted_image_files(image_dir):
          Retrieves and returns image files from a directory sorted by page number.
    • get_text_nodes(json_dicts, image_dir=None):
          Converts a list of JSON dictionaries containing markdown text into TextNode objects,
          associating each node with metadata including the page number and corresponding image path (if available).

Dependencies:
    - Standard Libraries: re, os, pathlib (Path)
    - External Libraries: llama_index.core.schema (TextNode)

Usage:
    - Import the necessary functions from this module to handle file uploads and generate TextNode objects
      for further content processing.
    - Example:
          from utils import save_uploaded_file, get_text_nodes
          file_path = save_uploaded_file(uploaded_file, "uploads")
          nodes = get_text_nodes(json_data, image_dir="path/to/images")

Author:
    Derrick Lim
Date:
    3 March 2025
===============================================================================
"""

import re
import os
from pathlib import Path
from llama_index.core.schema import TextNode

def save_uploaded_file(uploaded_file, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    file_path = os.path.join(save_dir, uploaded_file.name)
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def get_page_number(file_name):
    match = re.search(r"-page-(\d+)\.jpg$", str(file_name))
    if match:
        return int(match.group(1))
    return 0

def _get_sorted_image_files(image_dir):
    """Get image files sorted by page."""
    raw_files = [f for f in list(Path(image_dir).iterdir()) if f.is_file()]
    sorted_files = sorted(raw_files, key=get_page_number)
    return sorted_files

def get_text_nodes(json_dicts, image_dir=None):
    """Split docs into nodes, by separator."""
    nodes = []

    image_files = _get_sorted_image_files(image_dir) if image_dir is not None else None
    md_texts = [d["text"] for d in json_dicts]

    for idx, md_text in enumerate(md_texts):
        chunk_metadata = {"page_num": idx + 1}
        # Check if an image exists for the current index
        if idx < len(image_files):
            chunk_metadata["image_path"] = str(image_files[idx])
        else:
            chunk_metadata["image_path"] = None  # No image available for this page
        
        # if image_files is not None:
        #     image_file = image_files[idx]
        #     chunk_metadata["image_path"] = str(image_file)
        chunk_metadata["parsed_text_markdown"] = md_text
        node = TextNode(
            text="",
            metadata=chunk_metadata,
        )
        nodes.append(node)

    return nodes