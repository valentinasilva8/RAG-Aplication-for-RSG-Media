"""
-----------------------------------------------------------------
(C) 2024 Prof. Tiran Dagan, FDU University. All rights reserved.
-----------------------------------------------------------------

PDF Ingestion Module

This module provides functionality for processing PDF documents using the Unstructured.io API.
Key features:
- PDF document ingestion and parsing
- Content chunking and structuring 
- Vector embeddings generation
- Document annotation and visualization
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Optional
import json
import hashlib
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import (
    Title, NarrativeText, ListItem, Table, Image
)

from helpers.pdf_annotation import annotate_pdf_pages
from helpers.enrichments import enrich_json_with_summaries
from helpers.file_and_folder import get_files_with_extension, get_pdf_page_count
from helpers.config import load_config, get_global_config

from rich.console import Console
from unstructured_ingest.v2.pipeline.pipeline import Pipeline
from unstructured_ingest.v2.interfaces import ProcessorConfig
from unstructured_ingest.v2.processes.connectors.local import (
    LocalIndexerConfig,
    LocalDownloaderConfig,
    LocalConnectionConfig,
    LocalUploaderConfig
)
from unstructured_ingest.v2.processes.partitioner import PartitionerConfig
from unstructured_ingest.v2.processes.chunker import ChunkerConfig
from unstructured_ingest.v2.logger import logger as unstructured_logger

# Load configuration at module level
load_config()

@dataclass
class PipelineConfigs:
    """Configuration container for Unstructured.io pipeline settings
    
    Attributes:
        processor_config: Settings for the main processor
        partitioner_config: PDF partitioning configuration
        indexer_config: Document indexing settings
        downloader_config: File download settings
        connection_config: API connection parameters
        uploader_config: Output file handling
        chunker_config: Optional chunking parameters
    """

class PDFProcessor:
    """Main PDF processing class that handles document ingestion and structuring
    
    Handles the complete pipeline of:
    - Loading and validating PDFs
    - Extracting content and structure
    - Generating chunks and annotations
    - Managing output files and directories
    """

    def __init__(self):
        self.console = Console()
        self.setup_logging()
        
        # Get the global config
        self.global_config = get_global_config()
        if not self.global_config:
            raise RuntimeError("Failed to load configuration")
        
        # Set up directories using self.global_config
        self.output_dir = os.path.realpath(self.global_config.directories.output_dir)
        self.partitioned_dir = os.path.join(self.output_dir, '01_partitioned')
        self.chunked_dir = os.path.join(self.output_dir, '02_chunked')
        self.work_dir = os.path.join(self.output_dir, 'temp')
        
        # Create directories
        for directory in [self.work_dir, self.partitioned_dir, self.chunked_dir]:
            os.makedirs(directory, exist_ok=True)

    def setup_logging(self):
        """Configure logging settings"""
        unstructured_logger.setLevel(logging.CRITICAL)
        unstructured_logger.disabled = False

    def create_pipeline_configs(self, input_dir: str, output_dir: str, is_chunking: bool = False) -> PipelineConfigs:
        """Create configuration objects for the processing pipeline
        
        Args:
            input_dir: Source directory for PDFs
            output_dir: Target directory for output
            is_chunking: Whether to enable content chunking
            
        Returns:
            PipelineConfigs: Complete pipeline configuration
        """
        print(f"\nCreating pipeline config:")
        print(f"Input dir: {input_dir}")
        print(f"Output dir: {output_dir}")
        print(f"Is chunking: {is_chunking}")
        
        processor_config = ProcessorConfig(
            num_processes=3,
            verbose=False,
            tqdm=True,
            work_dir=self.work_dir
        )
        
        partitioner_config = PartitionerConfig(
            partition_by_api=True,
            strategy="hi_res",
            api_key=self.global_config.api_keys.unstructured_api_key,
            partition_endpoint=self.global_config.api_keys.unstructured_url,
            extract_image_block_to_payload=True,
            additional_partition_args={
                "coordinates": True,
                "extract_image_block_types": ["Image", "Table"],
                "split_pdf_page": True,
                "split_pdf_allow_failed": True,
                "split_pdf_concurrency_level": 15
            }
        )
        
        configs = PipelineConfigs(
            processor_config=processor_config,
            partitioner_config=partitioner_config,
            indexer_config=LocalIndexerConfig(input_path=input_dir),
            downloader_config=LocalDownloaderConfig(),
            connection_config=LocalConnectionConfig(),
            uploader_config=LocalUploaderConfig(output_dir=output_dir)
        )
        
        if is_chunking:
            print("\nSetting up chunking config:")
            configs.chunker_config = ChunkerConfig(
                chunking_strategy="by_title",
                chunk_by_api=True,
                chunk_api_key=self.global_config.api_keys.unstructured_api_key,
                similarity_threshold=0.3,
                chunk_max_characters=3000,
                chunk_overlap=150,
                preserve_markup=True,
                additional_chunk_args={
                    "preserve_tags": True,
                    "xml_tags_to_preserve": [
                        "COMPANY", "PARTY", "DATE", "ADDRESS", "CONTACT", 
                        "RIGHTS", "TERRITORY", "TERM", "PAYMENT", "LEGAL", 
                        "PRODUCT", "ID", "STATUS"
                    ],
                    "skip_tag_stripping": True,
                    "keep_xml_tags": True,
                    "xml_keep_tags": True
                }
            )
            print("Chunking config created successfully")
            
        return configs

    def process_pdfs(self, input_dir: str, pdf_files: List[str]):
        """Process a list of PDF files through the complete pipeline
        
        Args:
            input_dir: Directory containing input PDF files
            pdf_files: List of PDF filenames to process
            
        Returns:
            bool: True if processing succeeded, False otherwise
        """
        status = True
        self.console.print(f"Processing {len(pdf_files)} PDF files...", style="blue")
        
        # Debug directory structure
        print("\nDirectory Structure:")
        print(f"Input directory: {input_dir}")
        print(f"Partitioned directory: {self.partitioned_dir}")
        print(f"Chunked directory: {self.chunked_dir}")
        print(f"Work directory: {self.work_dir}")
        
        # Check directory contents before processing
        print("\nInitial directory contents:")
        print(f"Input dir contents: {os.listdir(input_dir)}")
        print(f"Partitioned dir contents: {os.listdir(self.partitioned_dir)}")
        print(f"Chunked dir contents: {os.listdir(self.chunked_dir)}")
        
        # 1. Run partitioning pipeline
        self.console.print("Starting partitioning...", style="blue")
        configs = self.create_pipeline_configs(input_dir, self.partitioned_dir)
        try:
            self._run_pipeline(configs)
        except Exception as e:
            self.console.print(f"Error during partitioning: {str(e)}", style="red")
            status = False
        
        # 2. Enrich partitions
        if status:
            self.console.print("Enhancing partitions with LLM summaries...", style="blue")
            try:
                self.enrich_partitions()
            except Exception as e:
                self.console.print(f"Error during enrichment: {str(e)}", style="red")
                status = False
        
        # 3. Chunk partitions
        if status:
            self.console.print("\nStarting chunking...", style="blue")
            chunking_configs = self.create_pipeline_configs(
                self.partitioned_dir, 
                self.chunked_dir, 
                is_chunking=True
            )
            try:
                print("\nChunking configuration:")
                print(f"Input path: {chunking_configs.indexer_config.input_path}")
                print(f"Output dir: {chunking_configs.uploader_config.output_dir}")
                print(f"Chunking strategy: {chunking_configs.chunker_config.chunking_strategy}")
                
                self._run_pipeline(chunking_configs)
                
                # Check directory contents after chunking
                print("\nPost-chunking directory contents:")
                print(f"Chunked dir contents: {os.listdir(self.chunked_dir)}")
                
            except Exception as e:
                self.console.print(f"Error during chunking: {str(e)}", style="red")
                print(f"Full chunking error: {str(e)}")
                status = False

        self.cleanup_file_extensions()
        
        # After chunking
        print(f"Checking chunked directory contents:")
        if os.path.exists(self.chunked_dir):
            print(os.listdir(self.chunked_dir))
        else:
            print("Chunked directory does not exist!")
        
        # 4. Annotate PDF pages using coordinates found in partitioned JSON files
        for pdf_file in pdf_files:
            basename = os.path.basename(pdf_file)
            pdf_path = os.path.join(input_dir, basename)
            try:
                num_pages = get_pdf_page_count(pdf_path)
                annotate_pdf_pages(basename, num_pages)
            except FileNotFoundError:
                self.console.print(f"Error: Could not find PDF file at {pdf_path}", style="red")
                logging.error(f"PDF file not found: {pdf_path}")
                status = False
            except Exception as e:
                self.console.print(f"Error processing {pdf_file}: {str(e)}", style="red")
                logging.error(f"Error processing {pdf_file}: {str(e)}")
                status = False
        
        return status

    def enrich_partitions(self):
        """Enhance partition JSON metadata with summaries"""
        self.console.print("Enhancing image and table metadata...", style="blue")
        # Only process partitioned files
        json_files = get_files_with_extension(self.partitioned_dir, '.json')
        
        for json_file in json_files:
            try:
                enrich_json_with_summaries(json_file)
                self.console.print(f"Successfully enriched {json_file}", style="green")
            except Exception as e:
                self.console.print(f"Error processing {json_file}: {str(e)}", style="red")
                logging.error(f"Error processing {json_file}: {str(e)}")

    def cleanup_file_extensions(self):
        """Clean up duplicate .json extensions"""
        chunked_files = [
            f for f in os.listdir(self.chunked_dir) 
            if f.endswith('.json.json')
        ]
        
        for file in chunked_files:
            old_path = os.path.join(self.chunked_dir, file)
            new_path = os.path.join(self.chunked_dir, file.replace('.json.json', '.json'))
            os.rename(old_path, new_path)
            
        self.console.print(
            f"Renamed {len(chunked_files)} files to remove duplicate .json extension", 
            style="green"
        )

    def _run_pipeline(self, configs: PipelineConfigs):
        """Run the Unstructured.io pipeline with given configurations"""
        print("\nStarting pipeline execution:")
        try:
            pipeline = Pipeline.from_configs(
                context=configs.processor_config,
                indexer_config=configs.indexer_config,
                downloader_config=configs.downloader_config,
                source_connection_config=configs.connection_config,
                partitioner_config=configs.partitioner_config,
                chunker_config=configs.chunker_config,
                uploader_config=configs.uploader_config
            )
            print("Pipeline created successfully")
            
            pipeline.run()
            print("Pipeline execution completed")
            
        except Exception as e:
            print(f"Pipeline execution failed: {str(e)}")
            raise

    def process_single_pdf(self, pdf_path: str) -> tuple[int, str]:
        """Process a single PDF file with detailed error reporting
        
        Args:
            pdf_path (str): Full path to the PDF file
            
        Returns:
            tuple[int, str]: Status code (0=fail, 1=success) and error message if any
        """
        try:
            input_dir = os.path.dirname(pdf_path)
            basename = os.path.basename(pdf_path)
            
            # 1. Run partitioning pipeline
            self.console.print(f"Partitioning {basename}...", style="blue")
            configs = self.create_pipeline_configs(input_dir, self.partitioned_dir)
            try:
                self._run_pipeline(configs)
            except Exception as e:
                return 0, f"Ingest failed: {str(e)}"

            # 2. Enrich partitions
            self.console.print("Enhancing partitions with LLM summaries...", style="blue")
            json_file = os.path.join(self.partitioned_dir, f"{basename}.json")
            if not os.path.exists(json_file):
                return 0, f"Partition JSON not found at {json_file}"
            
            try:
                enrich_json_with_summaries(json_file)
            except Exception as e:
                return 0, f"Enrichment failed: {str(e)}"

            # 3. Chunk partitions
            self.console.print("Chunking document...", style="blue")
            try:
                chunking_configs = self.create_pipeline_configs(
                    self.partitioned_dir,
                    self.chunked_dir,
                    is_chunking=True
                )
                self._run_pipeline(chunking_configs)
            except Exception as e:
                return 0, f"Chunking failed: {str(e)}"

            self.cleanup_file_extensions()

            # 4. Annotate PDF pages
            try:
                num_pages = get_pdf_page_count(pdf_path)
                annotate_pdf_pages(basename, num_pages)
            except FileNotFoundError:
                return 0, f"PDF file not found during annotation: {pdf_path}"
            except Exception as e:
                return 0, f"PDF annotation failed: {str(e)}"

            # If we made it here, everything succeeded
            return 1, "Success"

        except Exception as e:
            return 0, f"Unexpected error during processing: {str(e)}"

def process_pdf(pdf_path: str) -> Optional[str]:
    """
    Process a PDF file and return path to JSON output.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        Optional[str]: Path to the output JSON file, or None if processing fails
    """
    try:
        # Create output directories if they don't exist
        output_dir = os.path.join("data", "output", "temp", "index")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate a unique filename based on PDF content
        with open(pdf_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:12]
        output_file = os.path.join(output_dir, f"{file_hash}.json")
        
        # If already processed, return existing file
        if os.path.exists(output_file):
            return output_file
            
        # Process PDF
        elements = partition_pdf(
            pdf_path,
            strategy="hi_res",
            extract_images_in_pdf=True,
            infer_table_structure=True,
            include_page_breaks=True
        )
        
        # Convert elements to JSON-serializable format
        processed_elements = []
        for element in elements:
            element_dict = {
                "type": element.__class__.__name__,
                "text": str(element),
                "metadata": element.metadata
            }
            
            # Add specific processing for different element types
            if isinstance(element, (Title, NarrativeText, ListItem)):
                element_dict["text"] = str(element)
            elif isinstance(element, Table):
                element_dict["text"] = str(element)
                element_dict["metadata"]["table_data"] = element.metadata.get("text", "")
            elif isinstance(element, Image):
                element_dict["metadata"]["image_path"] = element.metadata.get("image_path", "")
                
            processed_elements.append(element_dict)
            
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_elements, f, indent=2, ensure_ascii=False)
            
        return output_file
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None