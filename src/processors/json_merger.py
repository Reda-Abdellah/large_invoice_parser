# src/processors/json_merger.py
from typing import List, Dict, Any
from datetime import datetime
import uuid
from ..models.invoice_models import (
    ProcessedOffer, OfferItem, OfferItemGroup, GroupType, 
    OfferItemType, UnitType
)

class JsonMerger:
    def __init__(self):
        pass
    
    def merge_analyses(self, analyzed_sections: List[Dict[str, Any]], 
                      original_structure: Any) -> ProcessedOffer:
        """Merge all section analyses into hierarchical offer structure"""
        
        processing_metadata = {
            'sections_processed': len(analyzed_sections),
            'processing_timestamp': datetime.now().isoformat(),
            'errors': []
        }
        
        # Build hierarchical structure
        offer_item_groups = self._build_hierarchical_groups(analyzed_sections)
        
        # Extract offer metadata
        offer_metadata = self._extract_offer_metadata(analyzed_sections)
        
        # Calculate totals
        total_amount = self._calculate_total_amount(offer_item_groups)
        
        return ProcessedOffer(
            offer_id=offer_metadata.get('offer_id'),
            offer_number=offer_metadata.get('offer_number'),
            date=offer_metadata.get('date'),
            vendor=offer_metadata.get('vendor'),
            customer=offer_metadata.get('customer'),
            project_name=offer_metadata.get('project_name'),
            total_amount=total_amount,
            currency=offer_metadata.get('currency', 'EUR'),
            default_margin=offer_metadata.get('default_margin', 25),
            offer_item_groups=offer_item_groups,
            processing_metadata=processing_metadata
        )
    
    def _build_hierarchical_groups(self, analyzed_sections: List[Dict[str, Any]]) -> List[OfferItemGroup]:
        """Build hierarchical offer item groups from analyzed sections"""
        groups_by_level = {}
        root_groups = []
        
        for section_analysis in analyzed_sections:
            if 'error' in section_analysis:
                continue
            
            section_title = section_analysis['section_title']
            section_level = section_analysis.get('section_level', 1)
            analysis_data = section_analysis['analysis']
            
            # Create offer items from analysis
            offer_items = []
            for item_data in analysis_data.get('offer_items', []):
                try:
                    # Generate unique ID
                    item_data['offer_item_id'] = str(uuid.uuid4())
                    
                    # Set defaults and validate types
                    item_data.setdefault('offer_item_type', 'NORMAL')
                    item_data.setdefault('unit_type', 'MATERIAL')
                    item_data.setdefault('margin', 25)
                    item_data.setdefault('unit_quantity', 0)
                    item_data.setdefault('unit_price', 0)
                    item_data.setdefault('unit', '')
                    
                    # Convert to proper enums
                    if item_data['offer_item_type'] not in ['NORMAL', 'OPTIONAL', 'VARIANT']:
                        item_data['offer_item_type'] = 'NORMAL'
                    
                    if item_data['unit_type'] not in ['MATERIAL', 'LABOR', 'SERVICE']:
                        item_data['unit_type'] = 'MATERIAL'
                    
                    offer_item = OfferItem(**item_data)
                    offer_items.append(offer_item)
                    
                except Exception as e:
                    print(f"Error creating offer item: {e}")
                    continue
            
            # Determine group type based on level
            group_type = GroupType.BASE if section_level <= 2 else GroupType.SUB
            
            # Get default margin from section metadata
            section_metadata = analysis_data.get('section_metadata', {})
            default_margin = section_metadata.get('default_margin', 25)
            
            # Create offer item group
            group = OfferItemGroup(
                offer_item_group_id=str(uuid.uuid4()),
                name=section_title,
                group_type=group_type,
                default_margin=default_margin,
                offer_groups=[],
                offer_items=offer_items,
                section_level=section_level
            )
            
            groups_by_level[section_level] = groups_by_level.get(section_level, [])
            groups_by_level[section_level].append(group)
        
        # Build hierarchy
        if not groups_by_level:
            return []
        
        # Start with level 1 (base groups)
        root_groups = groups_by_level.get(1, [])
        
        # Nest sub-groups
        for level in sorted(groups_by_level.keys())[1:]:
            parent_level = level - 1
            if parent_level in groups_by_level:
                parent_groups = groups_by_level[parent_level]
                current_groups = groups_by_level[level]
                
                # Simple nesting - add sub-groups to the last parent group
                if parent_groups and current_groups:
                    parent_groups[-1].offer_groups.extend(current_groups)
        
        return root_groups
    
    def _calculate_total_amount(self, offer_item_groups: List[OfferItemGroup]) -> float:
        """Calculate total amount from all offer items"""
        total = 0.0
        
        def calculate_group_total(group: OfferItemGroup) -> float:
            group_total = 0.0
            
            # Add items in this group
            for item in group.offer_items:
                item_total = item.unit_quantity * item.unit_price
                # Apply margin
                item_total *= (1 + item.margin / 100)
                group_total += item_total
            
            # Add sub-groups
            for sub_group in group.offer_groups:
                group_total += calculate_group_total(sub_group)
            
            return group_total
        
        for group in offer_item_groups:
            total += calculate_group_total(group)
        
        return total
    
    def _extract_offer_metadata(self, analyzed_sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract offer-level metadata from section analyses"""
        metadata = {
            'offer_id': str(uuid.uuid4()),
            'default_margin': 25,
            'currency': 'EUR'
        }
        
        for section_analysis in analyzed_sections:
            if 'error' in section_analysis:
                continue
                
            section_meta = section_analysis['analysis'].get('section_metadata', {})
            
            # Extract project information from section titles
            section_title = section_analysis.get('section_title', '')
            if any(keyword in section_title.lower() for keyword in ['project', 'projet', 'chantier']):
                metadata['project_name'] = section_title
            
            # Look for offer numbers in content
            # This could be enhanced with regex patterns
            
        return metadata
