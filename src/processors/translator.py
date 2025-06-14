# src/processors/translator.py
from typing import Dict, Any, List, Optional
from langchain.prompts import PromptTemplate
from ..utils.ollama_client import EnhancedOllamaClient
import re

class DocumentTranslator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_client = EnhancedOllamaClient(
            base_url=config.get('ollama_base_url', 'http://localhost:11434'),
            context_window_size=config.get('context_window_size', 8192),
            timeout=config.get('timeout', 300)
        )
        
        # Use a capable model for translation
        translation_model = config.get('translation_model', config.get('analysis_model', 'llama3.2:7b'))
        self.llm = self.ollama_client.create_llm_with_context(
            translation_model,
            config.get('context_window_size', 8192)
        )
        
        self.fr_to_en_prompt = PromptTemplate(
            input_variables=["french_content"],
            template="""
            Translate this French construction/engineering document to English.
            Preserve the exact markdown structure, formatting, headers, and technical specifications.
            Keep technical terms, measurements, and reference numbers unchanged.
            
            IMPORTANT:
            - Maintain all markdown formatting (headers, tables, lists)
            - Keep technical specifications like "DN 100", "PN16", measurements in original form
            - Preserve reference numbers and codes (like "CFC 243.A")
            - Translate only descriptive text, not technical data
            
            French content:
            {french_content}
            
            Return the English translation maintaining exact formatting:
            """
        )
        
        self.en_to_fr_prompt = PromptTemplate(
            input_variables=["english_content", "original_french_terms"],
            template="""
            Translate this English construction/engineering content back to French.
            Use the original French technical terms and maintain professional construction terminology.
            
            Original French technical terms to preserve:
            {original_french_terms}
            
            English content to translate:
            {english_content}
            
            Return the French translation using proper construction terminology:
            """
        )
    
    def translate_markdown_to_english(self, french_markdown: str) -> Optional[str]:
        """Translate French markdown to English while preserving structure"""
        if not self.config.get('enable_translation', False):
            return None
        
        try:
            print("Translating markdown from French to English...")
            
            # Split into chunks if too large
            chunks = self._split_for_translation(french_markdown)
            translated_chunks = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"  Translating chunk {i}/{len(chunks)}")
                
                translated_chunk = self.llm.invoke(
                    self.fr_to_en_prompt.format(french_content=chunk)
                )
                
                translated_chunks.append(translated_chunk)
            
            # Combine translated chunks
            translated_markdown = '\n\n'.join(translated_chunks)
            
            print(f"  Translation complete: {len(french_markdown)} -> {len(translated_markdown)} characters")
            return translated_markdown
            
        except Exception as e:
            print(f"Error translating markdown to English: {e}")
            return None
    
    def translate_offer_to_french(self, processed_offer: 'ProcessedOffer') -> Optional['ProcessedOffer']:
        """Translate processed offer back to French"""
        if not self.config.get('enable_translation', False):
            return None
        
        try:
            print("Translating final offer back to French...")
            
            # Extract French terms from original content for reference
            french_terms = self._extract_french_technical_terms()
            
            # Create a copy of the offer for translation
            offer_dict = processed_offer.model_dump()
            
            # Translate offer-level fields
            offer_dict = self._translate_offer_fields(offer_dict, french_terms)
            
            # Translate item groups recursively
            if 'offer_item_groups' in offer_dict:
                offer_dict['offer_item_groups'] = self._translate_item_groups(
                    offer_dict['offer_item_groups'], 
                    french_terms
                )
            
            # Create new ProcessedOffer instance
            from ..models.invoice_models import ProcessedOffer
            translated_offer = ProcessedOffer(**offer_dict)
            
            print("  French translation complete")
            return translated_offer
            
        except Exception as e:
            print(f"Error translating offer to French: {e}")
            return None
    
    def _split_for_translation(self, content: str, max_chunk_size: int = 3000) -> List[str]:
        """Split content into translation-friendly chunks"""
        if len(content) <= max_chunk_size:
            return [content]
        
        chunks = []
        lines = content.split('\n')
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk + line + '\n') > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_french_technical_terms(self) -> str:
        """Extract common French technical terms for reference"""
        return """
        Common French construction terms:
        - Tuyauterie = Piping
        - Raccordement = Connection
        - Vanne = Valve
        - Robinet = Faucet/Tap
        - Équilibrage = Balancing
        - Purgeur = Purger
        - Vidange = Drainage
        - Accessoires = Accessories
        - Installation = Installation
        - Montage = Assembly
        - Distribution = Distribution
        - Chauffage = Heating
        - Activités = Activities
        - Circuit = Circuit
        - Réseau = Network
        - Intérieur = Interior
        """
    
    def _translate_offer_fields(self, offer_dict: Dict[str, Any], french_terms: str) -> Dict[str, Any]:
        """Translate main offer fields"""
        fields_to_translate = ['project_name', 'vendor', 'customer']
        
        for field in fields_to_translate:
            if field in offer_dict and offer_dict[field]:
                try:
                    translated = self.llm.invoke(
                        self.en_to_fr_prompt.format(
                            english_content=offer_dict[field],
                            original_french_terms=french_terms
                        )
                    )
                    offer_dict[field] = translated.strip()
                except Exception as e:
                    print(f"Warning: Could not translate field {field}: {e}")
        
        return offer_dict
    
    def _translate_item_groups(self, groups: List[Dict[str, Any]], french_terms: str) -> List[Dict[str, Any]]:
        """Translate item groups recursively"""
        for group in groups:
            # Translate group name
            if 'name' in group and group['name']:
                try:
                    translated_name = self.llm.invoke(
                        self.en_to_fr_prompt.format(
                            english_content=group['name'],
                            original_french_terms=french_terms
                        )
                    )
                    group['name'] = translated_name.strip()
                except Exception as e:
                    print(f"Warning: Could not translate group name: {e}")
            
            # Translate offer items
            if 'offer_items' in group:
                group['offer_items'] = self._translate_offer_items(group['offer_items'], french_terms)
            
            # Translate sub-groups recursively
            if 'offer_groups' in group:
                group['offer_groups'] = self._translate_item_groups(group['offer_groups'], french_terms)
        
        return groups
    
    def _translate_offer_items(self, items: List[Dict[str, Any]], french_terms: str) -> List[Dict[str, Any]]:
        """Translate individual offer items"""
        for item in items:
            # Fields to translate
            fields_to_translate = ['name', 'desc_html', 'category']
            
            for field in fields_to_translate:
                if field in item and item[field]:
                    try:
                        if field == 'desc_html':
                            # Handle HTML content
                            html_content = item[field]
                            # Extract text from HTML for translation
                            text_content = re.sub(r'<[^>]+>', '', html_content)
                            if text_content.strip():
                                translated_text = self.llm.invoke(
                                    self.en_to_fr_prompt.format(
                                        english_content=text_content,
                                        original_french_terms=french_terms
                                    )
                                )
                                # Rebuild HTML
                                item[field] = f"<p>{translated_text.strip()}</p>"
                        else:
                            translated = self.llm.invoke(
                                self.en_to_fr_prompt.format(
                                    english_content=item[field],
                                    original_french_terms=french_terms
                                )
                            )
                            item[field] = translated.strip()
                    except Exception as e:
                        print(f"Warning: Could not translate item field {field}: {e}")
        
        return items
