# src/utils/pdf_converter.py
from pathlib import Path
from typing import Dict, Any
import re

class PDFToMarkdownConverter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.marker_config = config.get('marker', {})
    
    def convert_pdf_to_markdown(self, pdf_path: str) -> str:
        """Convert PDF to markdown using marker"""
        try:
            # Import marker with current API
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.output import text_from_rendered
            from marker.config.parser import ConfigParser
            
            print("Loading marker models...")
            
            # Create configuration
            config = {
                "output_format": "markdown",
            }
            
            # Add marker-specific configurations
            if self.marker_config.get('max_pages'):
                config['max_pages'] = self.marker_config['max_pages']
            
            if self.marker_config.get('languages'):
                config['langs'] = self.marker_config['languages']
            
            # Create config parser and converter
            config_parser = ConfigParser(config)
            converter = PdfConverter(
                config=config_parser.generate_config_dict(),
                artifact_dict=create_model_dict(),
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
            )
            
            print(f"Converting PDF: {pdf_path}")
            
            # Convert the PDF
            rendered = converter(pdf_path)
            
            # Extract text and images
            full_text, out_meta, images = text_from_rendered(rendered)
            
            # Post-process the markdown if needed
            processed_markdown = self._post_process_markdown(full_text)
            
            print(f"✅ PDF conversion complete ({len(processed_markdown)} characters)")
            
            # Save images if requested and images exist
            if self.config.get('save_extracted_images', False) and images:
                self._save_extracted_images(images, pdf_path)
            
            return processed_markdown
            
        except ImportError as ie:
            raise RuntimeError(
                f"PDF conversion failed: {str(ie)}. "
                "Please install the latest marker-pdf version: pip install marker-pdf"
            )
        except Exception as e:
            raise RuntimeError(f"PDF conversion failed: {str(e)}")
    
    def _post_process_markdown(self, markdown_content: str) -> str:
        """Post-process the converted markdown"""
        if not markdown_content:
            return ""
        
        # Clean up common conversion artifacts
        lines = markdown_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.rstrip()
            
            # Skip empty lines at the beginning
            if not cleaned_lines and not line:
                continue
            
            cleaned_lines.append(line)
        
        # Remove excessive empty lines
        final_lines = []
        empty_count = 0
        
        for line in cleaned_lines:
            if not line.strip():
                empty_count += 1
                if empty_count <= 2:
                    final_lines.append(line)
            else:
                empty_count = 0
                final_lines.append(line)
        
        cleaned_content = '\n'.join(final_lines)
        
        # Additional cleaning based on config
        if self.config.get('remove_page_numbers', True):
            cleaned_content = self._remove_page_numbers(cleaned_content)
        
        if self.config.get('fix_table_formatting', True):
            cleaned_content = self._fix_table_formatting(cleaned_content)
        
        return cleaned_content
    
    def _remove_page_numbers(self, content: str) -> str:
        """Remove page numbers and headers/footers"""
        content = re.sub(r'\n\s*\d+\s*\n', '\n', content)
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            if len(stripped) < 10 and re.match(r'^[\d\-\s]+$', stripped):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _fix_table_formatting(self, content: str) -> str:
        """Fix common table formatting issues"""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            if '|' in line:
                stripped = line.strip()
                
                if not stripped.startswith('|'):
                    stripped = '| ' + stripped
                
                if not stripped.endswith('|'):
                    stripped = stripped + ' |'
                
                leading_spaces = len(line) - len(line.lstrip())
                line = ' ' * leading_spaces + stripped
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _save_extracted_images(self, images: Dict[str, Any], pdf_path: str):
        """Save extracted images to disk"""
        try:
            pdf_name = Path(pdf_path).stem
            image_dir = Path(f"{pdf_name}_images")
            image_dir.mkdir(exist_ok=True)
            
            saved_count = 0
            for image_name, image_data in images.items():
                try:
                    image_path = image_dir / f"{image_name}.png"
                    
                    if hasattr(image_data, 'save'):
                        image_data.save(image_path)
                        saved_count += 1
                    else:
                        with open(image_path, 'wb') as f:
                            f.write(image_data)
                        saved_count += 1
                        
                except Exception as img_error:
                    print(f"⚠️  Could not save image {image_name}: {img_error}")
            
            if saved_count > 0:
                print(f"📸 Saved {saved_count} images to {image_dir}")
            
        except Exception as e:
            print(f"⚠️  Could not save images: {e}")
