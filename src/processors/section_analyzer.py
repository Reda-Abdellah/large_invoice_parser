# src/processors/section_analyzer.py
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
from ..models.invoice_models import OfferItem, OfferItemType, UnitType
from ..utils.ollama_client import EnhancedOllamaClient

class SectionAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_client = EnhancedOllamaClient(
            base_url=config.get('ollama_base_url', 'http://localhost:11434'),
            context_window_size=config.get('context_window_size', 8192),
            timeout=config.get('timeout', 300)
        )
        
        analysis_context_size = config.get('context_window_size', 8192)
        
        self.llm = self.ollama_client.create_llm_with_context(
            config.get('analysis_model', 'llama3.2:7b'),
            analysis_context_size
        )
        
        self.analysis_prompt = PromptTemplate(
            input_variables=["section_content", "section_context"],
            template="""
            Analyze this construction/engineering offer section and extract structured data for items and services.
            
            Section Context: {section_context}
            
            Content:
            {section_content}
            
            Extract the following information in JSON format:
            {{
                "offer_items": [
                    {{
                        "name": "item name/description",
                        "offer_item_type": "NORMAL|OPTIONAL|VARIANT",
                        "unit_quantity": number,
                        "unit_type": "MATERIAL|LABOR|SERVICE",
                        "unit": "m|m²|m³|kg|h|pcs|etc",
                        "unit_price": number,
                        "margin": number (default 25),
                        "article_number": "article/reference number if any",
                        "desc_html": "HTML formatted description",
                        "is_optional": boolean,
                        "category": "category name"
                    }}
                ],
                "section_metadata": {{
                    "contains_pricing": boolean,
                    "contains_technical_specs": boolean,
                    "contains_quantities": boolean,
                    "group_type": "BASE|SUB",
                    "default_margin": number,
                    "key_information": ["list", "of", "key", "points"]
                }}
            }}
            
            Focus on extracting:
            - Construction materials, equipment, labor
            - Technical specifications (DN, dimensions, materials)
            - Quantities and units (m, m², pieces, hours)
            - Pricing information
            - Article/reference numbers
            
            Return valid JSON only.
            """
        )
    
    def analyze_section(self, section_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single section chunk for offer items"""
        try:
            full_content = f"Context: {section_chunk['context']}\n\nContent: {section_chunk['content']}"
            
            context_check = self.ollama_client.check_context_requirements(
                full_content, 
                self.config.get('context_window_size', 8192)
            )
            
            if not context_check['fits_in_context']:
                print(f"Warning: Section '{section_chunk['section_title']}' "
                      f"({context_check['estimated_tokens']} tokens) exceeds context window. "
                      f"Using adaptive context size...")
                
                adaptive_context_size = min(
                    self.config.get('max_context_window', 32768),
                    context_check['estimated_tokens'] + 1000
                )
                
                adaptive_llm = self.ollama_client.create_llm_with_context(
                    self.config.get('analysis_model', 'llama3.2:7b'),
                    adaptive_context_size
                )
                
                response = adaptive_llm.invoke(
                    self.analysis_prompt.format(
                        section_content=section_chunk['content'],
                        section_context=section_chunk['context']
                    )
                )
            else:
                response = self.llm.invoke(
                    self.analysis_prompt.format(
                        section_content=section_chunk['content'],
                        section_context=section_chunk['context']
                    )
                )
            
            import json
            analysis_result = json.loads(response)
            
            # Add section information to items
            for item in analysis_result.get('offer_items', []):
                item['section'] = section_chunk['section_title']
                # Convert description to HTML format
                if 'name' in item and 'desc_html' not in item:
                    item['desc_html'] = f"<p>{item['name'].replace(chr(10), '</br>')}</p>"
            
            return {
                'section_title': section_chunk['section_title'],
                'section_level': section_chunk.get('section_level', 1),
                'chunk_index': section_chunk['chunk_index'],
                'analysis': analysis_result,
                'context_info': context_check,
                'raw_response': response
            }
            
        except Exception as e:
            return {
                'section_title': section_chunk['section_title'],
                'chunk_index': section_chunk['chunk_index'],
                'analysis': {'offer_items': [], 'section_metadata': {}},
                'error': str(e)
            }
    
    def analyze_all_sections(self, chunked_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze all section chunks with progress reporting"""
        analyzed_sections = []
        total_sections = len(chunked_sections)
        
        for i, section_chunk in enumerate(chunked_sections, 1):
            print(f"Analyzing section {i}/{total_sections}: {section_chunk['section_title']}")
            analysis = self.analyze_section(section_chunk)
            analyzed_sections.append(analysis)
        
        return analyzed_sections
