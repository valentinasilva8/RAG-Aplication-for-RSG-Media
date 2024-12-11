# RAG Document Processing System

## Overview

This system is a Retrieval-Augmented Generation (RAG) application designed to process PDF documents through several stages:

1. **Document Ingestion**: Processes PDF files using Unstructured.io API
2. **Content Enrichment**: Enhances text, images, and tables with AI-generated metadata
3. **Chunking**: Segments documents into meaningful chunks
4. **Vector Storage**: Stores chunks with embeddings in Supabase
5. **Intelligent Retrieval**: Uses vector similarity to find relevant information
6. **Variable Extraction**: Processes documents to extract key contract variables

## Installation

### Prerequisites
- Python 3.8.1 or higher (but less than 4.0)
- pip (Python package installer)

### Steps
1. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```


Key dependencies include:
- PyPDF2>=3.0.0
- pdf2image>=1.16.3
- pdfminer.six>=20221105
- unstructured[all-docs]>=0.10.30
- fastapi>=0.104.1
- uvicorn>=0.24.0
- supabase>=2.0.3
- openai>=1.0.0
- And other dependencies listed in requirements.txt

## System Architecture

### Main Components

1. **API Layer** (`rag_functions.py`)
   - FastAPI application serving as the main entry point
   - Handles file uploads and processing requests
   - Coordinates the document processing pipeline

2. **Processing Pipeline** (`helpers/pdf_ingest.py`)
   - PDF document partitioning
   - Content extraction and structuring
   - Annotation processing

3. **Enrichment System** (`helpers/enrichments.py`)
   - Text tagging with XML-style markers
   - Image and table content summarization
   - Content structure enhancement

4. **Storage Layer** (`store_chunks.py`)
   - Vector embedding generation
   - Supabase database integration
   - Chunk management and storage

## Detailed Component Breakdown

### 1. API Layer (`rag_functions.py`)

The main entry point handling:

- **File Upload Endpoint** (`/upload`)
  - Accepts PDF files
  - Validates file format and size
  - Initiates processing pipeline

- **Document Processing**
  - Coordinates with Unstructured.io API
  - Manages processing stages
  - Returns processing status and results

### 2. Document Processing (`helpers/pdf_ingest.py`)

The PDFProcessor class manages:

- **Document Partitioning**
  ```python
  def process_pdfs(self, input_dir: str, pdf_files: List[str])
  ```
  - Splits documents into logical sections
  - Extracts text, tables, and images
  - Preserves document structure

- **Content Extraction**
  - Uses Unstructured.io API for high-quality extraction
  - Maintains formatting and layout information
  - Handles multiple document types

### 3. Content Enrichment (`helpers/enrichments.py`)

Enhances document content through:

- **Text Tagging**
  ```python
  def enrich_text(text_content)
  ```
  - Adds semantic XML tags (e.g., <COMPANY>, <DATE>, <PAYMENT>)
  - Identifies entities (companies, dates, addresses)
  - Preserves original text structure

- **Image Processing**
  ```python
  def summarize_image(image_base64)
  ```
  - Generates descriptions for images
  - Extracts relevant information
  - Links images to context

- **Table Processing**
  ```python
  def summarize_table(table_image_base64)
  ```
  - Analyzes table structure and content
  - Extracts row and column relationships
  - Generates structured summaries of tabular data
  - Preserves data relationships and hierarchies

### 4. Storage System (`store_chunks.py`)

Manages document storage and retrieval:

- **Vector Generation**
  ```python
  def encode_text_to_vector(text)
  ```
  - Creates embeddings using OpenAI's API
  - Processes text chunks for similarity search
  - Optimizes for retrieval

- **Database Management**
  ```python
  def insert_chunks(file_path)
  ```
  - Stores chunks in Supabase
  - Manages document relationships
  - Handles metadata storage

## Variable Extraction Process

The system extracts key variables through a two-step process:

1. **Retrieval Question**: Finds relevant chunks using vector similarity
   ```python
   "retrieve_question": """Find text containing:
   1. Tables or definitions that mention 'Pay License Period'
   2. Look for <examples> tags containing date ranges
   3. Look for <DATE> tags containing date ranges
   4. Look for text that shows examples of license periods
   ...
   ```

2. **Generate Question**: Extracts specific information from relevant chunks, focusing on XML tags
   ```python
   "generate_question": """Extract ONLY the exact license period date range.
   Rules:
   1. If you find a date range in <DATE> tags, use that exact value
   2. If you find a date range in <examples> tags within a Pay License Period definition, use that exact value
   3. Return the date range in exactly the format shown (e.g., '01/07/2020-05/01/2023')
   4. Only extract values from within XML tags
   ...
   ```

The system specifically looks for values within XML tags (e.g., <DATE>, <PAYMENT>, <COMPANY>) to ensure accurate extraction of information.

## Usage

To run the application:

1. First, configure your `config.ini` with the necessary API keys and credentials:
   ```ini
   [API_KEYS]
   unstructured_api_key = your_unstructured_key  # Get from unstructured.io
   unstructured_url = https://api.unstructuredapp.io/general/v0/general
   openai_api_key = your_openai_key  # Get from platform.openai.com
   
   [SUPABASE]
   supabase_url = your_supabase_url  # Get from your Supabase project settings
   supabase_key = your_supabase_key  # Get your service_role key from Supabase
   ```
   
   **IMPORTANT**: The application will not work without valid API keys. Make sure to:
   - Sign up for Unstructured.io and get an API key
   - Get an OpenAI API key from platform.openai.com
   - Create a Supabase project and get your project URL and service_role key

2. Open two terminal windows:

   Terminal 1 (Backend - will run on http://localhost:8000):
   ```bash
   cd packaging/src/backend
   uvicorn rag_functions:app --host localhost --port 8000 --reload
   ```

   Terminal 2 (Frontend - will run on http://localhost:3000):
   ```bash
   cd packaging/src/frontend
   npm install 
   npm run dev
   ```

3. Access the application:
   - Backend API: http://localhost:8000
   - Frontend Interface: http://localhost:3000
   - Use the frontend interface to upload and process PDF documents
   - API documentation available at http://localhost:8000/docs

Note: 
- Make sure both ports (8000 and 3000) are available and not being used by other applications
- If you get authentication errors, double-check your API keys in config.ini
- The application will log errors if any API keys are missing or invalid

## Processing Flow

1. **Document Upload**
   - File received through API
   - Initial validation performed
   - Processing pipeline initiated

2. **Content Processing**
   - Document partitioned into elements
   - Text, images, and tables extracted
   - Content structure preserved

3. **Enrichment**
   - Content tagged with semantic XML markers
   - Images and tables summarized
   - Structure enhanced for retrieval

4. **Storage**
   - Content chunked for optimal retrieval
   - Vector embeddings generated
   - Chunks stored in Supabase

5. **Variable Extraction**
   - Relevant chunks retrieved using similarity search
   - Specific information extracted using GPT-4
   - Results formatted and returned

## Error Handling

The system includes comprehensive error handling for:

- File processing errors
- API communication issues
- Database operations
- Content extraction problems

## Logging

Detailed logging is implemented throughout:

- Processing status and progress
- Error tracking and reporting
- Performance monitoring
- Debug information

## Security Considerations

- API key management
- File validation
- Access control
- Data sanitization

## Future Enhancements

### Immediate Planned Features

1. **Excel Report Generation**
   - Automatic generation of Excel reports containing extracted variables
   - Customizable templates for different document types
   - Summary sheets with key contract information
   - Export options for different Excel formats
   - Batch processing capabilities for multiple documents

2. **Enhanced Document Processing**
   - Support for additional document types (Word, HTML, etc.)
   - Improved table extraction and analysis
   - Better handling of complex document layouts
   - Support for multiple languages

3. **User Interface Improvements**
   - Interactive dashboard for monitoring processing status
   - Batch upload capabilities
   - Progress tracking for long-running processes
   - Real-time processing updates

### Long-term Development Goals

1. **Advanced Analytics**
   - Contract comparison tools
   - Trend analysis across multiple documents
   - Automated anomaly detection
   - Custom variable definition interface

2. **Integration Features**
   - API endpoints for third-party integration
   - Webhook support for processing events
   - Integration with popular document management systems
   - Support for cloud storage providers

3. **Performance Optimizations**
   - Parallel processing of multiple documents
   - Caching system for frequent queries
   - Optimized vector search algorithms
   - Reduced API calls through better chunking

4. **Enhanced Security Features**
   - Role-based access control
   - Document-level permissions
   - Audit logging
   - Encryption at rest and in transit

5. **Quality of Life Features**
   - Automated testing for variable extraction
   - Custom variable definition interface
   - Template management system
   - Bulk processing tools

### Technical Improvements

1. **Code Architecture**
   - Modular plugin system for new features
   - Improved error handling and recovery
   - Better logging and monitoring
   - Unit test coverage

2. **Database Optimizations**
   - Improved vector search performance
   - Better handling of large documents
   - Optimized storage schema
   - Backup and recovery features (We have used pg_dump's free version to backup the database in which we need to run the dump command every time we want to backup the database with new data. However, using a paid version of supabase's backup feature would be a better solution for more dynamic applications like this one.)

3. **API Enhancements**
   - Versioned API endpoints
   - Rate limiting
   - Better error responses
   - API documentation



