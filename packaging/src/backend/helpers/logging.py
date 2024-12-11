import logging

"""
Logging Configuration Module

Handles:
- Setting up application logging
- Configuring log levels for different components
- Managing log file output
"""

def setup_logging():
    """Configure application-wide logging settings
    
    Sets up:
    - File-based logging
    - Console output
    - Component-specific log levels
    - Log format and rotation
    """
    logging.basicConfig(
        filename='pdf_converter.log',
        level=logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='w'
    )
    # Suppress INFO logs from http.client
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    logging.getLogger('').addHandler(console)
    
    logging.getLogger('http.client').setLevel(logging.ERROR)
    logging.getLogger('httpx').setLevel(logging.ERROR)
    logging.getLogger('unstructured').setLevel(logging.ERROR)
    logging.getLogger('unstructured_ingest.v2').setLevel(logging.ERROR)
    logging.getLogger('unstructured_ingest').setLevel(logging.ERROR)
    logging.getLogger('unstructured.trace').setLevel(logging.ERROR)
    