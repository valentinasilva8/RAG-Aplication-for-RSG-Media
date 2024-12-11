"""
-----------------------------------------------------------------
(C) 2024 Prof. Tiran Dagan, FDU University. All rights reserved.
-----------------------------------------------------------------

Partition JSON Enrichment Module

Provides functionality to enhance JSON data with:
- LLM-generated summaries of images
- Table content analysis
- Text element tagging and enrichment
"""

import logging
from openai import OpenAI
import json
from .config import global_config
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import base64
import re

# Initialize the logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

console = Console()

def summarize_table(table_image_base64):
    """Generate a text summary of a table using GPT-4 Vision
    
    Args:
        table_image_base64: Base64 encoded image of the table
        
    Returns:
        str: Natural language summary of table contents
    """
    client = OpenAI(api_key=global_config.api_keys.openai_api_key)
    
    prompt = """You are a table analyzing agent. Please analyze the table and give me a series of paragraphs for each data row. 
    I want you to describe in brief the content of each field and clearly call out the values from the table for that field. Include all the details for each field; please do not miss on any crucial information. 
    Each paragraph ends in \n\n before moving to the next item. Make sure you understand how the table is presenting the data.
    For instance, If there is data which is reading from "left to right" that means the "columns" of that table are specifying "fields" and the "rows" are the attributes or values of those fields, and if there is data reading from "top to bottom" that means the "rows" of that table are specifying "fields" and the columns of that table represent attributes or values of those fields. 
    Also, make taggings for all the values in the 2nd point below for example, <definition> xxxxx </definition>. 
    Please make the output is more compact while retaining all necessary details. Condense each field's analysis into concise, maintaining all the required metadata tags. This will reduce verbosity while keeping the structure organized and suitable for chunk processing.
    To make sure that I do not use a lot of tokens, please remove redundant or unnecessary information for fields where they do not apply. For example, for the field “color”, we do not need <units> so just do not output it. 
    Further, if you see a value that is not in my prompt but is in the table, then add it too so that you do not miss any information from the table.
    
    In summary, only provide me the text paragraphs for each field keeping all the points with no additional information outside the context before or after.
    1. Identify which way the table is reading; from left to right or from top to bottom
    2. Create a detailed metadata object for each field containing: 
    - "definition": Precise description of what this field represents 
    - "intent": Business purpose and use cases for this field 
    - "units": Units of measurement (if applicable) 
    - "data_type": Expected data type (string, number, date, boolean, etc.) 
    - "constraints": Business rules, valid ranges, or requirements 
    - "examples": List of valid example values 
    - "format": Expected format pattern (if applicable) 
    - "validation_rules": Specific validation requirements 
    - "is_required": Boolean indicating if field is mandatory 
    - "business_context": How this field relates to business processes 
    do not provide any json or anything else outside the context"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{table_image_base64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=1500,
        temperature=0
    )
    
    return response.choices[0].message.content.strip()



def enrich_json_with_summaries(json_file):
    """Process JSON data to add summaries and semantic enrichments
    
    Enhances JSON with:
    - Image descriptions
    - Table summaries  
    - Semantic text tagging
    
    Args:
        json_file: Path to JSON file to enrich
    """
    def enrich_text(text_content):
        """Add semantic XML-style tags to text content
        
        Tags added include:
        - Companies and organizations
        - Dates and time periods
        - Legal clauses and terms
        - Payment and financial info
        
        Args:
            text_content: Raw text to enrich
            
        Returns:
            str: Text with semantic tags added
        """
        client = OpenAI(api_key=global_config.api_keys.openai_api_key)
        
        # Debug print before enrichment
        print("\nBEFORE ENRICHMENT:")
        print(f"Text: {text_content[:200]}...")
        
        prompt = """You are a precise text tagging agent. Your task is to add XML-style tags around EXISTING text elements in the document. 
        
        Rules:
        1. ONLY tag text that actually exists in the input - NEVER generate new text or content - this is strictly forbidden
        2. DO NOT modify, rephrase or expand the original text
        3. DO NOT make assumptions or add information not present in the text
        4. Tag ALL relevant information that matches the tag definitions
        5. Preserve the exact original text structure and formatting
        6. For date ranges (e.g. "01/07/2020-05/01/2023"), tag the entire range as a single <DATE> element
        7. Your output must contain ONLY the input text with added XML tags
        
        Tags to use (only for EXACT matches in the original text):
        <COMPANY> - Company names (e.g., "SAMPLE LICENSOR", "RSG Media")
        <PARTY> - Party designations (e.g., "licensor", "licensee")
        <DATE> - Dates in any format, including date ranges (e.g., "01/07/2020-05/01/2023")
        <ADDRESS> - Full physical addresses
        <CONTACT> - Names, phones, emails
        <RIGHTS> - Rights and permissions granted
        <TERRITORY> - Geographic regions
        <TERM> - Time periods and durations
        <PAYMENT> - Money amounts and payment terms
        <LEGAL> - Legal clauses and conditions
        <PRODUCT> - Products or services
        <ID> - Reference numbers (e.g., "GB 111111111")
        <STATUS> - Contract status indicators

        Example input:
        "The license period is from 01/07/2020-05/01/2023 for the territory."
        
        Example output:
        "The license period is from <DATE>01/07/2020-05/01/2023</DATE> for the territory."

        Tag the following text:
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a precise text tagger that only tags existing text without adding any new information."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\n{text_content}"
                }
            ],
            temperature=0,
            max_tokens=2000
        )
        
        enriched_text = response.choices[0].message.content.strip()
        
        # Debug print after enrichment
        print("\nAFTER ENRICHMENT:")
        print(f"Text: {enriched_text[:200]}...")
        
        return enriched_text

    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # Retrieve lists of items to enrich
    textElements = [item for item in json_data if item['type'] == 'NarrativeText']
    imageElements = [item for item in json_data if item['type'] == 'Image']
    tableElements = [item for item in json_data if item['type'] == 'Table']
    titleElements = [item for item in json_data if item['type'] == 'Title']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        
        # Text processing
        task = progress.add_task(
            f"Processing text", 
            total=len(textElements)
        )

        for idx, item in enumerate(textElements, 1):
            progress.update(task, description=f"Enriching text: {idx}/{len(textElements)}")
            try:
                text_content = item.get('text', '')
                if text_content:
                    enriched_text = enrich_text(text_content)
                    # Save enriched text back to the text field
                    item['text'] = enriched_text
                progress.advance(task)
                
            except Exception as e:
                # Log the error with context for debugging
                error_context = text_content[:50] + "..." if len(text_content) > 50 else text_content
                console.print(f"Error processing text: {error_context} - {str(e)}", style="red")
                logger.error(f"Error processing text: {error_context} - {str(e)}")
        
        # Images
        task = progress.add_task(
            f"Enriching images", 
            total=len(imageElements)
        )

        for idx, item in enumerate(imageElements, 1):
            progress.update(task, description=f"Enriching images: {idx}/{len(imageElements)}")
            image_base64 = item['metadata']['image_base64']
            if image_base64:
                try:
                    summary = summarize_image(image_base64)
                    print(f"Generated summary for image {idx}: {summary}")  # Debugging output
                    item['text'] = summary

                    # Save after each image is processed
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    
                    progress.advance(task)
                except Exception as e:
                    console.print(f"Error processing image: {str(e)}", style="red")
                    logger.error(f"Error processing image: {str(e)}")
            else:
                console.print(f"Skipping image without base64 data: {item.get('text', 'Unnamed image')}", 
                            style="yellow")

        # Tables
        task = progress.add_task(
            f"Processing tables", 
            total=len(tableElements)
        )

        for idx, item in enumerate(tableElements, 1):
            progress.update(task, description=f"Enriching tables: {idx}/{len(tableElements)}")
            try:
                table_image_base64 = item['metadata']['image_base64']
                if table_image_base64:
                    structured_data = summarize_table(table_image_base64)
                    print(f"Generated summary for table {idx}: {structured_data}")  # Debugging output

                    # Ensure the structured data is saved in the 'text' field
                    item['text'] = structured_data

                    # Save after each table is processed
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    
                progress.advance(task)
            except Exception as e:
                console.print(f"Error processing table: {str(e)}", style="red")
                logger.error(f"Error processing table: {str(e)}")

        # Add the title processing task after the existing tasks
        task = progress.add_task(
            f"Processing titles", 
            total=len(titleElements)
        )

        for idx, item in enumerate(titleElements, 1):
            progress.update(task, description=f"Enriching titles: {idx}/{len(titleElements)}")
            try:
                title_content = item['text']
                enriched_title = enrich_title(title_content)
                print(f"Generated enriched title {idx}: {enriched_title}")  # Debugging output

                item['text'] = enriched_title

                # Save after each title is processed
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                progress.advance(task)
            except Exception as e:
                console.print(f"Error processing title: {str(e)}", style="red")
                logger.error(f"Error processing title: {str(e)}")

        # Final save of all changes
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            console.print("Successfully saved all changes", style="green")
        except Exception as final_save_error:
            console.print(f"Error in final save: {str(final_save_error)}", style="red")

