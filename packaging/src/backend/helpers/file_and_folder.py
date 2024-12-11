import json
import os
from typing import List

import fitz

"""
File and Directory Management Module

Provides utilities for:
- File path handling
- PDF page counting
- File extension filtering
"""

def get_json_file_elements(pdf_filename):
    """Get JSON elements associated with a PDF file
    
    Args:
        pdf_filename (str): Name of PDF file (without extension)
        
    Returns:
        list: JSON elements from associated file
    """
    file_path = pdf_filename +'.json'
    with open(file_path, 'r') as file:
        return json.load(file)
    
def get_pdf_page_count(file_path: str) -> int:
    """Count pages in a PDF file
    
    Args:
        file_path (str): Path to PDF file
        
    Returns:
        int: Number of pages in PDF
    """
    with fitz.open(file_path) as pdf:
        return len(pdf)
    
def get_files_with_extension(directory: str, extension: str) -> List[str]:
    """Get list of files with specific extension from directory
    
    Args:
        directory (str): Directory to search
        extension (str): File extension to filter by
        
    Returns:
        List[str]: List of matching file paths
        
    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")
        
    # Ensure extension starts with a dot
    if not extension.startswith('.'):
        extension = f'.{extension}'
        
    # Get all files in directory that match the extension
    matching_files = [
        os.path.join(directory, f) 
        for f in os.listdir(directory) 
        if f.lower().endswith(extension.lower())
    ]
    
    return sorted(matching_files)  # Return sorted list for consistent ordering
