# src/models/pipeline_state.py
from typing_extensions import TypedDict
from typing import List, Dict, Any, Optional
from .invoice_models import ProcessedOffer

class PipelineState(TypedDict):
    raw_markdown: str
    translated_markdown: Optional[str]
    overlapping_chunks: List[Dict[str, Any]]
    structure_with_delimiters: Optional[Dict[str, Any]]
    final_json: Optional[ProcessedOffer]
    final_json_translated: Optional[ProcessedOffer]
    processing_errors: List[str]