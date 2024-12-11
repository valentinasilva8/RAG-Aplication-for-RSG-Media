"""
PDF Annotation and Visualization Module

Provides functionality for:
- Drawing bounding boxes around content elements
- Generating annotated PDF visualizations
- Creating debugging visualizations
"""

import fitz
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from PIL import Image
import os
import logging
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TextColumn, 
    BarColumn, 
    TaskProgressColumn,
    TimeRemainingColumn
)
from rich.console import Console
from .config import global_config
from .file_and_folder import get_json_file_elements

console = Console()

def setup_logging():
    """Initialize logging for PDF annotation process"""
    logger = logging.getLogger(__name__)
    file_handler = logging.FileHandler('pdf_converter.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(file_handler)

def draw_bounding_boxes(pdf_page, documents, output_filename, output_dir):
    """Generate annotated visualization of PDF page
    
    Args:
        pdf_page: PDF page object
        documents: List of document elements with coordinates
        output_filename: Original PDF path
        output_dir: Output directory for annotated images
    """
    base_filename = os.path.splitext(os.path.basename(output_filename))[0]
    complete_image_path = os.path.join(
        output_dir, 
        f"{base_filename}-{pdf_page.number + 1}-annotated.jpg"
    )
    
    if os.path.exists(complete_image_path):
        logging.info(f"Skipping existing annotation for {base_filename} page {pdf_page.number + 1}")
        return
        
    pix = pdf_page.get_pixmap()
    pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    fig, ax = plt.subplots(1, figsize=(20, 20))
    ax.imshow(pil_image)
    
    category_to_color = {
        "Title": "orchid",
        "Image": "forestgreen",
        "Table": "tomato",
        "ListItem": "gold",
        "NarrativeText": "deepskyblue",
    }
    
    boxes_drawn = 0
    for doc in documents:
        category = doc['type']
        c = doc['metadata']['coordinates']
        points = c['points']
        layout_width = c['layout_width']
        layout_height = c['layout_height']

        scaled_points = [
            (x * pix.width / layout_width, y * pix.height / layout_height)
            for x, y in points
        ]
        box_color = category_to_color.get(category, "deepskyblue")
        polygon = patches.Polygon(
            scaled_points, linewidth=2, edgecolor=box_color, facecolor="none"
        )
        ax.add_patch(polygon)
        boxes_drawn += 1
    
    legend_handles = [patches.Patch(color=color, label=category) 
                     for category, color in category_to_color.items()]
    ax.axis("off")
    ax.legend(handles=legend_handles, loc="upper right")
    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    fig.savefig(complete_image_path, format="jpg", dpi=300)
    plt.close(fig)

def annotate_pdf_pages(file_name: str, num_pages: int, progress=None):
    """Process and annotate all pages in a PDF file
    
    Args:
        file_name: Name of PDF file
        num_pages: Total number of pages
        progress: Optional progress tracking object
    """
    output_dir = global_config.directories.output_dir
    input_dir = global_config.directories.input_dir
    image_dir = os.path.join(output_dir, '03_annotated_pages')
    input_json_path = os.path.join(output_dir, '01_partitioned', file_name)
    input_file_path = os.path.join(input_dir, file_name)
    
    pdf = fitz.open(input_file_path)
    docs = get_json_file_elements(input_json_path)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress_bar:
        task = progress_bar.add_task(
            f"[cyan]Annotating PDF: {file_name}", 
            total=num_pages
        )
        
        for page_number in range(1, num_pages + 1):
            progress_bar.update(
                task,
                description=f"[cyan]Annotating page {page_number}/{num_pages}"
            )
            
            page_docs = [doc for doc in docs if doc['metadata'].get('page_number') == page_number]
            draw_bounding_boxes(pdf.load_page(page_number - 1), page_docs, input_file_path, image_dir)
            
            progress_bar.advance(task)
            
    pdf.close()
