# src/utils/pdf_converter.py
from typing import Dict, Any, Optional
import tempfile
import os
from pathlib import Path

class PDFToMarkdownConverter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.marker_config = config.get('marker', {})
    
    def convert_pdf_to_markdown(self, pdf_path: str) -> str:
        """Convert PDF to markdown using marker"""
        try:
            # Import marker (install with: pip install marker-pdf)
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models
            
            # Load marker models (this might take a while on first run)
            print("Loading marker models...")
            model_lst = load_all_models()
            
            # Convert PDF to markdown
            print(f"Converting PDF: {pdf_path}")
            
            # Configure marker settings
            marker_kwargs = {
                'max_pages': self.marker_config.get('max_pages', None),
                'langs': self.marker_config.get('languages', None),
                'batch_multiplier': self.marker_config.get('batch_multiplier', 2),
            }
            
            # Remove None values
            marker_kwargs = {k: v for k, v in marker_kwargs.items() if v is not None}
            
            # Convert the PDF
            full_text, images, out_meta = convert_single_pdf(
                pdf_path, 
                model_lst,
                **marker_kwargs
            )
            
            # Post-process the markdown if needed
            processed_markdown = self._post_process_markdown(full_text)
            
            print(f"✅ PDF conversion complete ({len(processed_markdown)} characters)")
            
            # Save images if requested
            if self.config.get('save_extracted_images', False) and images:
                self._save_extracted_images(images, pdf_path)
            
            return processed_markdown
            
        except ImportError:
            raise RuntimeError(
                "marker-pdf not installed. Please install with: pip install marker-pdf"
            )
        except Exception as e:
            raise RuntimeError(f"PDF conversion failed: {str(e)}")
    
    def _post_process_markdown(self, markdown_content: str) -> str:
        """Post-process the converted markdown"""
        # Clean up common conversion artifacts
        lines = markdown_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines at the beginning
            if not cleaned_lines and not line:
                continue
            
            # Clean up excessive whitespace
            if line:
                cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1]:  # Only add empty line if previous wasn't empty
                cleaned_lines.append('')
        
        # Join and clean up
        cleaned_content = '\n'.join(cleaned_lines)
        
        # Additional cleaning based on config
        if self.config.get('remove_page_numbers', True):
            cleaned_content = self._remove_page_numbers(cleaned_content)
        
        if self.config.get('fix_table_formatting', True):
            cleaned_content = self._fix_table_formatting(cleaned_content)
        
        return cleaned_content
    
    def _remove_page_numbers(self, content: str) -> str:
        """Remove page numbers and headers/footers"""
        import re
        
        # Remove standalone page numbers
        content = re.sub(r'\n\s*\d+\s*\n', '\n', content)
        
        # Remove page headers/footers (lines that are very short and contain only numbers/basic text)
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip lines that look like page numbers or headers
            if len(line.strip()) < 10 and re.match(r'^\s*[\d\-\s]+\s*$', line):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _fix_table_formatting(self, content: str) -> str:
        """Fix common table formatting issues"""
        # This is a basic implementation - you might need to adjust based on your PDFs
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Fix table separators
            if '|' in line and not line.strip().startswith('|'):
                # Ensure table rows start with |
                line = '| ' + line.lstrip()
            
            if '|' in line and not line.strip().endswith('|'):
                # Ensure table rows end with |
                line = line.rstrip() + ' |'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _save_extracted_images(self, images: Dict[str, Any], pdf_path: str):
        """Save extracted images to disk"""
        try:
            pdf_name = Path(pdf_path).stem
            image_dir = Path(f"{pdf_name}_images")
            image_dir.mkdir(exist_ok=True)
            
            for i, (image_name, image_data) in enumerate(images.items()):
                image_path = image_dir / f"image_{i}_{image_name}"
                with open(image_path, 'wb') as f:
                    f.write(image_data)
            
            print(f"📸 Saved {len(images)} images to {image_dir}")
            
        except Exception as e:
            print(f"⚠️  Could not save images: {e}")
