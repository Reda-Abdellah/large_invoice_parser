# src/models/pipeline_state.py
from typing_extensions import TypedDict
from typing import List, Dict, Any, Optional
from ..models.invoice_models import ProcessedInvoice, DocumentStructure

class PipelineState(TypedDict):
    raw_markdown: str
    document_structure: Optional[DocumentStructure]
    chunked_sections: List[Dict[str, Any]]
    analyzed_sections: List[Dict[str, Any]]
    final_json: Optional[ProcessedInvoice]
    processing_errors: List[str]