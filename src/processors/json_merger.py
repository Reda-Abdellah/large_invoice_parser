# src/processors/json_merger.py
from typing import List, Dict, Any
from datetime import datetime
from ..models.invoice_models import ProcessedInvoice, InvoiceItem, DocumentStructure

class JsonMerger:
    def __init__(self):
        pass
    
    def merge_analyses(self, analyzed_sections: List[Dict[str, Any]], 
                      original_structure: DocumentStructure) -> ProcessedInvoice:
        """Merge all section analyses into final JSON"""
        
        # Extract all items
        all_items = []
        processing_metadata = {
            'sections_processed': len(analyzed_sections),
            'processing_timestamp': datetime.now().isoformat(),
            'errors': []
        }
        
        for section_analysis in analyzed_sections:
            if 'error' in section_analysis:
                processing_metadata['errors'].append({
                    'section': section_analysis['section_title'],
                    'error': section_analysis['error']
                })
                continue
            
            items_data = section_analysis['analysis'].get('items', [])
            for item_data in items_data:
                try:
                    item = InvoiceItem(**item_data)
                    all_items.append(item)
                except Exception as e:
                    processing_metadata['errors'].append({
                        'section': section_analysis['section_title'],
                        'item_error': str(e),
                        'item_data': item_data
                    })
        
        # Extract invoice metadata
        invoice_metadata = self._extract_invoice_metadata(analyzed_sections)
        
        # Calculate totals
        total_amount = sum(item.total_price for item in all_items if item.total_price)
        
        return ProcessedInvoice(
            invoice_id=invoice_metadata.get('invoice_id'),
            date=invoice_metadata.get('date'),
            vendor=invoice_metadata.get('vendor'),
            customer=invoice_metadata.get('customer'),
            total_amount=total_amount if total_amount > 0 else None,
            currency=invoice_metadata.get('currency'),
            structure=original_structure,
            items=all_items,
            processing_metadata=processing_metadata
        )
    
    def _extract_invoice_metadata(self, analyzed_sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract invoice-level metadata from section analyses"""
        metadata = {}
        
        for section_analysis in analyzed_sections:
            if 'error' in section_analysis:
                continue
                
            section_meta = section_analysis['analysis'].get('section_metadata', {})
            
            # Look for contact info, dates, etc.
            if section_meta.get('contains_contact_info'):
                # Try to extract vendor/customer info
                pass
            
            if section_meta.get('contains_dates'):
                # Try to extract invoice date
                pass
        
        return metadata
