#!/usr/bin/env python3
"""
Convert all PDF research papers to Markdown format for AI-assisted thesis writing.

This script:
- Recursively processes all PDFs in research-papers/
- Outputs to research-knowledge-base/ preserving folder structure
- Generates metadata index for tracking conversions
- Uses PyMuPDF for fast, CPU-efficient text extraction
- Uses parallel processing to maximize CPU/RAM utilization
- Skips failures and logs errors
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import sys
import re

try:
    import fitz  # PyMuPDF
    from tqdm import tqdm
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Install with: pip install PyMuPDF tqdm")
    sys.exit(1)


# Configuration
INPUT_DIR = Path("research-papers")
OUTPUT_DIR = Path("research-knowledge-base")
ERROR_LOG = Path("conversion_errors.log")
METADATA_FILE = OUTPUT_DIR / "index.json"

# Parallel processing configuration
# Use all available CPU cores for parallel processing (PyMuPDF is lightweight)
MAX_WORKERS = multiprocessing.cpu_count()


def setup_logging():
    """Configure logging for error tracking."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(ERROR_LOG),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def find_all_pdfs(base_dir: Path) -> List[Path]:
    """Recursively find all PDF files in the research papers directory."""
    pdfs = list(base_dir.rglob("*.pdf"))
    logging.info(f"Found {len(pdfs)} PDF files to convert")
    return sorted(pdfs)


def clean_text(text: str) -> str:
    """Clean extracted text for better markdown formatting."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove weird characters but keep common symbols
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
    return text.strip()


def extract_title_from_text(text: str, pdf_name: str) -> str:
    """Try to extract paper title from first page text."""
    lines = text.split('\n')[:10]  # Check first 10 lines
    for line in lines:
        line = line.strip()
        # Title is usually the first substantial line (>10 chars, not a number)
        if len(line) > 10 and not line.replace(' ', '').isdigit():
            return line
    # Fallback to filename
    return pdf_name.replace('.pdf', '').replace('_', ' ').replace('-', ' ')


def convert_pdf_to_markdown(
    pdf_path: Path,
    output_base: Path,
    input_base: Path
) -> Dict:
    """
    Convert a single PDF to Markdown using PyMuPDF and return metadata.
    
    Args:
        pdf_path: Path to input PDF
        output_base: Base output directory
        input_base: Base input directory (to preserve structure)
    
    Returns:
        Dict with conversion metadata
    """
    metadata = {
        "pdf_path": str(pdf_path.relative_to(input_base)),
        "markdown_path": None,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "page_count": 0,
        "file_size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2)
    }
    
    try:
        # Preserve directory structure
        relative_path = pdf_path.relative_to(input_base)
        output_subdir = output_base / relative_path.parent
        output_subdir.mkdir(parents=True, exist_ok=True)
        
        # Prepare output markdown file path
        md_filename = pdf_path.stem + ".md"
        md_path = output_subdir / md_filename
        
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        metadata["page_count"] = len(doc)
        
        # Extract text from all pages
        markdown_content = []
        
        # Add header with paper info
        title = extract_title_from_text(doc[0].get_text() if len(doc) > 0 else "", pdf_path.name)
        markdown_content.append(f"# {title}\n\n")
        markdown_content.append(f"**Source:** `{pdf_path.name}`  \n")
        markdown_content.append(f"**Pages:** {len(doc)}  \n")
        markdown_content.append(f"**Converted:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
        markdown_content.append("---\n\n")
        
        # Extract text page by page
        for page_num, page in enumerate(doc, start=1):
            # Get text from page
            text = page.get_text()
            
            if text.strip():
                # Clean the text
                cleaned_text = clean_text(text)
                
                # Add page separator
                markdown_content.append(f"## Page {page_num}\n\n")
                markdown_content.append(cleaned_text)
                markdown_content.append("\n\n")
        
        doc.close()
        
        # Write to markdown file
        final_markdown = ''.join(markdown_content)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_markdown)
        
        metadata["markdown_path"] = str(md_path.relative_to(output_base))
        metadata["success"] = True
        
        logging.info(f"✓ Converted: {pdf_path.name} ({metadata['page_count']} pages)")
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        metadata["error"] = error_msg
        logging.error(f"✗ Failed: {pdf_path.name} - {error_msg}")
    
    return metadata


def save_metadata(metadata_list: List[Dict], output_file: Path):
    """Save conversion metadata to JSON index file."""
    summary = {
        "conversion_date": datetime.now().isoformat(),
        "total_files": len(metadata_list),
        "successful": sum(1 for m in metadata_list if m["success"]),
        "failed": sum(1 for m in metadata_list if not m["success"]),
        "files": metadata_list
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Metadata index saved to: {output_file}")


def main():
    """Main conversion workflow."""
    logger = setup_logging()
    
    # Validate input directory
    if not INPUT_DIR.exists():
        logger.error(f"Input directory not found: {INPUT_DIR}")
        sys.exit(1)
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Find all PDFs
    pdf_files = find_all_pdfs(INPUT_DIR)
    
    if not pdf_files:
        logger.warning("No PDF files found!")
        return
    
    logger.info(f"Starting conversion of {len(pdf_files)} files...")
    logger.info(f"Using PyMuPDF (fast text extraction) with {MAX_WORKERS} parallel workers")
    logger.info(f"Estimated total time: ~{len(pdf_files) * 5 / MAX_WORKERS:.0f} seconds")
    
    # Process all PDFs in parallel with progress bar
    metadata_list = []
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all conversion tasks
        future_to_pdf = {
            executor.submit(
                convert_pdf_to_markdown,
                pdf_path,
                OUTPUT_DIR,
                INPUT_DIR
            ): pdf_path
            for pdf_path in pdf_files
        }
        
        # Process completed tasks with progress bar
        with tqdm(total=len(pdf_files), desc="Converting PDFs", unit="file") as pbar:
            for future in as_completed(future_to_pdf):
                pdf_path = future_to_pdf[future]
                try:
                    metadata = future.result()
                    metadata_list.append(metadata)
                    
                    if metadata["success"]:
                        pbar.set_description(f"✓ {pdf_path.name[:30]}")
                    else:
                        pbar.set_description(f"✗ {pdf_path.name[:30]}")
                except Exception as e:
                    logger.error(f"Unexpected error processing {pdf_path.name}: {e}")
                    metadata_list.append({
                        "pdf_path": str(pdf_path.relative_to(INPUT_DIR)),
                        "success": False,
                        "error": f"Unexpected error: {str(e)}"
                    })
                
                pbar.update(1)
    
    # Save metadata index
    save_metadata(metadata_list, METADATA_FILE)
    
    # Print summary
    successful = sum(1 for m in metadata_list if m["success"])
    failed = sum(1 for m in metadata_list if not m["success"])
    
    print("\n" + "="*60)
    print("CONVERSION COMPLETE")
    print("="*60)
    print(f"Total files:      {len(metadata_list)}")
    print(f"Successful:       {successful}")
    print(f"Failed:           {failed}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Metadata index:   {METADATA_FILE}")
    print(f"Error log:        {ERROR_LOG}")
    print("="*60)
    
    if failed > 0:
        print(f"\nCheck {ERROR_LOG} for details on failed conversions")


if __name__ == "__main__":
    main()