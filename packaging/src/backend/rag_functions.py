"""
RAG API Functions Module

Provides FastAPI endpoints for:
- Document upload and processing
- Content extraction and analysis
- Variable identification and extraction
"""

import openai
import numpy as np
import configparser
from supabase import create_client, Client
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import httpx
from helpers.pdf_ingest import PDFProcessor
from helpers.pdf_annotation import annotate_pdf_pages
from helpers.enrichments import enrich_json_with_summaries
from helpers.config import load_config, get_global_config
import logging
from store_chunks import insert_chunks, process_embeddings, get_or_create_document_id
import os
import json

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration at startup
load_config()
global_config = get_global_config()

if not global_config:
    raise RuntimeError("Failed to load configuration")

# Initialize the clients with global_config values
unstructured_api_key = global_config.api_keys.unstructured_api_key
unstructured_url = global_config.api_keys.unstructured_url

# Initialize OpenAI client
client = openai.OpenAI(
    api_key=global_config.api_keys.openai_api_key
)

# Initialize Supabase client
supabase: Client = create_client(
    supabase_url=global_config.supabase.supabase_url,
    supabase_key=global_config.supabase.supabase_key
)

# Ensure upload directory exists
UPLOAD_DIR = Path("data/input")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def query_similar_chunks(embedding, document_id):
    """Find similar chunks using vector similarity search
    
    Args:
        embedding: Query vector embedding
        document_id: Document to search within
        
    Returns:
        list: Similar chunks with similarity scores
    """
    try:
        response = supabase.rpc(
            'match_documents2', {
            'query_embedding': embedding.tolist(),
            'match_threshold': -0.2,
            'match_count': 5,
            'filter_document_id': document_id
        }).execute()

        if response.data:
            print(f"Found {len(response.data)} matching chunks for document_id {document_id}")
            for chunk in response.data:
                print(f"Similarity score: {chunk['similarity']}")
                print(f"First 100 chars of chunk: {chunk['text'][:100]}...")
                
            return [
                {
                    'id': chunk['id'],
                    'text': chunk['text'],
                    'similarity': chunk['similarity'],
                    'metadata': {'page_number': chunk['start_page_number']}
                } for chunk in response.data
            ]
        else:
            # Debug query to check chunks for this document
            check_chunks = supabase.table("chunks").select("id, text").eq("document_id", document_id).limit(5).execute()
            print(f"Sample of available chunks for document_id {document_id}:")
            for chunk in check_chunks.data:
                print(f"Chunk {chunk['id']}: {chunk['text'][:100]}...")
            return []
            
    except Exception as e:
        print(f"Error querying Supabase: {e}")
        return []

def get_openai_embedding(prompt: str):
    """Get vector embedding from OpenAI for the given prompt"""
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=prompt
        )
        return np.array(response.data[0].embedding)
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def process_variables(variables, document_id, file_path: str = None):
    """Extract requested variables from document content
    
    Args:
        variables: List of variables to extract
        document_id: Document to process
        file_path: Optional path to document file
        
    Returns:
        dict: Extracted variables and values
    """
    results = {}
    
    for var in variables:
        print(f"\nProcessing variable: {var['name']} for document_id: {document_id}")
        
        # Get embedding for retrieval question
        embedding = get_openai_embedding(var['retrieve_question'])
        if embedding is None:
            print(f"Failed to get embedding for {var['name']}")
            continue
            
        # Get similar chunks
        chunks = query_similar_chunks(embedding, document_id)
        if not chunks:
            print(f"No relevant chunks found for {var['name']} in document_id {document_id}")
            continue
            
        # Prepare context from chunks
        context = "\n".join([chunk['text'] for chunk in chunks])
        
        # Prepare prompt for generation
        prompt = f"""Based on the following context, {var['generate_question']}

Context:
{context}

Answer:"""
        
        try:
            # Generate answer using OpenAI
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system", 
                        "content": """You are a precise data extractor. Extract EXACTLY what is asked for:
                        - For currency, if you see € or 'euro', return 'EUR'
                        - For payments, include the FULL amount with currency symbols and rates (e.g., €3.000,00/H)
                        - If multiple values exist, return ALL relevant values
                        - Do not make assumptions or add explanatory text
                        - If the specific value is not found, return ONLY 'Not found'"""
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            
            answer = response.choices[0].message.content.strip()
            results[var['name']] = answer
            
            print(f'"{var["name"]}", "{answer}"')
            
        except Exception as e:
            print(f"Error generating answer for {var['name']}: {e}")
            continue
    
    return results

