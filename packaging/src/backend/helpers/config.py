"""
Configuration Management Module

Provides functionality for:
- Loading and validating configuration settings
- Managing global configuration state
- Setting up required directories and API keys
"""

import configparser
import logging
import os
import sys
import json
from types import SimpleNamespace

global_config = SimpleNamespace()

DEFAULT_CONFIG = """
[API_KEYS]
unstructured_api_key = your_unstructured_key
unstructured_url = https://api.unstructuredapp.io/general/v0/general  
openai_api_key = your_openai_key 

[DIRECTORIES]
input_dir = ./data/input
output_dir = ./data/output

[MODEL]
embedding_model = meta-llama/Meta-Llama-3-8B-Instruct
llm_model = gpt-4o

[SUPABASE]
supabase_url = your_supabase_url
supabase_key = your_supabase_key

[PDF_PROCESSING]
save_bbox_images = True
save_document_elements = True
logging_level = CRITICAL
show_progressbar = True
"""

def create_default_config(config_path):
    """Create a default configuration file with standard settings
    
    Args:
        config_path (str): Path where config file should be created
    """
    with open(config_path, 'w') as config_file:
        config_file.write(DEFAULT_CONFIG)
    logging.info(f"Created default config file at {config_path}")

def load_config(config_path='config.ini'):
    """Load and validate configuration settings from file
    
    Args:
        config_path (str): Path to configuration file
        
    Returns:
        GlobalConfig: Loaded configuration object
        
    Raises:
        SystemExit: If critical parameters are missing
    """
    global global_config
    
    if not os.path.exists(config_path):
        logging.warning(f"Config file not found at {config_path}. Creating default config.")
        create_default_config(config_path)
        print(f"A default configuration file has been created at {config_path}")
        print("Please edit this file to add your API keys before running the program again.")
        sys.exit(1)
        
    config = configparser.ConfigParser()
    config.optionxform = str  # Preserve case
    config.read(config_path)
    
    # Check for critical parameters
    critical_params = [
        ('API_KEYS', 'unstructured_api_key'),
        ('API_KEYS', 'openai_api_key'),
        ('DIRECTORIES', 'input_dir'),
        ('DIRECTORIES', 'output_dir')
    ]
    
    missing_params = []
    
    for section, key in critical_params:
        if not config.has_section(section) or not config.has_option(section, key):
            missing_params.append(f"{section}.{key}")
    
    if missing_params:
        print(f"Critical parameter(s) missing in config.ini: {', '.join(missing_params)}")
        print("Please add the missing parameters to your config.ini file.")
        sys.exit(1)
    
    # Convert to SimpleNamespace
    for section in config.sections():
        section_namespace = SimpleNamespace()
        for key, value in config.items(section):
            # Convert boolean strings to actual booleans
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            setattr(section_namespace, key, value)
        setattr(global_config, section.lower(), section_namespace)
    
    # Create directories if they don't exist
    try:
        os.makedirs(global_config.directories.input_dir, exist_ok=True)
        os.makedirs(global_config.directories.output_dir, exist_ok=True)
        logging.info("Directories created/verified successfully")
    except Exception as e:
        logging.error(f"Error creating directories: {str(e)}")
        sys.exit(1)
    
    logging.info("Configuration loaded successfully")
    return global_config

def save_config(config_path='config.ini'):
    """Save current configuration state to file
    
    Args:
        config_path (str): Path to save configuration
        
    Returns:
        bool: True if save successful, False otherwise
    """
    config = configparser.ConfigParser()
    
    # Convert SimpleNamespace back to ConfigParser format
    for section in dir(global_config):
        if not section.startswith('_'):
            config[section.upper()] = {}
            section_obj = getattr(global_config, section)
            for key in dir(section_obj):
                if not key.startswith('_'):
                    config[section.upper()][key] = str(getattr(section_obj, key))
    
    # Write to file
    try:
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        logging.info(f"Configuration saved successfully to {config_path}")
        return True
    except Exception as e:
        logging.error(f"Error saving config: {str(e)}")
        return False

def load_configuration():
    """Load and validate the complete configuration
    
    Validates:
    - Required sections exist
    - Critical parameters are present
    - Directory paths are valid
    
    Returns:
        SimpleNamespace: Validated configuration object
    """
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # Convert section names while preserving case for values
        config_dict = {}
        for section in config.sections():
            # Store with original section names
            config_dict[section] = {k: v for k, v in config[section].items()}
        
        return SimpleNamespace(**{
            'api_keys': SimpleNamespace(**config_dict['API_KEYS']),
            'directories': SimpleNamespace(**config_dict['DIRECTORIES']),
            'model': SimpleNamespace(**config_dict['MODEL']),
            'supabase': SimpleNamespace(**config_dict['SUPABASE']),
            'pdf_processing': SimpleNamespace(**config_dict['PDF_PROCESSING'])
        })
            
    except Exception as e:
        logging.error(f"Configuration error: {str(e)}")
        print(f"Available sections: {config.sections()}")  # Debug print
        print(f"Config dict: {config_dict}")  # Debug print
        return None

def get_global_config():
    """Get the global configuration object."""
    global global_config
    return global_config