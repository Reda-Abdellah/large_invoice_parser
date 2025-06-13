# src/processors/structure_extractor.py
import re
import markdown
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
from ..models.invoice_models import InvoiceSection, DocumentStructure
from ..utils.ollama_client import EnhancedOllamaClient

class StructureExtractor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_client = EnhancedOllamaClient(
            base_url=config.get('ollama_base_url', 'http://localhost:11434'),
            context_window_size=config.get('context_window_size', 8192),
            timeout=config.get('timeout', 300)
        )
        
        # Use smaller context for structure extraction (lighter model)
        structure_context_size = min(
            config.get('context_window_size', 8192), 
            4096  # Cap at 4k for structure extraction
        )
        
        self.llm = self.ollama_client.create_llm_with_context(
            config.get('structure_model', 'llama3.2:3b'),
            structure_context_size
        )
        
        self.structure_prompt = PromptTemplate(
            input_variables=["markdown_content"],
            template="""
            Analyze this markdown document and extract its hierarchical structure.
            Focus on identifying:
            1. Main sections (# headers)
            2. Subsections (## headers)
            3. Sub-subsections (### headers)
            4. Key content areas that contain invoice data
            
            Document:
            {markdown_content}
            
            Return a simple hierarchical structure with:
            - Section titles
            - Header levels (1-6)
            - Brief content summary for each section
            
            Format as a structured list with indentation showing hierarchy.
            """
        )
    
    def extract_structure_markdown(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Extract structure using markdown parsing"""
        html = markdown.markdown(markdown_content)
        soup = BeautifulSoup(html, 'html.parser')
        
        structure = []
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for header in headers:
            level = int(header.name[1])
            title = header.get_text().strip()
            
            # Get content until next header of same or higher level
            content = self._extract_section_content(header, level)
            
            structure.append({
                'title': title,
                'level': level,
                'content': content,
                'start_position': str(header)
            })
        
        return structure
    
    def _extract_section_content(self, header, level: int) -> str:
        """Extract content between current header and next header of same/higher level"""
        content_parts = []
        current = header.next_sibling
        
        while current:
            if current.name and current.name.startswith('h'):
                next_level = int(current.name[1])
                if next_level <= level:
                    break
            
            if hasattr(current, 'get_text'):
                content_parts.append(current.get_text())
            elif isinstance(current, str):
                content_parts.append(current)
            
            current = current.next_sibling
        
        return ' '.join(content_parts).strip()
    
    def enhance_structure_with_llm(self, structure: List[Dict[str, Any]]) -> DocumentStructure:
        """Use LLM to enhance structure understanding with context window management"""
        structure_text = self._format_structure_for_llm(structure)
        
        # Check if content fits in context window
        context_check = self.ollama_client.check_context_requirements(
            structure_text, 
            self.config.get('context_window_size', 8192)
        )
        
        if not context_check['fits_in_context']:
            print(f"Warning: Structure text ({context_check['estimated_tokens']} tokens) "
                  f"exceeds context window ({context_check['context_size']} tokens). "
                  f"Truncating content...")
            structure_text = self._truncate_for_context(structure_text)
        
        enhanced_structure = self.llm.invoke(
            self.structure_prompt.format(markdown_content=structure_text)
        )
        
        # Convert to structured format
        sections = []
        for section_data in structure:
            section = InvoiceSection(
                title=section_data['title'],
                level=section_data['level'],
                content=section_data['content']
            )
            sections.append(section)
        
        return DocumentStructure(sections=sections)
    
    def _truncate_for_context(self, text: str) -> str:
        """Truncate text to fit within context window"""
        max_chars = self.config.get('context_window_size', 8192) * 3  # Rough char-to-token ratio
        if len(text) > max_chars:
            return text[:max_chars] + "\n\n[Content truncated due to context window limits]"
        return text
    
    def _format_structure_for_llm(self, structure: List[Dict[str, Any]]) -> str:
        """Format structure for LLM analysis"""
        formatted = []
        for section in structure:
            indent = "  " * (section['level'] - 1)
            formatted.append(f"{indent}- {section['title']} (Level {section['level']})")
            if section['content']:
                content_preview = section['content'][:200] + "..." if len(section['content']) > 200 else section['content']
                formatted.append(f"{indent}  Content: {content_preview}")
        
        return "\n".join(formatted)