def check_document_processed(file_path: str) -> tuple[bool, str]:
    """
    Check if document has already been processed by looking for chunks in database 
    and existing JSON files
    Returns: (is_processed, json_file_path)
    """
    try:
        file_name = Path(file_path).name
        print(f"Checking if {file_name} has been processed...")
        
        # Check database
        response = supabase.table('chunks') \
            .select('id') \
            .eq('source_file', file_name) \
            .execute()
            
        chunks_exist = len(response.data) > 0
        
        # Check for existing JSON file
        chunked_dir = os.path.join(global_config.directories.output_dir, '02_chunked')
        json_file = os.path.join(chunked_dir, f"{file_name}.json")
        json_exists = os.path.exists(json_file)
        
        print(f"Found existing chunks in DB: {chunks_exist}")
        print(f"Found existing JSON file: {json_exists}")
        
        return chunks_exist, json_file
        
    except Exception as e:
        logging.error(f"Error checking document status: {e}")
        return False, ""

# FastAPI endpoints
@app.get("/")
async def root():
    return {"message": "RAG Processing API"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle document upload and processing
    
    Processes uploaded file through:
    1. Initial PDF processing
    2. Content chunking
    3. Variable extraction
    4. Results storage
    
    Returns:
        dict: Processing results and extracted data
    """
    print(f"Received file: {file.filename}")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_path = UPLOAD_DIR / file.filename
    try:
        # Save the file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        print(f"File saved to: {file_path}")
        
        # Process the document
        processor = PDFProcessor()
        processor.config = global_config
        status, error_msg = processor.process_single_pdf(str(file_path))
        
        if status == 1:
            # Get the chunked file path
            output_dir = os.path.realpath(global_config.directories.output_dir)
            chunked_dir = os.path.join(output_dir, '02_chunked')
            json_file = os.path.join(chunked_dir, f"{file.filename}.json")
            
            if os.path.exists(json_file):
                print(f"Storing chunks from: {json_file}")
                # Insert chunks with embeddings
                document_id = insert_chunks(json_file)
                if document_id:
                    print(f"Processing variables for document_id: {document_id}")
                    # Pass document_id to process_variables
                    variables = [
                        {
                            "name": "deal_name",
                            "retrieve_question": "Find text containing <PRODUCT> tags that describe the agreement type, or <LEGAL> tags that contain the word 'Agreement'. Focus on the first few paragraphs of the document.",
                            "generate_question": "Extract ONLY the core agreement type (e.g. 'License Agreement', 'Service Agreement'). If you see <PRODUCT>License Agreement</PRODUCT> or <LEGAL>License Agreement</LEGAL>, return just 'License Agreement' without any party names or dates."
                        },
                        {
                            "name": "license_period",
                            "retrieve_question": """Find text containing:
                            1. Tables or definitions that mention 'Pay License Period' or 'License Period'
                            2. Look for <examples> tags containing date ranges
                            3. Look for <DATE> tags containing date ranges
                            4. Look for text that shows examples of license periods in DD/MM/YYYY-DD/MM/YYYY format
                            5. Focus on text that defines or shows examples of license periods
                            
                            Example text to match:
                            - <examples>"01/07/2020-05/01/2023"</examples>
                            - <definition>Pay License Period</definition>
                            - <DATE>01/07/2020-05/01/2023</DATE>
                            - Tables showing license period dates""",
                            
                            "generate_question": """Extract ONLY the exact license period date range. 

                            Rules:
                            1. If you find a date range in <examples> tags within a Pay License Period definition, use that exact value
                            2. If you find a date range in <DATE> tags, use that exact value
                            3. Return the date range in exactly the format shown (e.g., '01/07/2020-05/01/2023')
                            4. Do not modify or reformat the dates
                            5. Do not include any explanatory text
                            6. If multiple periods exist, prioritize the Pay License Period
                            7. Look for date ranges in both <examples> and <DATE> tags
                            8. If no specific date range is found, return 'Not found'

                            Example matches:
                            Input: '<examples>"01/07/2020-05/01/2023"</examples>'
                            Output: '01/07/2020-05/01/2023'
                            
                            Input: '<DATE>01/07/2020-05/01/2023</DATE>'
                            Output: '01/07/2020-05/01/2023'"""
                        },
                        {
                            "name": "license_fee",
                            "retrieve_question": "Find text containing <PAYMENT> tags or numbers with currency symbols (€, $) near terms like 'fee', 'payment', 'amount', 'cost', or 'price'. Also look for numbers followed by /H or per hour.",
                            "generate_question": "Extract ONLY the exact payment amount with its currency symbol and rate (e.g., €3.000,00/H or €42.000,00). Return the full amount exactly as written, NOT including any hourly rates, just the total sums."
                        },
                        {
                            "name": "contract_status",
                            "retrieve_question": "Find text containing <STATUS> tags or <LEGAL> tags that indicate the agreement's current state. Also look for phrases like 'Read, Agreed and executed', 'terminated', 'active', or text about contract effectiveness and termination.",
                            "generate_question": """Based on the tagged text, determine and return ONLY one of these status values:
                            - 'Active' if the agreement is currently in force
                            - 'Terminated' if the agreement shows signs of being completed, executed, or ended (including phrases like 'Read, Agreed and executed')
                            - 'Draft' if the agreement appears to be in draft form
                            - 'Not found' if the status cannot be determined

                            For example:
                            - <STATUS>Read, Agreed and executed</STATUS> should return 'Terminated'
                            - <STATUS>Active</STATUS> should return 'Active'
                            - <LEGAL>This agreement is currently in effect</LEGAL> should return 'Active'"""
                        },
                        {
                            "name": "licensor",
                            "retrieve_question": """Find text containing:
                            1. <PARTY> tags with the word 'LICENSOR' in them
                            2. Text near phrases like 'hereinafter the "licensor"'
                            3. Text in the opening paragraphs where parties are first introduced
                            
                            Focus on the agreement's header section where parties are first defined.""",
                            
                            "generate_question": """Extract ONLY the company/entity name that is identified as the licensor. 
                            
                            Rules:
                            1. Look for text between <PARTY> tags that appears BEFORE 'hereinafter the "licensor"'
                            2. Return the exact name as it appears in the document
                            3. Do not include any additional text or explanations
                            4. If multiple matches exist, prioritize the one that appears first in the document header
                            5. If no clear licensor is found, return 'Not found'"""
                        },
                        {
                            "name": "licensee",
                            "retrieve_question": "Find text containing <COMPANY>RSG Media</COMPANY> where it is first introduced as a party in the agreement. Look specifically at the beginning of the document where parties are defined.",
                            "generate_question": "Return ONLY 'RSG Media' if it appears as a party to the agreement. Look for text patterns like 'hereinafter \"RSG Media\"' or where RSG Media is introduced as the second party after the licensor."
                        },
                        {
                            "name": "licensor_address",
                            "retrieve_question": "Find text containing <ADDRESS> tags that appear IMMEDIATELY AFTER the licensor is named and BEFORE the word 'AND' that introduces the second party.",
                            "generate_question": "Extract ONLY the first address that appears after the licensor is named and before the second party is introduced. Return exactly what appears between the <ADDRESS> tags in that location only."
                        },
                        {
                            "name": "licensee_address",
                            "retrieve_question": "Find text containing <ADDRESS> tags that appear near <COMPANY>RSG Media</COMPANY> tags.",
                            "generate_question": "Extract ONLY the complete address found between <ADDRESS> tags that appears with RSG Media's details."
                        },
                        {
                            "name": "document_language",
                            "retrieve_question": "Find text containing <PRODUCT> tags with 'Language' or 'language version' mentions, or <LEGAL> tags discussing document languages.",
                            "generate_question": "List ALL languages mentioned as official document versions. For Italian language mentions, return just 'Italian'. Return only the language name."
                        },
                        {
                            "name": "territory",
                            "retrieve_question": "Find text containing <TERRITORY> tags that specify geographical regions, especially near phrases like 'Licensed territory' or 'Territory'.",
                            "generate_question": "Extract ALL territories listed between <TERRITORY> tags. Format as a bullet list with each territory on a new line starting with '- '. Remove any '(the \"Territory\")' type annotations."
                        },
                        {
                            "name": "rights_granted",
                            "retrieve_question": """Find text containing <RIGHTS> tags or <PRODUCT> tags that describe distribution rights, licenses, or permissions. 
                            Look for:
                            - Text near terms like 'Distribution', 'rights granted', 'license', 'exploitation'
                            - Sections describing VOD, SVOD, PPV, EST, DTR, DTO
                            - Text containing <RIGHTS> tags that mention viewing or distribution methods
                            - Sections discussing theatrical, television, or home entertainment rights
                            - Text about linear and non-linear distribution
                            - Sections mentioning catch-up rights or near video on demand
                            Focus especially on text that appears in licensing terms or rights sections.""",
                            "generate_question": """Extract ALL rights granted, including distribution and exploitation rights. Format as a bullet list where each line starts with '- '.

                            Include rights such as:
                            - Download to Rent
                            - DTO (Download to Own)
                            - SVOD (Subscription Video on Demand)
                            - FVOD (Free Video on Demand)
                            - Near Video on Demand
                            - Catch Up rights
                            - PPV (Pay Per View)
                            - Television rights
                            - Theatrical rights
                            - Linear/Non-Linear Distribution
                            - EST (Electronic Sell-Through)
                            - Home Entertainment
                            - DTR (Download to Rent)

                            For example:
                            - Download to Rent
                            - SVOD
                            - Pay Per View
                            
                            Return ALL rights mentioned in the text, preserving the exact terminology used in the document. Include both abbreviated (e.g., 'PPV') and full forms if both are mentioned."""
                        },
                        {
                            "name": "contract_currency",
                            "retrieve_question": "Find text containing <PAYMENT> tags with € symbols or text containing the word 'Euro' or 'euro'.",
                            "generate_question": "Return ONLY 'EUR' if euro symbols (€) or the word 'euro/Euro' is found in the payment amounts or currency specifications."
                        },

                        {
                            "name": "due_date",
                            "retrieve_question": "Find text containing <TERM> tags near payment terms, especially looking for text that mentions payment timing, days, or due dates. Focus on text that appears near <PAYMENT> tags and mentions of invoice payment terms.",
                            "generate_question": """Extract ONLY the exact payment timing terms. If you find a specific payment schedule like '90 [ninety] days end month from the start avail date', return it exactly as written.
                            
                            For example:
                            - If you see '<TERM>90 [ninety] days end month</TERM> from the start avail date of the License Period' return exactly that
                            - If you see other specific payment timing terms, return them exactly as written
                            - If no specific payment timing is found, return 'Not found'
                            
                            Do not include the payment amounts or other terms - focus only on the timing/due date information."""
                        },
                        {
                            "name": "definitions",
                            "retrieve_question": """Find text containing definitions by looking for these specific patterns:
                            1. Text containing 'means' or 'shall mean' near <PRODUCT>, <TERM>, or <RIGHTS> tags
                            2. Text matching pattern '[Term]: means' or '[Term] shall mean'
                            3. Text containing 'Extended Catch-Up', 'Catch Up', 'Video on Demand', or similar technical terms followed by their definitions
                            4. Text blocks starting with bullet points or numbers that define technical terms
                            5. Text containing timing specifications like '48 hours', '30 day period' near technical terms
                            6. Sections titled 'Definitions', 'Terms', or 'Glossary'
                            7. Look for definitions related to:
                               - Catch-Up services
                               - Video on Demand
                               - Storage periods
                               - Viewing periods
                               - Playback rights
                               - Technical specifications
                            
                            Example text to match:
                            - "Extended Catch-Up: means the ability to store..."
                            - "<PRODUCT>Term</PRODUCT> means..."
                            - "1.1 [Term] shall mean..."
                            - "• Technical Term: means..."
                            """,
                            
                            "generate_question": """Extract and format ALL definitions as a bulleted list. For each definition:
                            1. Start with "• "
                            2. Include the term followed by ": " (colon and space)
                            3. Include the complete definition including all technical specifications and time periods
                            4. Preserve exact timing specifications (e.g., "48 hours", "30 day period")
                            5. Keep all technical details exactly as written
                            
                            Format each definition exactly like this:
                            • Term: complete definition
                            
                            Example of correct formatting:
                            • Extended Catch-Up: means the ability to store the Audiovisual Work on a connected device for unconnected playback within 48 hours from initial playback (Viewing Period) within a 30 day storage period
                            
                            Important:
                            - Include ALL definitions found, even if they appear outside a dedicated definitions section
                            - Keep technical specifications and timing details exactly as written
                            - Don't summarize or modify the definitions
                            - Include definitions even if they're part of numbered lists or bullet points
                            - Return 'Not found' if no definitions matching these patterns are found"""
                        }
                    ]
                    
                    results = process_variables(variables, document_id)
                    return {
                        "status": "success",
                        "document_id": document_id,
                        "processing_results": results
                    }
            
        raise HTTPException(status_code=500, detail=error_msg)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        # Clean up the file if processing failed
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "rag_functions:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info",
        workers=1
    )