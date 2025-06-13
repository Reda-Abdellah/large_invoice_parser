# src/processors/section_analyzer.py
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
from ..models.invoice_models import InvoiceItem
from ..utils.ollama_client import EnhancedOllamaClient

class SectionAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_client = EnhancedOllamaClient(
            base_url=config.get('ollama_base_url', 'http://localhost:11434'),
            context_window_size=config.get('context_window_size', 8192),
            timeout=config.get('timeout', 300)
        )
        
        # Use larger context for detailed analysis
        analysis_context_size = config.get('context_window_size', 8192)
        
        self.llm = self.ollama_client.create_llm_with_context(
            config.get('analysis_model', 'llama3.2:7b'),
            analysis_context_size
        )
        
        self.analysis_prompt = PromptTemplate(
            input_variables=["section_content", "section_context"],
            template="""
            Analyze this invoice section and extract structured data.
            
            Section Context: {section_context}
            
            Content:
            {section_content}
            
            Extract the following information in JSON format:
            {{
                "items": [
                    {{
                        "description": "item description",
                        "quantity": number or null,
                        "unit_price": number or null,
                        "total_price": number or null,
                        "category": "category name or null"
                    }}
                ],
                "section_metadata": {{
                    "contains_pricing": boolean,
                    "contains_dates": boolean,
                    "contains_contact_info": boolean,
                    "key_information": ["list", "of", "key", "points"]
                }}
            }}
            
            Only extract actual invoice items (products, services, fees).
            Return valid JSON only.
            """
        )
    
    def analyze_section(self, section_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single section chunk with context window management"""
        try:
            # Combine section content and context
            full_content = f"Context: {section_chunk['context']}\n\nContent: {section_chunk['content']}"
            
            # Check if content fits in context window
            context_check = self.ollama_client.check_context_requirements(
                full_content, 
                self.config.get('context_window_size', 8192)
            )
            
            if not context_check['fits_in_context']:
                print(f"Warning: Section '{section_chunk['section_title']}' "
                      f"({context_check['estimated_tokens']} tokens) exceeds context window. "
                      f"Using adaptive context size...")
                
                # Use maximum available context for large sections
                adaptive_context_size = min(
                    self.config.get('max_context_window', 32768),
                    context_check['estimated_tokens'] + 1000  # Add buffer for response
                )
                
                # Create LLM with larger context for this section
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
            
            # Parse JSON response
            import json
            analysis_result = json.loads(response)
            
            # Add section information to items
            for item in analysis_result.get('items', []):
                item['section'] = section_chunk['section_title']
            
            return {
                'section_title': section_chunk['section_title'],
                'chunk_index': section_chunk['chunk_index'],
                'analysis': analysis_result,
                'context_info': context_check,
                'raw_response': response
            }
            
        except Exception as e:
            return {
                'section_title': section_chunk['section_title'],
                'chunk_index': section_chunk['chunk_index'],
                'analysis': {'items': [], 'section_metadata': {}},
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
