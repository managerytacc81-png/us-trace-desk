from enum import Enum
from typing import List, Optional, Tuple, Union, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from trace_desk.models.forms import (
    Form8130_3, EASAForm1, LogbookEntry, RemovalTag, WorkOrder, BillOfSale
)


class DocumentType(str, Enum):
    FORM_8130_3 = "FORM_8130_3"
    EASA_FORM_1 = "EASA_FORM_1"
    LOGBOOK = "LOGBOOK"
    REMOVAL_TAG = "REMOVAL_TAG"
    WORK_ORDER = "WORK_ORDER"
    BILL_OF_SALE = "BILL_OF_SALE"
    UNKNOWN = "UNKNOWN"


class BtBDocument(BaseModel):
    document_id: str
    doc_type: DocumentType
    file_path: Optional[str] = None
    extracted_date: Optional[str] = None
    part_number: Optional[str] = None
    serial_number: Optional[str] = None
    # Concrete parsed data
    form_8130: Optional[Form8130_3] = None
    easa_form_1: Optional[EASAForm1] = None
    logbook: Optional[LogbookEntry] = None
    removal_tag: Optional[RemovalTag] = None
    work_order: Optional[WorkOrder] = None
    bill_of_sale: Optional[BillOfSale] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

    def get_event_date(self) -> Optional[str]:
        if self.extracted_date:
            return self.extracted_date
        if self.form_8130:
            return self.form_8130.block_14e_date or self.form_8130.block_13e_date
        if self.easa_form_1:
            return self.easa_form_1.date
        if self.logbook:
            return self.logbook.date
        if self.removal_tag:
            return self.removal_tag.date
        if self.work_order:
            return self.work_order.date
        if self.bill_of_sale:
            return self.bill_of_sale.date
        return None

    def get_hours_cycles(self) -> Tuple[Optional[float], Optional[int]]:
        """Returns (hours_tsn, cycles_csn) if available."""
        if self.logbook:
            return self.logbook.part_hours_tsn, self.logbook.part_cycles_csn
        if self.removal_tag:
            return self.removal_tag.part_hours_tsn, self.removal_tag.part_cycles_csn
        if self.work_order:
            h = self.work_order.outgoing_tsn if self.work_order.outgoing_tsn is not None else self.work_order.incoming_tsn
            c = self.work_order.outgoing_csn if self.work_order.outgoing_csn is not None else self.work_order.incoming_csn
            return h, c
        return None, None


class BtBTracePackage(BaseModel):
    package_id: str = Field(..., description="Package identifier, e.g. BTB-CFM56-0042")
    part_number: str = Field(..., description="Target assembly or component part number")
    serial_number: str = Field(..., description="Target serial number")
    description: str = Field(default="Aviation Component", description="Nomenclature description")
    is_life_limited: bool = Field(default=False, description="Flag indicating if part is an LLP")
    life_limit_cycles: Optional[int] = Field(None, description="Published mandatory cycle limit")
    life_limit_hours: Optional[float] = Field(None, description="Published mandatory hour limit")
    documents: List[BtBDocument] = Field(default_factory=list)

    def get_8130_forms(self) -> List[Form8130_3]:
        forms = []
        for doc in self.documents:
            if doc.form_8130:
                forms.append(doc.form_8130)
        return forms

    def get_chronological_events(self) -> List[BtBDocument]:
        """Returns documents ordered by event date where parsable."""
        def parse_date(doc: BtBDocument):
            d_str = doc.get_event_date()
            if not d_str:
                return datetime.min
            for fmt in ("%Y-%m-%d", "%d/%b/%Y", "%d-%b-%Y", "%m/%d/%Y", "%Y/%m/%d", "%d.%m.%Y"):
                try:
                    return datetime.strptime(d_str.strip(), fmt)
                except ValueError:
                    pass
            return datetime.min

        return sorted(self.documents, key=parse_date)

    def get_ownership_transfers(self) -> List[BillOfSale]:
        bos_list = []
        for doc in self.documents:
            if doc.bill_of_sale:
                bos_list.append(doc.bill_of_sale)
        return bos_list
