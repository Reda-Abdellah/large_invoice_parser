# src/processors/structure_delimiter_extractor.py
from typing import List, Dict, Any
import uuid

from ..prompts.structure_prompt import get_structure_prompt
from ..utils.ollama_client import EnhancedOllamaClient
import re
from ..utils.json_cleaner import JSONResponseCleaner

class StructureDelimiterExtractor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_client = EnhancedOllamaClient(
            base_url=config.get('ollama_base_url', 'http://localhost:11434'),
            context_window_size=config.get('context_window_size', 8192),
            timeout=config.get('timeout', 300)
        )

        self.json_cleaner = JSONResponseCleaner()
        
        self.llm = self.ollama_client.create_llm_with_context(
            config.get('structure_model', 'llama3.2:3b'),
            config.get('context_window_size', 8192)
        )
        
        self.extraction_prompt = get_structure_prompt()
        
    
    def extract_structure_from_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structure with delimiters from all chunks"""
        
        print("Phase 2: Extracting structure with delimiters from chunks...")

        # Reset state for new document
        # Track context across chunks
        self.extraction_context = {
            'current_main_group': None,
            'current_sub_group': None,
            'all_groups': [],
            'item_counter': 0
        }
        chunk_items_list = []
        for chunk in chunks:
            chunk_items = self._extract_from_chunk_with_context(chunk)
            chunk_items_list.append(chunk_items)
            self._merge_chunk_items(chunk_items)

        # Build final structure
        final_structure = self._build_final_offer_structure()
        
        print(f"  Final structure: {final_structure.get('total_sections', 0)} sections")
        
        return final_structure, chunk_items_list
    
    def _extract_from_chunk_with_context(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Extract offer items from chunk with previous context"""
        try:
            chunk_info = f"Chunk {chunk['chunk_index'] + 1}/{chunk['total_chunks']} | Chars: {chunk['start_char']}-{chunk['end_char']}"
            
            # Clean content
            # cleaned_content = self._clean_chunk_content(chunk['content'])
            cleaned_content = chunk['content']
            
            # Build context from previous chunks
            previous_context = self._build_previous_context()
            
            response = self.llm.invoke(
                self.extraction_prompt.format(
                    chunk_content=cleaned_content,
                    chunk_info=chunk_info,
                    previous_context=previous_context
                )
            )
            
            print(f"    Extracting from chunk {chunk['chunk_index']}...")
            
            # Parse JSON response
            result = self.json_cleaner.extract_json(response)
            
            if not result:
                print(f"    Warning: Could not extract valid JSON from chunk {chunk['chunk_index']}")
                return {"offer_item_groups": []}
            
            # Add chunk information to all items
            self._add_chunk_info_to_items(result, chunk)
            
            print(f"    Successfully extracted items from chunk {chunk['chunk_index']}")
            return result
            
        except Exception as e:
            print(f"    Error extracting from chunk {chunk['chunk_id']}: {e}")
            return {"offer_item_groups": []}
    
    def _build_previous_context(self) -> str:
        """Build context string from previous extractions"""
        if not self.extraction_context['all_groups']:
            return "No previous context (first chunk)"
        
        context_lines = ["Current document structure:"]
        
        # Show current hierarchy
        if self.extraction_context['current_main_group']:
            context_lines.append(f"Current main group: {self.extraction_context['current_main_group']['name']}")
        
        if self.extraction_context['current_sub_group']:
            context_lines.append(f"Current sub group: {self.extraction_context['current_sub_group']['name']}")
        
        # Show recent groups
        context_lines.append("\nRecent groups extracted:")
        recent_groups = self.extraction_context['all_groups'][-3:]  # Last 3 groups
        
        for group in recent_groups:
            context_lines.append(f"- {group['name']} ({group['group_type']})")
            for sub_group in group.get('offer_groups', [])[-2:]:  # Last 2 sub-groups
                item_count = len(sub_group.get('offer_items', []))
                context_lines.append(f"  - {sub_group['name']} ({item_count} items)")
        
        context_lines.append(f"\nTotal items extracted so far: {self.extraction_context['item_counter']}")
        
        return "\n".join(context_lines)
    
    def _add_chunk_info_to_items(self, result: Dict[str, Any], chunk: Dict[str, Any]):
        """Add chunk information to all extracted items"""
        def add_chunk_recursive(groups):
            for group in groups:
                # Add to sub-groups
                for sub_group in group.get('offer_groups', []):
                    # Add to items
                    for item in sub_group.get('offer_items', []):
                        item['chunk_id'] = chunk['chunk_id']
                        item['chunk_index'] = chunk['chunk_index']
                        if 'offer_item_id' not in item:
                            item['offer_item_id'] = str(uuid.uuid4())
                    
                    # Recurse for nested groups
                    if sub_group.get('offer_groups'):
                        add_chunk_recursive([sub_group])
        
        add_chunk_recursive(result.get('offer_item_groups', []))
    
    def _merge_chunk_items(self, chunk_items: Dict[str, Any]):
        """Merge items from current chunk with accumulated structure"""
        new_groups = chunk_items.get('offer_item_groups', [])
        
        for new_group in new_groups:
            # Find or create main group
            existing_main = self._find_or_create_main_group(new_group)
            
            # Merge sub-groups and items
            for new_sub_group in new_group.get('offer_groups', []):
                existing_sub = self._find_or_create_sub_group(existing_main, new_sub_group)
                
                # Add items to sub-group
                new_items = new_sub_group.get('offer_items', [])
                existing_sub['offer_items'].extend(new_items)
                self.extraction_context['item_counter'] += len(new_items)
                
                # Update current context
                self.extraction_context['current_sub_group'] = existing_sub
            
            self.extraction_context['current_main_group'] = existing_main
    
    def _find_or_create_main_group(self, new_group: Dict[str, Any]) -> Dict[str, Any]:
        """Find existing main group or create new one"""
        group_name = new_group['name'].strip()
        
        # Look for existing group with similar name
        for existing_group in self.extraction_context['all_groups']:
            if self._is_similar_group_name(existing_group['name'], group_name):
                return existing_group
        
        # Create new main group
        main_group = {
            'offer_item_group_id': new_group.get('offer_item_group_id', str(uuid.uuid4())),
            'name': group_name,
            'group_type': 'BASE',
            'offer_groups': []
        }
        
        self.extraction_context['all_groups'].append(main_group)
        return main_group
    
    def _find_or_create_sub_group(self, main_group: Dict[str, Any], new_sub_group: Dict[str, Any]) -> Dict[str, Any]:
        """Find existing sub-group or create new one"""
        sub_group_name = new_sub_group['name'].strip()
        
        # Look for existing sub-group
        for existing_sub in main_group['offer_groups']:
            if self._is_similar_group_name(existing_sub['name'], sub_group_name):
                return existing_sub
        
        # Create new sub-group
        sub_group = {
            'offer_item_group_id': new_sub_group.get('offer_item_group_id', str(uuid.uuid4())),
            'name': sub_group_name,
            'group_type': 'SUB',
            'offer_items': []
        }
        
        main_group['offer_groups'].append(sub_group)
        return sub_group
    
    def _is_similar_group_name(self, name1: str, name2: str) -> bool:
        """Check if two group names are similar"""
        # Normalize names for comparison
        norm1 = re.sub(r'[^\w\s]', '', name1.lower()).strip()
        norm2 = re.sub(r'[^\w\s]', '', name2.lower()).strip()
        
        # Check for exact match or significant overlap
        if norm1 == norm2:
            return True
        
        # Check if one contains the other (for partial matches)
        if len(norm1) > 10 and len(norm2) > 10:
            return norm1 in norm2 or norm2 in norm1
        
        return False
    
    def _build_final_offer_structure(self) -> Dict[str, Any]:
        """Build final offer structure with incremental hierarchical IDs"""
        # Assign incremental IDs to main groups
        for main_index, main_group in enumerate(self.extraction_context['all_groups'], 1):
            main_group['offer_item_group_id'] = str(main_index)
            
            # Assign incremental IDs to sub-groups
            for sub_index, sub_group in enumerate(main_group.get('offer_groups', []), 1):
                sub_group['offer_item_group_id'] = f"{main_index}.{sub_index}"
                
                # Assign incremental IDs to items
                for item_index, item in enumerate(sub_group.get('offer_items', []), 1):
                    item['offer_item_id'] = f"{main_index}.{sub_index}.{item_index}"
                    
                    # Add parent references for easy navigation
                    item['parent_sub_group_id'] = sub_group['offer_item_group_id']
                    item['parent_main_group_id'] = main_group['offer_item_group_id']
                
                # Add parent reference to sub-group
                sub_group['parent_main_group_id'] = main_group['offer_item_group_id']
        
        return {
            'offer_item_groups': self.extraction_context['all_groups'],
            'total_main_groups': len(self.extraction_context['all_groups']),
            'total_items': self.extraction_context['item_counter'],
            'id_structure': {
                'main_groups': f"1 to {len(self.extraction_context['all_groups'])}",
                'sub_groups': "X.Y format where X is main group ID",
                'items': "X.Y.Z format where X.Y is sub-group ID"
            }
        }

    def _assign_hierarchical_ids(self):
        """Alternative method to assign IDs after all extraction is complete"""
        main_counter = 1
        
        for main_group in self.extraction_context['all_groups']:
            # Assign main group ID
            main_group['offer_item_group_id'] = str(main_counter)
            
            sub_counter = 1
            for sub_group in main_group.get('offer_groups', []):
                # Assign sub-group ID
                sub_group['offer_item_group_id'] = f"{main_counter}.{sub_counter}"
                sub_group['parent_main_group_id'] = str(main_counter)
                
                item_counter = 1
                for item in sub_group.get('offer_items', []):
                    # Assign item ID
                    item['offer_item_id'] = f"{main_counter}.{sub_counter}.{item_counter}"
                    item['parent_sub_group_id'] = f"{main_counter}.{sub_counter}"
                    item['parent_main_group_id'] = str(main_counter)
                    
                    item_counter += 1
                
                sub_counter += 1
            
            main_counter += 1

    def _validate_id_structure(self) -> bool:
        """Validate that all IDs follow the correct hierarchical pattern"""
        try:
            for main_group in self.extraction_context['all_groups']:
                main_id = main_group['offer_item_group_id']
                
                # Validate main ID is a number
                if not main_id.isdigit():
                    print(f"Invalid main group ID: {main_id}")
                    return False
                
                for sub_group in main_group.get('offer_groups', []):
                    sub_id = sub_group['offer_item_group_id']
                    
                    # Validate sub ID format (X.Y)
                    if not re.match(rf"^{main_id}\.\d+$", sub_id):
                        print(f"Invalid sub group ID: {sub_id} for main group {main_id}")
                        return False
                    
                    for item in sub_group.get('offer_items', []):
                        item_id = item['offer_item_id']
                        
                        # Validate item ID format (X.Y.Z)
                        if not re.match(rf"^{sub_id}\.\d+$", item_id):
                            print(f"Invalid item ID: {item_id} for sub group {sub_id}")
                            return False
            
            return True
            
        except Exception as e:
            print(f"ID validation error: {e}")
            return False
    
    def _count_total_items(self, structure: Dict[str, Any]) -> int:
        """Count total items in structure"""
        total = 0
        for main_group in structure.get('offer_item_groups', []):
            for sub_group in main_group.get('offer_groups', []):
                total += len(sub_group.get('offer_items', []))
        return total
    
    def _clean_chunk_content(self, content: str) -> str:
        """Clean chunk content"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip image references
            if line.startswith('![](') and line.endswith('.jpeg)'):
                continue
                
            # Skip total/summary lines
            if any(keyword in line.lower() for keyword in ['total', 'fr.', '................', 'a reporter']):
                continue
                
            # Skip empty lines with only dots or dashes
            if re.match(r'^[\.\-\s]*$', line):
                continue
                
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)



