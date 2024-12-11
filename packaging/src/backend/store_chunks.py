import os
import json
import configparser
from supabase import create_client, Client
from openai import OpenAI
from helpers.pdf_ingest import PDFProcessor  # Import the PDFProcessor
from types import SimpleNamespace
import sys

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from helpers.enrichments import global_config  # Import global_config

# Load configuration
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')

try:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")
        
    config.read(config_path)
    
    # Check for required sections and keys without modifying them
    required_sections = ['API_KEYS', 'SUPABASE']
    required_keys = {
        'API_KEYS': ['openai_api_key'],
        'SUPABASE': ['supabase_url', 'supabase_key']
    }
    
    for section in required_sections:
        if section not in config:
            raise KeyError(f"{section} section missing from config file")
        for key in required_keys[section]:
            if key not in config[section]:
                raise KeyError(f"{key} missing from {section} section")
        
except Exception as e:
    print(f"Configuration Error: {str(e)}")
    raise

# Initialize OpenAI client with key from config
openai_client = OpenAI(
    api_key=config['API_KEYS']['openai_api_key']
)

# Initialize Supabase client from config
url: str = config['SUPABASE']['supabase_url']
key: str = config['SUPABASE']['supabase_key']
supabase: Client = create_client(url, key)

# Create necessary directories
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, 'data')
input_dir = os.path.join(data_dir, 'input')
output_dir = os.path.join(data_dir, 'output')
chunked_dir = os.path.join(output_dir, '02_chunked')

# Create all directories
for directory in [data_dir, input_dir, output_dir, chunked_dir]:
    os.makedirs(directory, exist_ok=True)

# Set up global configuration
global_config.api_keys = SimpleNamespace()
global_config.api_keys.openai_api_key = config['API_KEYS']['openai_api_key']
global_config.api_keys.unstructured_api_key = config['API_KEYS'].get('unstructured_api_key', '')
global_config.api_keys.unstructured_url = config['API_KEYS'].get('unstructured_url', 'https://api.unstructured.io/general/v0/general')

global_config.directories = SimpleNamespace()
global_config.directories.output_dir = output_dir
global_config.directories.input_dir = input_dir
global_config.directories.partitioned_dir = os.path.join(output_dir, '01_partitioned')
global_config.directories.chunked_dir = chunked_dir
global_config.directories.work_dir = os.path.join(output_dir, 'temp')

# Create configuration namespace for PDFProcessor
pdf_config = SimpleNamespace()
pdf_config.api_keys = global_config.api_keys
pdf_config.directories = global_config.directories

"""
Document Chunking and Storage Module

Handles:
- Breaking documents into semantic chunks
- Generating vector embeddings
- Storing chunks in Supabase
"""

def encode_text_to_vector(text):
    """Generate vector embedding for text using OpenAI
    
    Args:
        text: Text content to embed
        
    Returns:
        list: Vector embedding array
    """
    try:
        print(f"Generating embedding for text: {text[:100]}...")  # Debug line
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        if response.data and response.data[0].embedding:
            print(f"Successfully generated embedding of length: {len(response.data[0].embedding)}")  # New debug line
            return response.data[0].embedding
        else:
            print("No embedding data in response")
            return None
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return None

def get_or_create_document_id(filename):
    """Get or create a document record in Supabase
    
    Args:
        filename: Name of document file
        
    Returns:
        int: Document ID from database
    """
    response = supabase.table("documents").select("document_id").eq("filename", filename).execute()
    if response.data:
        return response.data[0]["document_id"]
    else:
        insert_response = supabase.table("documents").insert({"filename": filename}).execute()
        return insert_response.data[0]["document_id"]

def fetch_chunks_without_embeddings(document_id):
    """Fetch chunks that have NULL embeddings for the given document."""
    response = supabase.table("chunks").select("*").eq("document_id", document_id).is_("embedding", None).execute()
    return response.data

def update_chunk_embedding(chunk_id, embedding):
    """Update the embedding column for the specified chunk."""
    try:
        print(f"Attempting to update chunk {chunk_id} with embedding of length {len(embedding)}")  # New debug line
        response = supabase.table("chunks").update({
            "embedding": embedding
        }).eq("id", chunk_id).execute()
        
        if response.data:
            print(f"Successfully updated embedding for chunk ID {chunk_id}")
            # Verify the update
            check = supabase.table("chunks").select("embedding").eq("id", chunk_id).execute()
            if check.data and check.data[0]["embedding"]:
                print(f"Verified: Embedding is stored for chunk {chunk_id}")
            else:
                print(f"Warning: Embedding may not have been stored properly for chunk {chunk_id}")
        else:
            print(f"No data returned when updating chunk {chunk_id}")
            if response.error:
                print(f"Error details: {response.error}")
    except Exception as e:
        print(f"Error updating embedding for chunk ID {chunk_id}: {str(e)}")
        print(f"Error type: {type(e)}")  # New debug line

