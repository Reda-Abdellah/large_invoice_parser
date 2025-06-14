# src/processors/section_detail_analyzer.py
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
from ..utils.ollama_client import EnhancedOllamaClient
import re

class SectionDetailAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_client = EnhancedOllamaClient(
            base_url=config.get('ollama_base_url', 'http://localhost:11434'),
            context_window_size=config.get('context_window_size', 8192),
            timeout=config.get('timeout', 300)
        )
        
        self.llm = self.ollama_client.create_llm_with_context(
            config.get('analysis_model', 'llama3.2:7b'),
            config.get('context_window_size', 8192)
        )
        
        self.detail_prompt = PromptTemplate(
            input_variables=["section_content", "section_info"],
            template="""
            Analyze this specific section from a construction/engineering offer and extract detailed offer items.
            
            Section Info: {section_info}
            
            Section Content:
            {section_content}
            
            Extract detailed offer items in JSON format:
            {{
                "section_analysis": {{
                    "section_id": "section_id",
                    "section_title": "title",
                    "section_type": "work_category|materials|labor|pricing|technical_specs",
                    "group_type": "BASE|SUB",
                    "default_margin": 25
                }},
                "offer_items": [
                    {{
                        "name": "detailed item description",
                        "offer_item_type": "NORMAL|OPTIONAL|VARIANT",
                        "unit_quantity": number,
                        "unit_type": "MATERIAL|LABOR|SERVICE",
                        "unit": "m|m²|m³|kg|h|pcs|etc",
                        "unit_price": number,
                        "margin": number,
                        "article_number": "reference if available",
                        "desc_html": "HTML formatted description",
                        "is_optional": boolean,
                        "category": "item category"
                    }}
                ],
                "section_metadata": {{
                    "total_items": number,
                    "has_pricing": boolean,
                    "has_quantities": boolean,
                    "technical_specs": ["list", "of", "specs"],
                    "key_materials": ["list", "of", "materials"]
                }}
            }}
            
            Focus on extracting:
            - Individual items with quantities and units
            - Technical specifications (DN, dimensions, materials)
            - Pricing information where available
            - Article/reference numbers
            - Detailed descriptions
            
            Return valid JSON only.
            """
        )
    
    def analyze_sections_detailed(self, structure_with_delimiters: Dict[str, Any], 
                                 raw_markdown: str) -> List[Dict[str, Any]]:
        """Analyze each section in detail using delimiters"""
        sections = structure_with_delimiters.get('sections', [])
        detailed_analyses = []
        
        print("Phase 3: Detailed section-by-section analysis...")
        
        for i, section in enumerate(sections, 1):
            print(f"  Analyzing section {i}/{len(sections)}: {section.get('title', 'Unnamed')}")
            
            # Extract section content using delimiters
            section_content = self._extract_section_content(section, raw_markdown)
            
            if not section_content.strip():
                print(f"    Warning: No content found for section '{section.get('title')}'")
                continue
            
            # Analyze the section content
            analysis = self._analyze_section_detail(section, section_content)
            detailed_analyses.append(analysis)
        
        print(f"  Completed detailed analysis of {len(detailed_analyses)} sections")
        return detailed_analyses
    
    def _extract_section_content(self, section: Dict[str, Any], raw_markdown: str) -> str:
        """Extract section content using start and end delimiters"""
        start_delimiter = section.get('start_delimiter', '')
        end_delimiter = section.get('end_delimiter', '')
        
        if not start_delimiter:
            print(f"Warning: No start delimiter for section '{section.get('title')}'")
            return ""
        
        # Find start position
        start_pos = raw_markdown.find(start_delimiter)
        if start_pos == -1:
            # Try fuzzy matching
            start_pos = self._fuzzy_find_delimiter(raw_markdown, start_delimiter)
            if start_pos == -1:
                print(f"Warning: Start delimiter not found for section '{section.get('title')}'")
                return ""
        
        # Find end position
        if end_delimiter:
            end_pos = raw_markdown.find(end_delimiter, start_pos + len(start_delimiter))
            if end_pos == -1:
                end_pos = self._fuzzy_find_delimiter(raw_markdown, end_delimiter, start_pos + len(start_delimiter))
                if end_pos == -1:
                    # Use end of document
                    end_pos = len(raw_markdown)
        else:
            # No end delimiter, use reasonable heuristics
            end_pos = self._find_section_end(raw_markdown, start_pos, section.get('level', 1))
        
        # Extract content
        content = raw_markdown[start_pos:end_pos].strip()
        
        # Remove the start delimiter from content
        if content.startswith(start_delimiter):
            content = content[len(start_delimiter):].strip()
        
        return content
    
    def _fuzzy_find_delimiter(self, text: str, delimiter: str, start_pos: int = 0) -> int:
        """Find delimiter with some fuzzy matching"""
        # Try exact match first
        pos = text.find(delimiter, start_pos)
        if pos != -1:
            return pos
        
        # Try with normalized whitespace
        normalized_delimiter = ' '.join(delimiter.split())
        normalized_text = ' '.join(text.split())
        
        pos = normalized_text.find(normalized_delimiter, start_pos)
        if pos != -1:
            # Convert back to original text position (approximate)
            return pos
        
        # Try partial matching (first few words)
        delimiter_words = delimiter.split()[:3]  # First 3 words
        if delimiter_words:
            partial_delimiter = ' '.join(delimiter_words)
            pos = text.find(partial_delimiter, start_pos)
            if pos != -1:
                return pos
        
        return -1
    
    def _find_section_end(self, text: str, start_pos: int, section_level: int) -> int:
        """Find reasonable end position for section when no end delimiter"""
        # Look for next header of same or higher level
        lines = text[start_pos:].split('\n')
        current_pos = start_pos
        
        for i, line in enumerate(lines[1:], 1):  # Skip first line
            stripped_line = line.strip()
            if stripped_line.startswith('#'):
                # Count header level
                header_level = len(stripped_line) - len(stripped_line.lstrip('#'))
                if header_level <= section_level:
                    return current_pos + sum(len(lines[j]) + 1 for j in range(i))
            current_pos += len(line) + 1
        
        # Default to next 2000 characters or end of document
        return min(start_pos + 2000, len(text))
    
    def _analyze_section_detail(self, section: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Analyze section content in detail"""
        try:
            section_info = f"Section: {section.get('title')} | Type: {section.get('section_type')} | Level: {section.get('level')}"
            
            response = self.llm.invoke(
                self.detail_prompt.format(
                    section_content=content,
                    section_info=section_info
                )
            )
            
            import json
            analysis = json.loads(response)
            
            # Add original section info
            analysis['original_section'] = section
            analysis['content_length'] = len(content)
            
            return analysis
            
        except Exception as e:
            print(f"    Error analyzing section '{section.get('title')}': {e}")
            return {
                'original_section': section,
                'section_analysis': {
                    'section_id': section.get('section_id'),
                    'section_title': section.get('title'),
                    'section_type': section.get('section_type', 'general'),
                    'group_type': 'BASE' if section.get('level', 1) <= 2 else 'SUB',
                    'default_margin': 25
                },
                'offer_items': [],
                'section_metadata': {
                    'total_items': 0,
                    'has_pricing': False,
                    'has_quantities': False,
                    'technical_specs': [],
                    'key_materials': []
                },
                'error': str(e)
            }
