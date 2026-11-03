from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ExceptionSeverity(str, Enum):
    CRITICAL = "CRITICAL"  # High risk of counterfeit, illegal release, or invalid airworthiness
    MAJOR = "MAJOR"        # Regulatory non-compliance, missing block, or custody jump
    MINOR = "MINOR"        # Clerical error, non-blocking formatting issue
    WARNING = "WARNING"    # Advisory notification / clarification suggested
    INFO = "INFO"          # Informational notice


class ExceptionCategory(str, Enum):
    COMPLETENESS_8130 = "COMPLETENESS_8130"
    SUP_FORGERY_RED_FLAG = "SUP_FORGERY_RED_FLAG"
    CHAIN_OF_CUSTODY = "CHAIN_OF_CUSTODY"
    STATUS_TERM_LEGALITY = "STATUS_TERM_LEGALITY"
    DATA_DISCREPANCY = "DATA_DISCREPANCY"


class AuditDisposition(str, Enum):
    PASS = "PASS"                         # Clean back-to-birth trace; airworthy
    CONDITIONAL_PASS = "CONDITIONAL_PASS" # Minor clerical discrepancies remediable via vendor memo
    REJECT_SUP_ALERT = "REJECT_SUP_ALERT" # Critical red flags; suspected unapproved part / broken trace


class AuditException(BaseModel):
    exception_id: str = Field(..., description="Unique exception identifier, e.g. EXP-001")
    rule_id: str = Field(..., description="Rule code, e.g. R-8130-COMP, R-SUP-FORGERY")
    rule_name: str = Field(..., description="Human-readable rule name")
    category: ExceptionCategory
    severity: ExceptionSeverity
    document_id: Optional[str] = Field(None, description="Tracking ID or filename of affected document")
    document_type: Optional[str] = Field(None, description="Form 8130-3, Logbook, Removal Tag, etc.")
    block_ref: Optional[str] = Field(None, description="Specific block reference, e.g. Block 11, Block 13/14")
    finding: str = Field(..., description="Concise statement of discrepancy")
    regulatory_ref: str = Field(..., description="Governing authority (e.g. FAA Order 8130.21J, AC 43-9D, FAA SUP Notice)")
    details: str = Field(..., description="Detailed diagnostic context and observed values")
    recommendation: str = Field(..., description="Actionable remedial advice for dealer quality manager")


class ExceptionReport(BaseModel):
    audit_id: str = Field(..., description="Unique audit package docket number")
    package_name: str = Field(..., description="Name or identifier of ingested BtB package")
    timestamp: str = Field(..., description="UTC ISO timestamp of audit execution")
    auditor: str = Field(default="USM Trace Exception-Audit Engine v1.0", description="Auditor identity")
    part_number: str = Field(..., description="Primary part number audited")
    serial_number: str = Field(..., description="Primary serial number audited")
    part_description: str = Field(default="Aviation Article", description="Nomenclature description")
    is_life_limited: bool = Field(default=False, description="Whether part is Life-Limited (LLP)")
    life_limit_cycles: Optional[int] = Field(None, description="Published mandatory cycle life limit if LLP")
    life_limit_hours: Optional[float] = Field(None, description="Mandatory hour life limit if applicable")
    current_tsn: Optional[float] = Field(None, description="Current Flight Hours (Time Since New)")
    current_csn: Optional[int] = Field(None, description="Current Flight Cycles (Cycles Since New)")
    remaining_cycles: Optional[int] = Field(None, description="Calculated remaining cycles before scrap")
    total_documents_analyzed: int = Field(default=0)
    audit_score: float = Field(..., ge=0.0, le=100.0, description="Overall trace compliance score (0-100)")
    disposition: AuditDisposition = Field(..., description="Final operational determination")
    exceptions: List[AuditException] = Field(default_factory=list)
    custody_chain_summary: List[Dict[str, Any]] = Field(default_factory=list)
    rule_summary: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
