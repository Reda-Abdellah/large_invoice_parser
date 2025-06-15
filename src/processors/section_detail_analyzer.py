# src/processors/section_detail_analyzer.py
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate

from ..prompts.section_details_prompt import get_section_detail_prompt
from ..utils.json_cleaner import JSONResponseCleaner
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
        self.json_cleaner = JSONResponseCleaner()
        
        self.llm = self.ollama_client.create_llm_with_context(
            config.get('analysis_model', 'llama3.2:7b'),
            config.get('context_window_size', 8192)
        )
        
        self.detail_prompt = get_section_detail_prompt()
    
    def analyze_sections_detailed(self, structure_with_delimiters: Dict[str, Any], 
                                 content_for_analysis: str,
                                 overlapping_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze only level 3 detailed sections using their specific chunk content"""
        
        # Get hierarchical sections
        hierarchical_sections = structure_with_delimiters.get('sections', [])
        flat_sections = structure_with_delimiters.get('flat_sections', [])
        
        # Create chunk lookup for fast access
        chunk_lookup = {chunk['chunk_id']: chunk for chunk in overlapping_chunks}
        
        # Extract only level 3 sections (detailed items)
        level3_sections = self._extract_level3_sections(hierarchical_sections, flat_sections)
        
        detailed_analyses = []
        
        print("Phase 3: Detailed analysis of level 3 sections...")
        print(f"  Found {len(level3_sections)} level 3 sections to analyze")
        
        for i, section in enumerate(level3_sections, 1):
            print(f"  Analyzing level 3 section {i}/{len(level3_sections)}: {section.get('title', 'Unnamed')}")
            
            # Get the specific chunk content for this section
            chunk_content = self._get_section_chunk_content(section, chunk_lookup)
            
            if not chunk_content:
                print(f"    Warning: No chunk content found for section '{section.get('title')}'")
                continue
            
            # Extract section content using delimiters from the chunk
            section_content = self._extract_section_content_from_chunk(
                section, 
                chunk_content,
                content_for_analysis
            )
            
            if not section_content.strip():
                print(f"    Warning: No content extracted for section '{section.get('title')}'")
                continue
            
            # Analyze the section content
            analysis = self._analyze_section_detail(section, section_content, flat_sections)
            if analysis:
                detailed_analyses.append(analysis)
        
        print(f"  Completed detailed analysis of {len(detailed_analyses)} sections")
        return detailed_analyses
    
    def _extract_level3_sections(self, hierarchical_sections: List[Dict[str, Any]], 
                                flat_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all level 3 sections from hierarchical structure"""
        level3_sections = []
        
        def extract_recursive(sections):
            for section in sections:
                if section.get('level') == 3:
                    level3_sections.append(section)
                
                # Recurse into child sections
                child_sections = section.get('child_sections', [])
                if child_sections:
                    extract_recursive(child_sections)
        
        extract_recursive(hierarchical_sections)
        
        # Also check flat sections as backup
        for section in flat_sections:
            if section.get('level') == 3:
                # Check if not already in list
                if not any(s['section_id'] == section['section_id'] for s in level3_sections):
                    level3_sections.append(section)
        
        return level3_sections
    
    def _get_section_chunk_content(self, section: Dict[str, Any], 
                                  chunk_lookup: Dict[str, Dict[str, Any]]) -> str:
        """Get the chunk content where this section was found"""
        chunk_id = section.get('chunk_id')
        
        if not chunk_id or chunk_id not in chunk_lookup:
            print(f"    Warning: Chunk ID '{chunk_id}' not found for section '{section.get('title')}'")
            return ""
        
        chunk = chunk_lookup[chunk_id]
        return chunk.get('content', '')
    
    def _extract_section_content_from_chunk(self, section: Dict[str, Any], 
                                           chunk_content: str,
                                           full_markdown: str) -> str:
        """Extract section content using delimiters, preferring chunk content"""
        start_delimiter = section.get('start_delimiter', '')
        end_delimiter = section.get('end_delimiter', '')
        
        if not start_delimiter:
            print(f"    Warning: No start delimiter for section '{section.get('title')}'")
            return ""
        
        # First try to extract from the specific chunk
        section_content = self._extract_with_delimiters(chunk_content, start_delimiter, end_delimiter)
        
        # If not found in chunk, try the full markdown (fallback)
        if not section_content.strip():
            print(f"    Delimiter not found in chunk, trying full markdown...")
            section_content = self._extract_with_delimiters(full_markdown, start_delimiter, end_delimiter)
        
        return section_content
    
    def _extract_with_delimiters(self, content: str, start_delimiter: str, end_delimiter: str) -> str:
        """Extract content between delimiters"""
        # Find start position
        start_pos = content.find(start_delimiter)
        if start_pos == -1:
            # Try fuzzy matching
            start_pos = self._fuzzy_find_delimiter(content, start_delimiter)
            if start_pos == -1:
                return ""
        
        # Find end position
        if end_delimiter:
            end_pos = content.find(end_delimiter, start_pos + len(start_delimiter))
            if end_pos == -1:
                end_pos = self._fuzzy_find_delimiter(content, end_delimiter, start_pos + len(start_delimiter))
                if end_pos == -1:
                    # Use reasonable end position
                    end_pos = min(start_pos + 2000, len(content))
        else:
            # No end delimiter, use reasonable heuristics
            end_pos = min(start_pos + 1500, len(content))
        
        # Extract content
        extracted = content[start_pos:end_pos].strip()
        
        # Remove the start delimiter from content
        if extracted.startswith(start_delimiter):
            extracted = extracted[len(start_delimiter):].strip()
        
        return extracted
    
    def _fuzzy_find_delimiter(self, text: str, delimiter: str, start_pos: int = 0) -> int:
        """Find delimiter with fuzzy matching"""
        # Try exact match first
        pos = text.find(delimiter, start_pos)
        if pos != -1:
            return pos
        
        # Try with normalized whitespace
        normalized_delimiter = ' '.join(delimiter.split())
        lines = text[start_pos:].split('\n')
        
        for i, line in enumerate(lines):
            normalized_line = ' '.join(line.split())
            if normalized_delimiter in normalized_line:
                # Calculate position in original text
                return start_pos + sum(len(lines[j]) + 1 for j in range(i))
        
        # Try partial matching (first few words)
        delimiter_words = delimiter.split()[:3]
        if delimiter_words:
            partial_delimiter = ' '.join(delimiter_words)
            pos = text.find(partial_delimiter, start_pos)
            if pos != -1:
                return pos
        
        return -1
    
    def _analyze_section_detail(self, section: Dict[str, Any], content: str, 
                               flat_sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze level 3 section content in detail"""
        try:
            # Build parent context
            parent_context = self._build_parent_context(section, flat_sections)
            
            section_info = (f"Section ID: {section.get('section_id')} | "
                          f"Title: {section.get('title')} | "
                          f"Type: {section.get('section_type')} | "
                          f"Level: {section.get('level')}")
            
            response = self.llm.invoke(
                self.detail_prompt.format(
                    section_content=content,
                    section_info=section_info,
                    parent_context=parent_context
                )
            )
            
            print(f"    Raw analysis response (first 150 chars):")
            print(f"    {response[:150]}...")
            
            # Extract JSON
            analysis = self.json_cleaner.extract_json(response)
            
            if not analysis:
                print(f"    Warning: Could not extract valid JSON for section '{section.get('title')}'")
                return self._create_fallback_analysis(section, content)
            
            # Add original section info and processing metadata
            analysis['original_section'] = section
            analysis['content_length'] = len(content)
            analysis['chunk_id'] = section.get('chunk_id')
            analysis['extraction_method'] = 'delimiter_based'
            
            print(f"    Successfully analyzed section with {len(analysis.get('offer_items', []))} items")
            return analysis
            
        except Exception as e:
            print(f"    Error analyzing section '{section.get('title')}': {e}")
            return self._create_fallback_analysis(section, content, str(e))
    
    def _build_parent_context(self, section: Dict[str, Any], 
                             flat_sections: List[Dict[str, Any]]) -> str:
        """Build context from parent sections"""
        parent_id = section.get('parent_section_id')
        
        if not parent_id:
            return "No parent context available"
        
        # Find parent sections
        parents = []
        current_parent_id = parent_id
        
        while current_parent_id:
            parent = next((s for s in flat_sections if s['section_id'] == current_parent_id), None)
            if parent:
                parents.append(parent)
                current_parent_id = parent.get('parent_section_id')
            else:
                break
        
        # Build context string
        if not parents:
            return "No parent context found"
        
        context_parts = ["Parent hierarchy:"]
        for parent in reversed(parents):  # Show from top level down
            context_parts.append(
                f"- Level {parent['level']}: {parent['title']} ({parent.get('section_type', 'unknown')})"
            )
        
        return "\n".join(context_parts)
    
    def _create_fallback_analysis(self, section: Dict[str, Any], content: str, error: str = None) -> Dict[str, Any]:
        """Create fallback analysis when processing fails"""
        return {
            'original_section': section,
            'section_analysis': {
                'section_id': section.get('section_id'),
                'section_title': section.get('title'),
                'section_type': section.get('section_type', 'technical_specs'),
                'group_type': 'SUB',
                'default_margin': 25,
                'parent_section_id': section.get('parent_section_id')
            },
            'offer_items': [],
            'section_metadata': {
                'total_items': 0,
                'has_pricing': False,
                'has_quantities': False,
                'technical_specs': [],
                'key_materials': []
            },
            'content_length': len(content),
            'chunk_id': section.get('chunk_id'),
            'extraction_method': 'fallback',
            'error': error or 'Processing failed'
        }