def summarize_image(image_base64):
    """
    Generates a summary of an image using OpenAI's GPT-4 Vision model.

    Args:
        image_base64 (str): Base64-encoded image data.

    Returns:
        str: A text summary of the image content.
    """
    client = OpenAI(api_key=global_config.api_keys.openai_api_key)
    
    prompt = """You are an image summarizing agent. I will be giving you an image and you will provide a summary describing 
    the image, starting with "An image", or "An illustration", or "A diagram:", or "A logo:" or "A symbol:". If it contains a part, 
    you will try to identify the part and if it shows an action (such as a person cleaning 
    a pool or a woman holding a pool cleaning product) you will call those out. If it is a symbol, just give the symbol
    a meaningful name such as "warning symbol" or "attention!"
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=300,
        temperature=0
    )
    
    return response.choices[0].message.content

# Add the new enrich_title function at the module level, after the existing functions
def enrich_title(title_text):
    """
    Enriches title text with appropriate tags using rule-based processing.
    
    Args:
        title_text (str): The title text to be enriched
        
    Returns:
        str: Enriched title text with appropriate tags
    """
    # First pass - identify and tag multi-word phrases
    phrase_patterns = [
        # Multi-word legal terms
        (r'\b((?:license|service|maintenance|support|software|subscription)\s+(?:agreement|contract)s?)\b', '<LEGAL>'),
        
        # Company names - match any capitalized multi-word sequence followed by company indicators
        (r'\b([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)+\s*(?:Inc\.|LLC|Ltd\.|Corp\.|Corporation|Company|Co\.|Holdings|Group)?)\b', '<COMPANY>'),
        
        # Sample/Test companies or parties
        (r'\b((?:SAMPLE|TEST)\s+(?:LICENSOR|LICENSEE|VENDOR|CUSTOMER|SUPPLIER|CONTRACTOR|PARTNER|BUYER|SELLER|PARTY))\b', '<PARTY>')
    ]
    
    # Apply phrase patterns first
    enriched_text = title_text
    for pattern, tag_type in phrase_patterns:
        matches = re.finditer(pattern, enriched_text, re.IGNORECASE)
        for match in reversed(list(matches)):
            start, end = match.span()
            matched_text = enriched_text[start:end]
            # Check if matched text looks like a company name (has capital letters)
            if tag_type == '<COMPANY>' and not re.search(r'[A-Z]', matched_text):
                continue
            # For company names, also tag as PARTY if they appear to be a contract party
            if tag_type == '<COMPANY>' and re.search(r'\b(licensor|licensee|vendor|customer)\b', enriched_text[max(0, start-10):end+10], re.IGNORECASE):
                enriched_text = (
                    enriched_text[:start] + 
                    f"<COMPANY><PARTY>{matched_text}</PARTY></COMPANY>" +
                    enriched_text[end:]
                )
            else:
                enriched_text = (
                    enriched_text[:start] + 
                    f"{tag_type}{matched_text}</{tag_type.strip('<>')}" +
                    enriched_text[end:]
                )

    # Second pass - single word patterns
    single_word_patterns = [
        # Individual legal terms (if not already part of a phrase)
        (r'\b(agreement|contract|license|amendment|addendum|deed|memorandum|terms|conditions)\b', '<LEGAL>'),
        
        # Individual business relationship terms
        (r'\b(licensor|licensee|vendor|customer|supplier|contractor|partner|buyer|seller|party|parties)\b', '<PARTY>'),
        
        # Product/Service keywords
        (r'\b(service|product|software|platform|system|solution|equipment|goods)\b', '<PRODUCT>'),
        
        # Status indicators
        (r'\b(draft|final|revised|amended|executed|confidential|private)\b', '<STATUS>'),
        
        # Date patterns
        (r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+\d{4}\b', '<DATE>'),
        
        # Reference/Version numbers
        (r'\b[A-Z0-9]+-[A-Z0-9]+(?:-[A-Z0-9]+)*\b|\bv\d+(?:\.\d+)*\b|#\d+\b', '<ID>'),
        
        # Territory/Jurisdiction
        (r'\b(?:worldwide|global|international|national|regional|domestic)\b', '<TERRITORY>')
    ]

    # Apply single word patterns
    for pattern, tag_type in single_word_patterns:
        matches = re.finditer(pattern, enriched_text, re.IGNORECASE)
        for match in reversed(list(matches)):
            start, end = match.span()
            # Check if this text is already tagged
            if re.search(r'<[^>]+>[^<]*' + re.escape(enriched_text[start:end]), enriched_text):
                continue
            matched_text = enriched_text[start:end]
            enriched_text = (
                enriched_text[:start] + 
                f"{tag_type}{matched_text}</{tag_type.strip('<>')}" +
                enriched_text[end:]
            )
    
    return enriched_text