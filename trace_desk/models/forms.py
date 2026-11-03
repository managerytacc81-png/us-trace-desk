"""
Aviation Airworthiness & Chain of Custody Form Models.
Conforming to FAA Order 8130.21J, AC 43-9D, EASA Part 21/145 standards.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class Form8130_3(BaseModel):
    """
    FAA Form 8130-3 (Airworthiness Approval Tag).
    Supports label-based mapping across revisions (Order 8130.21J, 8130.21H, 8130.21G).
    Fields default to None/empty so incomplete scans can be modeled and audited.
    """
    document_id: str = Field(..., description="Unique document tracking ID or filename")
    form_edition: Optional[str] = Field("8130.21J", description="Form revision / Order version")

    # Block 1: Approving Competent Authority / Country
    block_1_country: Optional[str] = Field(None, description="Approving Civil Aviation Authority / Country, e.g. USA / FAA")
    
    # Block 2: Organization Name and Address
    block_2_org_name_address: Optional[str] = Field(None, description="Issuing organization name and physical address")
    
    # Block 3: Form Tracking Number
    block_3_form_tracking_no: Optional[str] = Field(None, description="Unique preprinted or generated form tracking number")
    
    # Block 4: Organization Certificate / Approval Number
    block_4_org_cert_no: Optional[str] = Field(None, description="FAA Certificate number (Part 21 PC/PMA/TSO or Part 145 CRS)")
    
    # Block 5: Work Order / Contract / Invoice Number
    block_5_work_order: Optional[str] = Field(None, description="Cross-reference work order, contract, or invoice number")
    
    # Block 6: Item Number
    block_6_item: Optional[str] = Field("1", description="Line item number")
    
    # Block 7: Description
    block_7_description: Optional[str] = Field(None, description="Part description or official nomenclature")
    
    # Block 8: Part Number
    block_8_part_number: Optional[str] = Field(None, description="Manufacturer part number")
    
    # Block 9: Eligibility
    block_9_eligibility: Optional[str] = Field("N/A", description="Aircraft/engine eligibility or 'N/A' per 8130.21J")
    
    # Block 10: Quantity
    block_10_quantity: Optional[int] = Field(None, description="Quantity of parts released")
    
    # Block 11: Status / Work
    block_11_status: Optional[str] = Field(None, description="Status/work term (e.g. NEW, OVERHAULED, REPAIRED, INSPECTED)")
    
    # Block 12: Remarks
    block_12_remarks: Optional[str] = Field(None, description="Remarks (TSN/CSN, AD compliance, repair spec, direct ship auth)")

    # Left-hand block: Block 13a-e Part 21 Production Release (New parts)
    block_13a_part_21_cert: bool = Field(default=False, description="Part 21 compliance checkbox/certification")
    block_13b_signature: Optional[str] = Field(None, description="Authorized signature for Block 13")
    block_13c_approval_no: Optional[str] = Field(None, description="Approval/Authorization Number (DMIR/DAR/PC)")
    block_13d_name: Optional[str] = Field(None, description="Typed/printed certifier name")
    block_13e_date: Optional[str] = Field(None, description="Date of Block 13 signature (DD/MMM/YYYY)")
    block_13_shaded: bool = Field(default=False, description="True if Block 13 is grayed out/shaded/voided")

    # Right-hand block: Block 14a-e Part 43 Maintenance Release (Return to Service)
    block_14a_part_43_cert: bool = Field(default=False, description="14 CFR 43.9 return-to-service certification")
    block_14b_signature: Optional[str] = Field(None, description="Authorized signature for Block 14")
    block_14c_approval_no: Optional[str] = Field(None, description="Repair Station Certificate / Inspector Authorization No.")
    block_14d_name: Optional[str] = Field(None, description="Typed/printed certifier name")
    block_14e_date: Optional[str] = Field(None, description="Date of Block 14 signature (DD/MMM/YYYY)")
    block_14_shaded: bool = Field(default=False, description="True if Block 14 is grayed out/shaded/voided")

    # Forgery & Mandatory Notice Boilerplate
    user_installer_responsibilities_boilerplate_present: bool = Field(
        default=True,
        description="Mandatory installer notice boilerplate text present on face or reverse per FAA Order 8130.21"
    )
    oem_claimed: Optional[str] = Field(None, description="OEM named on form or component (e.g. CFM, GE, Pratt, Rolls)")
    serial_number: Optional[str] = Field(None, description="Serial number if identified in Block 12 or Block 8")
    
    # Raw printed label overrides for legacy renumbered forms
    raw_labels_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Maps printed label text to standard block fields"
    )


class EASAForm1(BaseModel):
    """EASA Form 1 Authorized Release Certificate."""
    document_id: str = Field(..., description="Unique document tracking ID or filename")
    approving_competent_authority: Optional[str] = Field(None, description="Competent authority, e.g. EASA, LBA, DGAC")
    organization_name_address: Optional[str] = Field(None, description="Issuing organization name and address")
    form_tracking_number: Optional[str] = Field(None, description="Unique tracking number")
    organization_approval_number: Optional[str] = Field(None, description="Part 145 or Part 21 approval number")
    work_order_invoice: Optional[str] = Field(None, description="Work order or contract reference")
    item: Optional[str] = "1"
    description: Optional[str] = Field(None, description="Article description")
    part_number: Optional[str] = Field(None, description="Part number")
    eligibility: Optional[str] = "N/A"
    quantity: Optional[int] = 1
    status_work: Optional[str] = Field(None, description="Status/work description")
    remarks: Optional[str] = Field(None, description="Remarks block")
    cert_type: str = "MAINTENANCE" # "PRODUCTION" or "MAINTENANCE"
    authorized_signature: Optional[str] = None
    approval_certificate_no: Optional[str] = None
    certifier_name: Optional[str] = None
    date: Optional[str] = None
    opposing_block_shaded: bool = True
    user_responsibilities_notice_present: bool = True
    serial_number: Optional[str] = None


class LogbookEntry(BaseModel):
    """Airframe or Engine Logbook entry documenting installation / removal event."""
    document_id: str = Field(..., description="Unique document tracking ID or filename")
    date: Optional[str] = Field(None, description="Date of logbook entry")
    aircraft_registration: Optional[str] = None
    engine_serial_number: Optional[str] = None
    part_number: Optional[str] = None
    serial_number: Optional[str] = None
    action_type: Optional[str] = "REMOVAL" # "INSTALLATION", "REMOVAL", "INSPECTION"
    airframe_hours_tsn: Optional[float] = None
    airframe_cycles_csn: Optional[int] = None
    part_hours_tsn: Optional[float] = None
    part_cycles_csn: Optional[int] = None
    technician_signature: Optional[str] = None
    technician_certificate: Optional[str] = None
    remarks: Optional[str] = None


class RemovalTag(BaseModel):
    """Serviceable / Teardown Removal Tag (Yellow / Green tag)."""
    document_id: str = Field(..., description="Unique document tracking ID or filename")
    tag_number: Optional[str] = None
    date: Optional[str] = None
    removing_organization: Optional[str] = None
    aircraft_registration: Optional[str] = None
    engine_serial_number: Optional[str] = None
    part_number: Optional[str] = None
    serial_number: Optional[str] = None
    reason_for_removal: Optional[str] = None
    part_hours_tsn: Optional[float] = None
    part_cycles_csn: Optional[int] = None
    inspector_name: Optional[str] = None
    inspector_certificate_no: Optional[str] = None


class WorkOrder(BaseModel):
    """MRO / Repair Station Teardown & Work Order record."""
    document_id: str = Field(..., description="Unique document tracking ID or filename")
    work_order_no: Optional[str] = None
    date: Optional[str] = None
    repair_station_name: Optional[str] = None
    repair_station_cert: Optional[str] = None
    part_number: Optional[str] = None
    serial_number: Optional[str] = None
    work_performed: Optional[str] = None
    incoming_tsn: Optional[float] = None
    incoming_csn: Optional[int] = None
    outgoing_tsn: Optional[float] = None
    outgoing_csn: Optional[int] = None
    authorized_signoff: Optional[str] = None


class BillOfSale(BaseModel):
    """Commercial Bill of Sale / Ownership Transfer Statement."""
    document_id: str = Field(..., description="Unique document tracking ID or filename")
    document_no: Optional[str] = None
    date: Optional[str] = None
    seller: Optional[str] = None
    buyer: Optional[str] = None
    part_number: Optional[str] = None
    serial_number: Optional[str] = None
    has_non_incident_statement: bool = True
    trace_affidavit_present: bool = True
