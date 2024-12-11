"""Helper functions for document processing."""

try:
    from .enrichments import enrich_json_with_summaries
except ImportError as e:
    print(f"Warning: Could not import enrichments: {e}")

try:
    from .pdf_ingest import process_pdf, PDFProcessor
except ImportError as e:
    print(f"Warning: Could not import pdf_ingest: {e}")

__all__ = ['enrich_json_with_summaries', 'process_pdf', 'PDFProcessor']