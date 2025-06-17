# src/processors/section_detail_analyzer.py
from typing import List, Dict, Any, Optional

from ..utils.enhanced_llm_client import EnhancedLLMClient

from ..prompts.section_details_prompt import get_section_detail_prompt
from ..utils.json_cleaner import JSONResponseCleaner
import re

class SectionDetailAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        self.llm_client = EnhancedLLMClient(config)
        self.task_name = "structure_extraction"

        self.json_cleaner = JSONResponseCleaner()
        
        self.item_detail_prompt = get_section_detail_prompt()
    
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
    
    
    

    def analyze_offer_items_detailed(self, offer_structure: Dict[str, Any], 
                                   overlapping_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze each offer item in detail using chunk content and delimiters"""
        
        # Create chunk lookup
        chunk_lookup = {chunk['chunk_id']: chunk for chunk in overlapping_chunks}
        
        # Process all offer items
        processed_structure = self._deep_copy_structure(offer_structure)
        total_items_processed = 0
        
        print("Phase 3: Detailed analysis of individual offer items...")
        
        for main_group in processed_structure.get('offer_item_groups', []):
            for sub_group in main_group.get('offer_groups', []):
                items = sub_group.get('offer_items', [])
                print(f"  Processing {len(items)} items in sub-group: {sub_group.get('name', 'Unnamed')}")
                
                for item in items:
                    item_details = self._analyze_single_item(item, main_group, sub_group, chunk_lookup)
                    if item_details:
                        item['details'] = item_details
                        total_items_processed += 1
                    else:
                        item['details'] = self._create_empty_details()
        
        print(f"  Completed detailed analysis of {total_items_processed} items")
        
        return processed_structure
    
    def _analyze_single_item(self, item: Dict[str, Any], 
                           main_group: Dict[str, Any], 
                           sub_group: Dict[str, Any],
                           chunk_lookup: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Analyze a single offer item in detail"""
        try:
            # Get chunk content
            chunk_id = item.get('chunk_id')
            if not chunk_id or chunk_id not in chunk_lookup:
                print(f"    Warning: Chunk {chunk_id} not found for item: {item.get('name', 'Unnamed')}")
                return None
            
            chunk = chunk_lookup[chunk_id]
            
            # # Extract item content using delimiters
            # item_content = self._extract_item_content(item, chunk['content'])
            item_content = chunk['content']
            
            if not item_content.strip():
                print(f"    Warning: No content extracted for item: {item.get('name', 'Unnamed')}")
                return None
            
            # Build context information
            context_info = self._build_item_context(item, main_group, sub_group)
            
            # Build item info
            item_info = (f"Name: {item.get('name')} | "
                        f"Chunk: {chunk_id}")
            if 'start_delimiter' in item:
                item_info += f" | Start Delimiter: {item.get('start_delimiter', 'None')}"
            if 'end_delimiter' in item:
                item_info += f" | End Delimiter: {item.get('end_delimiter', 'None')}"
            
            # Analyze with LLM
            response = self.llm_client.invoke(
                self.task_name,
                self.item_detail_prompt.format(
                    item_content=item_content,
                    item_info=item_info,
                    context_info=context_info
                )
            )
            
            # Parse response
            analysis = self.json_cleaner.extract_json(response)
            
            if not analysis:
                print(f"    Warning: Could not extract JSON for item: {item.get('name', 'Unnamed')}")
                return None
            
            print(f"    ✓ Analyzed item: {item.get('name', 'Unnamed')[:50]}...")
            return analysis
            
        except Exception as e:
            print(f"    Error analyzing item {item.get('name', 'Unnamed')}: {e}")
            return None
    
    def _extract_item_content(self, item: Dict[str, Any], chunk_content: str) -> str:
        """Extract specific item content using delimiters"""
        start_delimiter = item.get('start_delimiter', '')
        end_delimiter = item.get('end_delimiter', '')
        
        if not start_delimiter:
            # If no delimiter, try to find content around item name
            item_name = item.get('name', '')
            if item_name:
                return self._extract_content_around_name(item_name, chunk_content)
            return ""
        
        # Extract using delimiters
        start_pos = chunk_content.find(start_delimiter)
        if start_pos == -1:
            # Try fuzzy matching
            start_pos = self._fuzzy_find_delimiter(chunk_content, start_delimiter)
            if start_pos == -1:
                return ""
        
        # Find end position
        if end_delimiter:
            end_pos = chunk_content.find(end_delimiter, start_pos + len(start_delimiter))
            if end_pos == -1:
                end_pos = min(start_pos + 1000, len(chunk_content))  # Reasonable limit
        else:
            end_pos = min(start_pos + 800, len(chunk_content))
        
        # Extract content
        content = chunk_content[start_pos:end_pos]
        
        # Include some context before and after
        context_before = chunk_content[max(0, start_pos - 200):start_pos]
        context_after = chunk_content[end_pos:min(len(chunk_content), end_pos + 200)]
        
        full_content = f"{context_before}\n--- ITEM CONTENT ---\n{content}\n--- END ITEM ---\n{context_after}"
        
        return full_content
    
    def _extract_content_around_name(self, item_name: str, chunk_content: str) -> str:
        """Extract content around item name when no delimiters available"""
        # Find item name in content
        name_pos = chunk_content.find(item_name)
        if name_pos == -1:
            # Try partial matching
            name_words = item_name.split()[:3]  # First 3 words
            for word in name_words:
                name_pos = chunk_content.find(word)
                if name_pos != -1:
                    break
        
        if name_pos == -1:
            return chunk_content[:1000]  # Return first part of chunk
        
        # Extract context around the name
        start_pos = max(0, name_pos - 300)
        end_pos = min(len(chunk_content), name_pos + 700)
        
        return chunk_content[start_pos:end_pos]
    
    def _fuzzy_find_delimiter(self, content: str, delimiter: str) -> int:
        """Find delimiter with fuzzy matching"""
        # Try with normalized whitespace
        normalized_delimiter = ' '.join(delimiter.split())
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            normalized_line = ' '.join(line.split())
            if normalized_delimiter in normalized_line:
                return sum(len(lines[j]) + 1 for j in range(i))
        
        return -1
    
    def _build_item_context(self, item: Dict[str, Any], 
                          main_group: Dict[str, Any], 
                          sub_group: Dict[str, Any]) -> str:
        """Build context information for item analysis"""
        context_parts = [
            f"Main Category: {main_group.get('name', 'Unknown')}",
            f"Sub-Category: {sub_group.get('name', 'Unknown')}",
            f"Item Position: {item.get('offer_item_id', 'Unknown')}",
        ]
        
        # Add parent context for better understanding
        if 'CHALEUR' in main_group.get('name', '').upper():
            context_parts.append("Context: Heating/thermal distribution system")
        elif 'TUYAUTERIE' in sub_group.get('name', '').upper():
            context_parts.append("Context: Piping and tubing specifications")
        elif 'ACCESSOIRE' in sub_group.get('name', '').upper():
            context_parts.append("Context: Accessories and fittings")
        
        return '\n'.join(context_parts)
    
    def _create_empty_details(self) -> Dict[str, Any]:
        """Create empty details structure when analysis fails"""
        return {
            "item_details": {
                "supplier_id": "not_available",
                "unit_quantity": None,
                "unit_type": "MATERIAL",
                "percentage": 0,
                "unit": "not_available",
                "unit_price": None,
                "margin": 25,
                "auction_discount": 0,
                "supplier_discount_goal": 0,
                "billing_percent_situations": [],
                "gantt_schedules": [],
                "progress": 0,
                "employees_ids": [],
                "article_id": "not_available",
                "article_number": "not_available",
                "desc_html": "<p>Details not available</p>",
                "is_ttc": False,
                "taxes_rate_percent": 0,
                "apply_discount": False,
                "isPageBreakBefore": False,
                "isSellingPriceLocked": False,
                "isInvalid": False,
                "isCostPriceLocked": False,
                "discount_value": 0,
                "is_optional": False,
                "variants": [],
                "articles": []
            },
            "additional_fields": {},
            "extraction_metadata": {
                "found_quantity": False,
                "found_price": False,
                "found_technical_specs": False,
                "confidence_level": "none"
            }
        }
    
    def _deep_copy_structure(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of the structure for processing"""
        import json
        return json.loads(json.dumps(structure))