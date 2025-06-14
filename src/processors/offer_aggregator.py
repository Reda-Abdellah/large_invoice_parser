# src/processors/offer_aggregator.py
from typing import List, Dict, Any
from datetime import datetime
import uuid
from ..models.invoice_models import (
    ProcessedOffer, OfferItem, OfferItemGroup, GroupType, 
    OfferItemType, UnitType
)

class OfferAggregator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def aggregate_and_format(self, section_analyses: List[Dict[str, Any]]) -> ProcessedOffer:
        """Aggregate all section analyses into final offer structure"""
        
        print("Phase 4: Aggregating and formatting final offer...")
        
        processing_metadata = {
            'sections_processed': len(section_analyses),
            'processing_timestamp': datetime.now().isoformat(),
            'errors': [],
            'total_items_extracted': 0
        }
        
        # Build hierarchical structure
        offer_item_groups = self._build_hierarchical_structure(section_analyses, processing_metadata)
        
        # Extract offer metadata
        offer_metadata = self._extract_offer_metadata(section_analyses)
        
        # Calculate totals
        total_amount = self._calculate_total_amount(offer_item_groups)
        
        # Count total items
        total_items = self._count_total_items(offer_item_groups)
        processing_metadata['total_items_extracted'] = total_items
        
        print(f"  Created {len(offer_item_groups)} main groups with {total_items} total items")
        print(f"  Estimated total amount: {total_amount:.2f} EUR")
        
        return ProcessedOffer(
            offer_id=offer_metadata.get('offer_id', str(uuid.uuid4())),
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
    
    def _build_hierarchical_structure(self, section_analyses: List[Dict[str, Any]], 
                                    processing_metadata: Dict[str, Any]) -> List[OfferItemGroup]:
        """Build hierarchical offer structure from section analyses"""
        groups_by_level = {}
        
        for analysis in section_analyses:
            if 'error' in analysis:
                processing_metadata['errors'].append({
                    'section': analysis.get('original_section', {}).get('title', 'Unknown'),
                    'error': analysis['error']
                })
                continue
            
            section_analysis = analysis.get('section_analysis', {})
            offer_items_data = analysis.get('offer_items', [])
            
            # Create offer items
            offer_items = []
            for item_data in offer_items_data:
                try:
                    offer_item = self._create_offer_item(item_data, section_analysis)
                    offer_items.append(offer_item)
                except Exception as e:
                    processing_metadata['errors'].append({
                        'section': section_analysis.get('section_title', 'Unknown'),
                        'item_error': str(e),
                        'item_data': item_data
                    })
            
            # Create offer item group
            level = analysis.get('original_section', {}).get('level', 1)
            group_type = GroupType.BASE if level <= 2 else GroupType.SUB
            
            group = OfferItemGroup(
                offer_item_group_id=section_analysis.get('section_id', str(uuid.uuid4())),
                name=section_analysis.get('section_title', 'Unnamed Section'),
                group_type=group_type,
                default_margin=section_analysis.get('default_margin', 25),
                offer_groups=[],
                offer_items=offer_items,
                section_level=level
            )
            
            if level not in groups_by_level:
                groups_by_level[level] = []
            groups_by_level[level].append(group)
        
        # Build hierarchy
        return self._organize_hierarchy(groups_by_level)
    
    def _create_offer_item(self, item_data: Dict[str, Any], 
                          section_analysis: Dict[str, Any]) -> OfferItem:
        """Create OfferItem from extracted data"""
        # Set defaults
        item_data.setdefault('offer_item_id', str(uuid.uuid4()))
        item_data.setdefault('offer_item_type', 'NORMAL')
        item_data.setdefault('unit_type', 'MATERIAL')
        item_data.setdefault('margin', section_analysis.get('default_margin', 25))
        item_data.setdefault('unit_quantity', 0)
        item_data.setdefault('unit_price', 0)
        item_data.setdefault('unit', '')
        item_data.setdefault('desc_html', f"<p>{item_data.get('name', '')}</p>")
        
        # Validate enums
        if item_data['offer_item_type'] not in ['NORMAL', 'OPTIONAL', 'VARIANT']:
            item_data['offer_item_type'] = 'NORMAL'
        
        if item_data['unit_type'] not in ['MATERIAL', 'LABOR', 'SERVICE']:
            item_data['unit_type'] = 'MATERIAL'
        
        # Add section context
        item_data['section'] = section_analysis.get('section_title')
        item_data['category'] = section_analysis.get('section_type')
        
        return OfferItem(**item_data)
    
    def _organize_hierarchy(self, groups_by_level: Dict[int, List[OfferItemGroup]]) -> List[OfferItemGroup]:
        """Organize groups into proper hierarchy"""
        if not groups_by_level:
            return []
        
        # Start with level 1 groups
        root_groups = groups_by_level.get(1, [])
        
        # Nest sub-groups into parent groups
        for level in sorted(groups_by_level.keys())[1:]:
            parent_level = level - 1
            if parent_level in groups_by_level:
                parent_groups = groups_by_level[parent_level]
                current_groups = groups_by_level[level]
                
                # Simple nesting strategy: distribute sub-groups among parents
                if parent_groups and current_groups:
                    groups_per_parent = len(current_groups) // len(parent_groups) + 1
                    
                    for i, sub_group in enumerate(current_groups):
                        parent_index = min(i // groups_per_parent, len(parent_groups) - 1)
                        parent_groups[parent_index].offer_groups.append(sub_group)
        
        return root_groups
    
    def _calculate_total_amount(self, offer_item_groups: List[OfferItemGroup]) -> float:
        """Calculate total offer amount"""
        def calculate_group_total(group: OfferItemGroup) -> float:
            total = 0.0
            
            # Add items in this group
            for item in group.offer_items:
                item_total = item.unit_quantity * item.unit_price
                # Apply margin
                item_total *= (1 + item.margin / 100)
                total += item_total
            
            # Add sub-groups
            for sub_group in group.offer_groups:
                total += calculate_group_total(sub_group)
            
            return total
        
        return sum(calculate_group_total(group) for group in offer_item_groups)
    
    def _count_total_items(self, offer_item_groups: List[OfferItemGroup]) -> int:
        """Count total items across all groups"""
        def count_group_items(group: OfferItemGroup) -> int:
            count = len(group.offer_items)
            for sub_group in group.offer_groups:
                count += count_group_items(sub_group)
            return count
        
        return sum(count_group_items(group) for group in offer_item_groups)
    
    def _extract_offer_metadata(self, section_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract offer-level metadata"""
        metadata = {
            'offer_id': str(uuid.uuid4()),
            'default_margin': 25,
            'currency': 'EUR'
        }
        
        # Look for project information in section titles
        for analysis in section_analyses:
            section_analysis = analysis.get('section_analysis', {})
            title = section_analysis.get('section_title', '')
            
            if any(keyword in title.lower() for keyword in ['project', 'projet', 'chantier']):
                metadata['project_name'] = title
                break
        
        return metadata
