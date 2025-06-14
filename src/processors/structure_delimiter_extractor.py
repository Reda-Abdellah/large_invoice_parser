# src/processors/structure_delimiter_extractor.py
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
from ..utils.ollama_client import EnhancedOllamaClient
import re
import uuid

class StructureDelimiterExtractor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_client = EnhancedOllamaClient(
            base_url=config.get('ollama_base_url', 'http://localhost:11434'),
            context_window_size=config.get('context_window_size', 8192),
            timeout=config.get('timeout', 300)
        )
        
        self.llm = self.ollama_client.create_llm_with_context(
            config.get('structure_model', 'llama3.2:3b'),
            config.get('context_window_size', 8192)
        )
        
        self.structure_prompt = PromptTemplate(
            input_variables=["chunk_content", "chunk_info"],
            template="""
            Analyze this markdown chunk and identify structural sections for a construction/engineering offer.
            
            Chunk Info: {chunk_info}
            
            Content:
            {chunk_content}
            
            For each section you identify, provide:
            1. Section title/name
            2. Section level (1=main, 2=sub, 3=detail)
            3. START and END delimiters (exact text snippets that mark section boundaries)
            4. Section type (work_category, materials, labor, pricing, technical_specs)
            5. Estimated content (brief description)
            
            Return JSON format:
            {{
                "sections": [
                    {{
                        "section_id": "unique_id",
                        "title": "section title",
                        "level": 1,
                        "section_type": "work_category|materials|labor|pricing|technical_specs",
                        "start_delimiter": "exact text that starts this section",
                        "end_delimiter": "exact text that ends this section",
                        "estimated_content": "brief description of what this section contains",
                        "chunk_id": "current_chunk_id"
                    }}
                ]
            }}
            
            Be precise with delimiters - they should be exact text snippets that can be found in the markdown.
            """
        )
        
        self.consolidation_prompt = PromptTemplate(
            input_variables=["all_sections"],
            template="""
            Consolidate these section analyses from multiple chunks into a coherent document structure.
            Remove duplicates, merge overlapping sections, and create a hierarchical structure.
            
            Sections from all chunks:
            {all_sections}
            
            Return consolidated structure in JSON format:
            {{
                "document_structure": {{
                    "total_sections": number,
                    "main_categories": ["list", "of", "main", "categories"],
                    "sections": [
                        {{
                            "section_id": "unique_id",
                            "title": "section title",
                            "level": 1,
                            "section_type": "work_category|materials|labor|pricing|technical_specs",
                            "start_delimiter": "exact start text",
                            "end_delimiter": "exact end text",
                            "estimated_content": "description",
                            "parent_section_id": "parent_id_if_applicable",
                            "child_sections": ["list", "of", "child", "section", "ids"]
                        }}
                    ]
                }}
            }}
            """
        )
    
    def extract_structure_from_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structure with delimiters from all chunks"""
        all_sections = []
        
        print("Phase 2: Extracting structure with delimiters from chunks...")
        
        for chunk in chunks:
            chunk_sections = self._analyze_chunk_structure(chunk)
            all_sections.extend(chunk_sections)
        
        # Consolidate sections from all chunks
        consolidated_structure = self._consolidate_sections(all_sections)
        
        print(f"  Found {len(all_sections)} sections across chunks")
        print(f"  Consolidated to {consolidated_structure.get('total_sections', 0)} unique sections")
        
        return consolidated_structure
    
    def _analyze_chunk_structure(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze structure in a single chunk"""
        try:
            chunk_info = f"Chunk {chunk['chunk_index'] + 1}/{chunk['total_chunks']} | Chars: {chunk['start_char']}-{chunk['end_char']}"
            
            response = self.llm.invoke(
                self.structure_prompt.format(
                    chunk_content=chunk['content'],
                    chunk_info=chunk_info
                )
            )
            
            import json
            result = json.loads(response)
            
            # Add chunk information to each section
            sections = result.get('sections', [])
            for section in sections:
                section['chunk_id'] = chunk['chunk_id']
                section['chunk_index'] = chunk['chunk_index']
                if 'section_id' not in section:
                    section['section_id'] = str(uuid.uuid4())
            
            return sections
            
        except Exception as e:
            print(f"Error analyzing chunk {chunk['chunk_id']}: {e}")
            return []
    
    def _consolidate_sections(self, all_sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolidate sections from multiple chunks"""
        try:
            sections_text = json.dumps(all_sections, indent=2)
            
            response = self.llm.invoke(
                self.consolidation_prompt.format(all_sections=sections_text)
            )
            
            import json
            consolidated = json.loads(response)
            
            return consolidated.get('document_structure', {
                'total_sections': 0,
                'main_categories': [],
                'sections': []
            })
            
        except Exception as e:
            print(f"Error consolidating sections: {e}")
            # Fallback: simple deduplication
            return self._simple_consolidation(all_sections)
    
    def _simple_consolidation(self, all_sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple fallback consolidation"""
        # Remove duplicates based on title similarity
        unique_sections = []
        seen_titles = set()
        
        for section in all_sections:
            title_key = section.get('title', '').lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_sections.append(section)
        
        return {
            'total_sections': len(unique_sections),
            'main_categories': list(set(s.get('section_type', '') for s in unique_sections)),
            'sections': unique_sections
        }
