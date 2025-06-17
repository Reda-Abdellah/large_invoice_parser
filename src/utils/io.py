from pathlib import Path
from typing import Any, Dict, Optional

from ..utils.pdf_converter import PDFToMarkdownConverter


def is_pdf_file(file_path: str) -> bool:
    """Check if the input file is a PDF"""
    return Path(file_path).suffix.lower() == '.pdf'

def convert_pdf_to_markdown(pdf_path: str, config: Dict[str, Any]) -> str:
    """Convert PDF to markdown using marker"""
    try:
        converter = PDFToMarkdownConverter(config)
        markdown_content = converter.convert_pdf_to_markdown(pdf_path)
        
        # Optionally save the converted markdown for debugging
        if config.get('save_converted_markdown', False):
            results_dir = Path(config.get('results_dir', 'results'))
            # Create results directory if it doesn't exist
            results_dir.mkdir(parents=True, exist_ok=True)
            
            markdown_path = results_dir / f"{Path(pdf_path).stem}_converted.md"
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Converted markdown saved to: {markdown_path}")
        
        return markdown_content
        
    except Exception as e:
        raise RuntimeError(f"Failed to convert PDF to markdown: {str(e)}")

def read_input_file(input_file: str, config: Dict[str, Any]) -> tuple[str, Optional[str]]:
    """Read input file, converting PDF to markdown if necessary"""
    converted_path = None
    
    if is_pdf_file(input_file):
        print(f"PDF input detected: {input_file}")
        print("Converting PDF to markdown...")
        
        markdown_content = convert_pdf_to_markdown(input_file, config)
        
        # Save converted markdown if requested
        if config.get('save_converted_markdown', True):
            results_dir = Path(config.get('results_dir', 'results'))
            results_dir.mkdir(parents=True, exist_ok=True)
            
            converted_path = results_dir / f"{Path(input_file).stem}_converted.md"
            with open(converted_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Converted markdown saved to: {converted_path}")
        
        return markdown_content, converted_path
    else:
        print(f"Markdown input detected: {input_file}")
        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                return file.read(), None
        except Exception as e:
            raise RuntimeError(f"Failed to read markdown file: {str(e)}")
