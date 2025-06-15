# src/processors/structure_delimiter_extractor.py
import json
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate

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
        
        self.structure_prompt = get_structure_prompt()
        
    
    def extract_structure_from_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structure with delimiters from all chunks"""
        
        print("Phase 2: Extracting structure with delimiters from chunks...")

        # Reset state for new document
        self.section_state = {
            'last_main_id': 0,
            'last_sub_ids': {},
            'last_item_ids': {},
            'all_sections': []
        }
        
        for chunk in chunks:
            chunk_sections = self._analyze_chunk_structure_with_context(chunk)
            self.section_state['all_sections'].extend(chunk_sections)
            self._update_section_state(chunk_sections)

        print("Consolidating sections from all chunks...")
        final_structure = self._build_final_structure()
        
        print(f"  Found {len(self.section_state['all_sections'])} sections across chunks")
        print(f"  Final structure: {final_structure.get('total_sections', 0)} sections")
        
        return final_structure, self.section_state['all_sections']
    
    def _analyze_chunk_structure_with_context(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze chunk structure with previous context"""
        try:
            chunk_info = f"Chunk {chunk['chunk_index'] + 1}/{chunk['total_chunks']} | Chars: {chunk['start_char']}-{chunk['end_char']}"
            
            # Prepare previous context
            previous_context = self._format_previous_context()
            
            response = self.llm.invoke(
                self.structure_prompt.format(
                    chunk_content=chunk['content'],
                    chunk_info=chunk_info,
                    previous_output=previous_context
                )
            )
            
            print(f"    Analyzing chunk {chunk['chunk_index']} with context...")
            
            # Extract JSON
            result = self.json_cleaner.extract_json(response)
            
            if not result:
                print(f"    Warning: Could not extract valid JSON from chunk {chunk['chunk_index']}")
                print(f"    Response: {response}")
                return []
            
            # Process and validate sections
            sections = result.get('sections', [])
            validated_sections = []
            
            for section in sections:
                # Add chunk information
                section['chunk_id'] = chunk['chunk_id']
                section['chunk_index'] = chunk['chunk_index']
                
                # Validate and fix section_id if needed
                section_id = self._validate_section_id(section)
                section['section_id'] = section_id
                
                # Clean title
                section['title'] = self._clean_section_title(section.get('title', ''))
                
                validated_sections.append(section)
            
            print(f"    Successfully extracted {len(validated_sections)} sections from chunk {chunk['chunk_index']}")
            return validated_sections
            
        except Exception as e:
            print(f"    Error analyzing chunk {chunk['chunk_id']}: {e}")
            return []
    
    def _format_previous_context(self) -> str:
        """Format previous sections for context"""
        if not self.section_state['all_sections']:
            return "No previous sections (this is the first chunk)"
        
        # Get last few sections for context
        recent_sections = self.section_state['all_sections'][-5:]  # Last 5 sections
        
        context_lines = ["Recent sections from previous chunks:"]
        for section in recent_sections:
            context_lines.append(
                f"- {section['section_id']}: {section['title']} (Level {section['level']}, Type: {section['section_type']})"
            )
        
        # Add current state summary
        context_lines.append(f"\nCurrent state:")
        context_lines.append(f"- Last main category ID: {self.section_state['last_main_id']}")
        context_lines.append(f"- Active sub-categories: {list(self.section_state['last_sub_ids'].keys())}")
        
        return "\n".join(context_lines)
    
    def _validate_section_id(self, section: Dict[str, Any]) -> str:
        """Validate and generate proper section ID"""
        proposed_id = section.get('section_id', '')
        level = section.get('level', 1)
        
        # Parse proposed ID
        id_parts = proposed_id.split('.')
        
        if level == 1:
            # Main category
            if len(id_parts) == 1 and id_parts[0].isdigit():
                main_id = int(id_parts[0])
                # Ensure it's the next logical main ID
                expected_main_id = self.section_state['last_main_id'] + 1
                if main_id != expected_main_id:
                    return str(expected_main_id)
                return proposed_id
            else:
                # Generate next main ID
                return str(self.section_state['last_main_id'] + 1)
        
        elif level == 2:
            # Sub-category
            if len(id_parts) == 2 and all(part.isdigit() for part in id_parts):
                main_id, sub_id = int(id_parts[0]), int(id_parts[1])
                # Validate main_id exists
                if main_id <= self.section_state['last_main_id']:
                    expected_sub_id = self.section_state['last_sub_ids'].get(main_id, 0) + 1
                    return f"{main_id}.{expected_sub_id}"
            
            # Generate based on current main category
            current_main = self.section_state['last_main_id']
            if current_main == 0:
                current_main = 1
                self.section_state['last_main_id'] = 1
            
            next_sub = self.section_state['last_sub_ids'].get(current_main, 0) + 1
            return f"{current_main}.{next_sub}"
        
        elif level == 3:
            # Detailed item
            if len(id_parts) == 3 and all(part.isdigit() for part in id_parts):
                main_id, sub_id, item_id = int(id_parts[0]), int(id_parts[1]), int(id_parts[2])
                parent_key = f"{main_id}.{sub_id}"
                
                # Validate parent exists
                if main_id <= self.section_state['last_main_id'] and sub_id <= self.section_state['last_sub_ids'].get(main_id, 0):
                    expected_item_id = self.section_state['last_item_ids'].get(parent_key, 0) + 1
                    return f"{parent_key}.{expected_item_id}"
            
            # Generate based on current sub-category
            current_main = self.section_state['last_main_id']
            current_sub = self.section_state['last_sub_ids'].get(current_main, 0)
            
            if current_main == 0 or current_sub == 0:
                # Need to create parent structure
                if current_main == 0:
                    current_main = 1
                    self.section_state['last_main_id'] = 1
                if current_sub == 0:
                    current_sub = 1
                    self.section_state['last_sub_ids'][current_main] = 1
            
            parent_key = f"{current_main}.{current_sub}"
            next_item = self.section_state['last_item_ids'].get(parent_key, 0) + 1
            return f"{parent_key}.{next_item}"
        
        return "1"  # Fallback
    
    def _update_section_state(self, sections: List[Dict[str, Any]]):
        """Update section state tracking"""
        for section in sections:
            section_id = section['section_id']
            level = section['level']
            id_parts = [int(p) for p in section_id.split('.')]
            
            if level == 1:
                self.section_state['last_main_id'] = max(self.section_state['last_main_id'], id_parts[0])
            
            elif level == 2:
                main_id, sub_id = id_parts[0], id_parts[1]
                self.section_state['last_main_id'] = max(self.section_state['last_main_id'], main_id)
                self.section_state['last_sub_ids'][main_id] = max(
                    self.section_state['last_sub_ids'].get(main_id, 0), 
                    sub_id
                )
            
            elif level == 3:
                main_id, sub_id, item_id = id_parts[0], id_parts[1], id_parts[2]
                self.section_state['last_main_id'] = max(self.section_state['last_main_id'], main_id)
                self.section_state['last_sub_ids'][main_id] = max(
                    self.section_state['last_sub_ids'].get(main_id, 0), 
                    sub_id
                )
                parent_key = f"{main_id}.{sub_id}"
                self.section_state['last_item_ids'][parent_key] = max(
                    self.section_state['last_item_ids'].get(parent_key, 0), 
                    item_id
                )
    
    def _build_final_structure(self) -> Dict[str, Any]:
        """Build final consolidated structure with hierarchical nesting"""
        all_sections = self.section_state['all_sections']
        
        # First, add parent-child relationships to all sections
        for section in all_sections:
            section_id = section['section_id']
            id_parts = section_id.split('.')
            
            if len(id_parts) > 1:
                parent_id = '.'.join(id_parts[:-1])
                section['parent_section_id'] = parent_id
            else:
                section['parent_section_id'] = None
            
            # Initialize children list
            section['child_sections'] = []
        
        # Build hierarchical structure
        hierarchical_sections = self._build_hierarchical_tree(all_sections)
        
        # Statistics
        main_categories = [s for s in all_sections if s['level'] == 1]
        sub_categories = [s for s in all_sections if s['level'] == 2]
        detailed_items = [s for s in all_sections if s['level'] == 3]
        
        return {
            'total_sections': len(all_sections),
            'main_categories': list(set(s.get('section_type', '') for s in main_categories)),
            'sections': hierarchical_sections,  # Now hierarchical instead of flat
            'flat_sections': all_sections,      # Keep flat version for reference
            'hierarchy_summary': {
                'main_categories': len(main_categories),
                'sub_categories': len(sub_categories), 
                'detailed_items': len(detailed_items)
            }
        }

    def _build_hierarchical_tree(self, flat_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert flat sections list to hierarchical tree structure"""
        # Create a dictionary to hold all nodes by their section_id
        nodes = {}
        
        # Create deep copies of sections and initialize children
        for section in flat_sections:
            section_copy = section.copy()
            section_copy['child_sections'] = []
            nodes[section['section_id']] = section_copy
        
        # Build the tree structure
        root_nodes = []
        
        for section in flat_sections:
            section_id = section['section_id']
            parent_id = section.get('parent_section_id')
            
            if parent_id and parent_id in nodes:
                # Add this section as a child of its parent
                nodes[parent_id]['child_sections'].append(nodes[section_id])
            else:
                # This is a root node (level 1)
                root_nodes.append(nodes[section_id])
        
        return root_nodes

    def _build_hierarchical_tree_alternative(self, flat_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Alternative implementation using level-based approach"""
        # Group sections by level
        sections_by_level = {1: [], 2: [], 3: []}
        
        for section in flat_sections:
            level = section.get('level', 1)
            section_copy = section.copy()
            section_copy['child_sections'] = []
            sections_by_level[level].append(section_copy)
        
        # Create lookup dictionary
        section_lookup = {s['section_id']: s for level_sections in sections_by_level.values() 
                        for s in level_sections}
        
        # Build hierarchy level by level
        # Level 3 items (detailed items) - no children
        for item in sections_by_level[3]:
            parent_id = item.get('parent_section_id')
            if parent_id and parent_id in section_lookup:
                section_lookup[parent_id]['child_sections'].append(item)
        
        # Level 2 items (sub-categories) - may have level 3 children
        for sub_cat in sections_by_level[2]:
            parent_id = sub_cat.get('parent_section_id')
            if parent_id and parent_id in section_lookup:
                section_lookup[parent_id]['child_sections'].append(sub_cat)
        
        # Return level 1 items (main categories) with all their nested children
        return sections_by_level[1]
    
    
    def _clean_section_title(self, title: str) -> str:
        """Clean section title from formatting artifacts"""
        if not title:
            return ""
        
        # Remove markdown formatting
        title = re.sub(r'^#+\s*', '', title)
        
        # Remove numbering artifacts that are not part of the actual title
        title = re.sub(r'^\d+\.\s*[A-Z]\.\s*\d+\.\s*', '', title)
        
        # Clean up common patterns
        title = re.sub(r'\s+', ' ', title)  # Multiple spaces
        title = title.strip()
        
        return title

        """Simple fallback consolidation"""
        # Remove duplicates based on title similarity
        unique_sections = []
        seen_titles = set()
        
        for section in all_sections:
            title_key = section.get('title', '').lower().strip()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_sections.append(section)
        
        return {
            'total_sections': len(unique_sections),
            'main_categories': list(set(s.get('section_type', '') for s in unique_sections)),
            'sections': unique_sections
        }