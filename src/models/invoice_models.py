# src/models/invoice_models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class InvoiceItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    category: Optional[str] = None
    section: str

class InvoiceSection(BaseModel):
    title: str
    level: int
    content: str
    items: List[InvoiceItem] = []
    subsections: List['InvoiceSection'] = []

class DocumentStructure(BaseModel):
    sections: List[InvoiceSection]
    metadata: Dict[str, Any] = {}

class ProcessedInvoice(BaseModel):
    invoice_id: Optional[str] = None
    date: Optional[datetime] = None
    vendor: Optional[str] = None
    customer: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    structure: DocumentStructure
    items: List[InvoiceItem]
    processing_metadata: Dict[str, Any] = {}


