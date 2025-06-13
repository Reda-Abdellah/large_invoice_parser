# src/models/pipeline_state.py
from typing_extensions import TypedDict
from typing import List, Dict, Any, Optional
from .invoice_models import ProcessedOffer

class PipelineState(TypedDict):
    raw_markdown: str
    document_structure: Optional[Any]
    chunked_sections: List[Dict[str, Any]]
    analyzed_sections: List[Dict[str, Any]]
    final_json: Optional[ProcessedOffer]
    processing_errors: List[str]
