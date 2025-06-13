# src/processors/structure_extractor.py
import re
import markdown
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
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
            Analyze this construction/engineering offer document and extract its hierarchical structure.
            Focus on identifying:
            1. Main offer sections (# headers) - these become BASE groups
            2. Sub-sections (## headers) - these become SUB groups  
            3. Item categories (### headers) - these contain actual offer items
            4. Technical specifications and pricing areas
            
            Document:
            {markdown_content}
            
            Look for patterns like:
            - Work categories (CFC codes, trade sections)
            - Material specifications (pipes, equipment, etc.)
            - Labor categories
            - Technical descriptions with quantities and units
            
            Return a structured analysis with:
            - Section titles and hierarchy levels
            - Whether section contains items vs. sub-groups
            - Estimated content type (materials, labor, specifications)
            
            Format as a structured list showing the offer hierarchy.
            """
        )
    
    def extract_structure_markdown(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Extract structure using markdown parsing for offer documents"""
        html = markdown.markdown(markdown_content)
        soup = BeautifulSoup(html, 'html.parser')
        
        structure = []
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for header in headers:
            level = int(header.name[1])
            title = header.get_text().strip()
            
            # Get content until next header of same or higher level
            content = self._extract_section_content(header, level)
            
            # Analyze content type for offer processing
            content_type = self._analyze_content_type(title, content)
            
            structure.append({
                'title': title,
                'level': level,
                'content': content,
                'content_type': content_type,
                'start_position': str(header),
                'estimated_items': self._estimate_item_count(content)
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
    
    def _analyze_content_type(self, title: str, content: str) -> str:
        """Analyze what type of offer content this section contains"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Check for different content types
        if any(keyword in title_lower for keyword in ['cfc', 'lot', 'poste', 'chapitre']):
            return 'work_category'
        elif any(keyword in content_lower for keyword in ['dn ', 'mm', 'kg', 'm²', 'm³', 'pcs']):
            return 'technical_items'
        elif any(keyword in content_lower for keyword in ['tuyau', 'tube', 'pipe', 'equipment']):
            return 'materials'
        elif any(keyword in content_lower for keyword in ['installation', 'montage', 'pose']):
            return 'labor'
        elif any(keyword in content_lower for keyword in ['€', 'eur', 'prix', 'price']):
            return 'pricing'
        else:
            return 'general'
    
    def _estimate_item_count(self, content: str) -> int:
        """Estimate how many offer items this section might contain"""
        # Look for patterns that suggest individual items
        lines = content.split('\n')
        item_indicators = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for item-like patterns
            if any(pattern in line.lower() for pattern in ['dn ', 'mm', '€', 'eur']):
                item_indicators += 1
            elif re.search(r'\d+\s*(m|kg|pcs|h)\b', line.lower()):
                item_indicators += 1
            elif line.startswith(('- ', '* ', '• ')):
                item_indicators += 1
        
        return max(0, item_indicators)
    
    def enhance_structure_with_llm(self, structure: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to enhance structure understanding for offer processing"""
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
        
        try:
            enhanced_structure = self.llm.invoke(
                self.structure_prompt.format(markdown_content=structure_text)
            )
            
            # Return enhanced structure with original data
            return {
                'sections': structure,
                'llm_analysis': enhanced_structure,
                'total_sections': len(structure),
                'estimated_total_items': sum(s.get('estimated_items', 0) for s in structure)
            }
            
        except Exception as e:
            print(f"Warning: LLM structure enhancement failed: {e}")
            # Return basic structure without LLM enhancement
            return {
                'sections': structure,
                'llm_analysis': None,
                'total_sections': len(structure),
                'estimated_total_items': sum(s.get('estimated_items', 0) for s in structure)
            }
    
    def _truncate_for_context(self, text: str) -> str:
        """Truncate text to fit within context window"""
        max_chars = self.config.get('context_window_size', 8192) * 3  # Rough char-to-token ratio
        if len(text) > max_chars:
            return text[:max_chars] + "\n\n[Content truncated due to context window limits]"
        return text
    
    def _format_structure_for_llm(self, structure: List[Dict[str, Any]]) -> str:
        """Format structure for LLM analysis"""
        formatted = []
        formatted.append("OFFER DOCUMENT STRUCTURE ANALYSIS:")
        formatted.append("=" * 50)
        
        for section in structure:
            indent = "  " * (section['level'] - 1)
            formatted.append(f"{indent}• {section['title']} (Level {section['level']})")
            formatted.append(f"{indent}  Type: {section.get('content_type', 'unknown')}")
            formatted.append(f"{indent}  Est. Items: {section.get('estimated_items', 0)}")
            
            if section['content']:
                content_preview = section['content'][:150] + "..." if len(section['content']) > 150 else section['content']
                formatted.append(f"{indent}  Preview: {content_preview}")
            formatted.append("")
        
        return "\n".join(formatted)
