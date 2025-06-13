# src/models/invoice_models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

class GroupType(str, Enum):
    BASE = "BASE"
    SUB = "SUB"

class OfferItemType(str, Enum):
    NORMAL = "NORMAL"
    OPTIONAL = "OPTIONAL"
    VARIANT = "VARIANT"

class UnitType(str, Enum):
    MATERIAL = "MATERIAL"
    LABOR = "LABOR"
    SERVICE = "SERVICE"

class BillingPercentSituation(BaseModel):
    situation_id: Optional[str] = None
    percentage: float = 0
    description: Optional[str] = None

class GanttSchedule(BaseModel):
    schedule_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration: Optional[int] = None

class OfferVariant(BaseModel):
    variant_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    price_difference: float = 0

class OfferArticle(BaseModel):
    article_id: str
    article_number: str
    name: str
    description: Optional[str] = None

class OfferItem(BaseModel):
    offer_item_id: str = Field(default_factory=lambda: f"generated_{datetime.now().timestamp()}")
    name: str
    offer_item_type: OfferItemType = OfferItemType.NORMAL
    supplier_id: Optional[str] = None
    unit_quantity: float = 0
    unit_type: UnitType = UnitType.MATERIAL
    percentage: float = 0
    unit: str = ""
    unit_price: float = 0
    margin: float = 25
    auction_discount: float = 0
    supplier_discount_goal: float = 0
    billing_percent_situations: List[BillingPercentSituation] = []
    gantt_schedules: List[GanttSchedule] = []
    progress: float = 0
    employees_ids: List[str] = []
    article_id: str = ""
    article_number: str = ""
    desc_html: str = ""
    is_ttc: bool = False
    taxes_rate_percent: float = 0
    apply_discount: bool = False
    isPageBreakBefore: bool = False
    isSellingPriceLocked: bool = False
    isInvalid: bool = False
    isCostPriceLocked: bool = False
    discount_value: float = 0
    is_optional: bool = False
    variants: List[OfferVariant] = []
    articles: List[OfferArticle] = []
    
    # Additional fields for processing context
    section: Optional[str] = None
    category: Optional[str] = None

class OfferItemGroup(BaseModel):
    offer_item_group_id: str = Field(default_factory=lambda: f"group_{datetime.now().timestamp()}")
    name: str
    group_type: GroupType = GroupType.BASE
    default_margin: float = 25
    offer_groups: List['OfferItemGroup'] = []
    offer_items: List[OfferItem] = []
    
    # Additional metadata
    section_level: Optional[int] = None
    parent_group_id: Optional[str] = None

class ProcessedOffer(BaseModel):
    offer_id: Optional[str] = None
    offer_number: Optional[str] = None
    date: Optional[datetime] = None
    vendor: Optional[str] = None
    customer: Optional[str] = None
    project_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "EUR"
    default_margin: float = 25
    offer_item_groups: List[OfferItemGroup]
    processing_metadata: Dict[str, Any] = {}

# Update the pipeline state
class PipelineState(BaseModel):
    raw_markdown: str
    document_structure: Optional[Any] = None
    chunked_sections: List[Dict[str, Any]] = []
    analyzed_sections: List[Dict[str, Any]] = []
    final_json: Optional[ProcessedOffer] = None
    processing_errors: List[str] = []