def process_embeddings(document_id):
    """Generate and store embeddings for document chunks
    
    Args:
        document_id: ID of document to process
    """
    print(f"\n=== Starting embedding processing for document_id: {document_id} ===")
    
    chunks = fetch_chunks_without_embeddings(document_id)
    print(f"Fetched {len(chunks) if chunks else 0} chunks without embeddings")
    
    if not chunks:
        print("All chunks already have embeddings.")
        return
    
    for chunk in chunks:
        print(f"\nProcessing chunk ID {chunk['id']}:")
        print(f"Text preview: {chunk['text'][:100]}...")
        
        try:
            embedding = encode_text_to_vector(chunk['text'])
            
            if embedding:
                print(f"Generated embedding of length: {len(embedding)}")
                update_chunk_embedding(chunk['id'], embedding)
            else:
                print(f"WARNING: Failed to generate embedding for chunk {chunk['id']}")
                
        except Exception as e:
            print(f"ERROR processing chunk {chunk['id']}: {str(e)}")
            print(f"Error type: {type(e)}")
            continue
    
    # Verify after processing
    remaining_chunks = fetch_chunks_without_embeddings(document_id)
    print(f"\nAfter processing: {len(remaining_chunks) if remaining_chunks else 0} chunks still without embeddings")

def insert_chunks(file_path):
    """Insert document chunks into Supabase with embeddings
    
    Args:
        file_path: Path to JSON chunks file
        
    Returns:
        int: Document ID for inserted chunks
    """
    try:
        print(f"Reading chunks from {file_path}")
        with open(file_path, 'r') as file:
            json_data = json.load(file)
            
        if not json_data:
            print(f"Warning: Empty JSON data from {file_path}")
            return None
            
        print(f"Found {len(json_data)} chunks to process")

        # Get or create document_id
        filename = os.path.basename(file_path).replace('.json', '')
        document_id = get_or_create_document_id(filename)
        print(f"Using document_id: {document_id} for file: {filename}")

        chunks_inserted = 0
        for item in json_data:
            try:
                # Generate embedding for the chunk text
                embedding = encode_text_to_vector(item["text"])
                
                metadata = item["metadata"]
                chunk_data = {
                    "element_id": item["element_id"],
                    "text": item["text"],
                    "document_id": document_id,
                    "filetype": metadata.get("filetype"),
                    "languages": metadata.get("languages", []),
                    "start_page_number": metadata.get("page_number"),
                    "end_page_number": metadata.get("page_number"),
                    "orig_elements": metadata.get("orig_elements"),
                    "source_file": filename,
                    "embedding": embedding  # Add embedding here
                }
                
                response = supabase.table("chunks").insert(chunk_data).execute()

                if response.data:
                    chunks_inserted += 1
                    print(f"Inserted chunk {chunks_inserted} with embedding")
                else:
                    print(f"Warning: No data returned when inserting chunk {item['element_id']}")

            except Exception as e:
                print(f"Error processing chunk {item['element_id']}: {str(e)}")
                continue

        print(f"Successfully inserted {chunks_inserted} new chunks with embeddings")
        return document_id

    except Exception as e:
        print(f"Error in insert_chunks: {str(e)}")
        raise

def main():
    """Main function."""
    try:
        # Initialize PDF processor with config
        pdf_processor = PDFProcessor()
        
        # Set both configurations
        pdf_processor.config = pdf_config
        pdf_processor.global_config = global_config
        
        # Create all required directories
        for directory in [
            pdf_config.directories.output_dir,
            pdf_config.directories.input_dir,
            pdf_config.directories.partitioned_dir,
            pdf_config.directories.chunked_dir,
            pdf_config.directories.work_dir
        ]:
            os.makedirs(directory, exist_ok=True)
            print(f"Ensuring directory exists: {directory}")
        
        # Get list of PDFs in input directory
        pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
        
        if not pdf_files:
            print("No PDF files found in input directory")
            return
            
        # Process each PDF file
        for pdf_file in pdf_files:
            pdf_path = os.path.join(input_dir, pdf_file)
            if not os.path.exists(pdf_path):
                print(f"PDF file not found: {pdf_path}")
                continue
                
            print(f"Processing: {pdf_file}")
            pdf_processor.process_pdfs(input_dir, [pdf_file])
            
            # Get JSON file path
            json_file = os.path.join(chunked_dir, f"{pdf_file}.json")
            print(f"Looking for chunks file at: {json_file}")
            
            if os.path.exists(json_file):
                print(f"\nProcessing chunks from: {json_file}")
                document_id = insert_chunks(json_file)
                
                # Add embedding processing
                if document_id:
                    process_embeddings(document_id)
            else:
                print(f"No chunks file found at: {json_file}")
    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()

