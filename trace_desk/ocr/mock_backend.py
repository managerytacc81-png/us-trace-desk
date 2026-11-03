"""
Deterministic Mock Backend for Testing and Offline Audits.
Provides 100% reproducible document extraction from synthetic fixtures or registered test payloads.
"""
import json
from pathlib import Path
from typing import Dict, Optional, Any, Union
from trace_desk.ocr.base import BaseOCRBackend
from trace_desk.models.package import BtBDocument, DocumentType
from trace_desk.models.forms import (
    Form8130_3, EASAForm1, LogbookEntry, RemovalTag, WorkOrder, BillOfSale
)


class DeterministicMockBackend(BaseOCRBackend):
    """
    Mock OCR backend that returns deterministic structured document models.
    Can load directly from registered objects or test fixture JSON/text files.
    """

    def __init__(self):
        self._registry: Dict[str, BtBDocument] = {}

    def register(self, key: str, doc: BtBDocument) -> None:
        """Register a mock BtBDocument keyed by filepath or filename."""
        self._registry[key] = doc
        self._registry[Path(key).name] = doc

    def extract_text(self, file_path: str) -> str:
        p = Path(file_path)
        if p.exists() and p.suffix in (".txt", ".json"):
            return p.read_text(encoding="utf-8")
        return f"[MOCK_OCR_EXTRACTED_TEXT for {p.name}]"

    def extract_document(
        self,
        file_path: str,
        doc_type: Optional[DocumentType] = None
    ) -> BtBDocument:
        p = Path(file_path)
        lookup_keys = [str(file_path), p.name, p.stem]

        for k in lookup_keys:
            if k in self._registry:
                return self._registry[k]

        # If file is a JSON payload fixture on disk
        if p.exists() and p.suffix.lower() == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return BtBDocument.model_validate(data)
            except Exception:
                pass

        # Deterministic heuristic synthesis based on filename
        stem_lower = p.stem.lower()

        if "8130" in stem_lower:
            return BtBDocument(
                document_id=p.stem,
                doc_type=DocumentType.FORM_8130_3,
                file_path=str(file_path),
                extracted_date="2026-03-15",
                part_number="322-049-204-0",
                serial_number="SN-CFM-88912",
                form_8130=Form8130_3(
                    document_id=p.stem,
                    block_1_country="USA / FAA",
                    block_2_org_name_address="Delta TechOps, Atlanta GA 30320",
                    block_3_form_tracking_no="DAL-2026-8812",
                    block_4_org_cert_no="CRS DALR026A",
                    block_5_work_order="WO-998214",
                    block_7_description="BUSHING SHRD (IGV)",
                    block_8_part_number="322-049-204-0",
                    block_10_quantity=1,
                    block_11_status="OVERHAULED",
                    block_12_remarks="Overhauled per CFM56-7B CMM 72-21-01. Dual FAA/EASA release. TSN: 12500.0, CSN: 5400",
                    block_14a_part_43_cert=True,
                    block_14b_signature="J. Henderson",
                    block_14c_approval_no="CRS DALR026A",
                    block_14d_name="John Henderson",
                    block_14e_date="2026-03-15",
                    block_13_shaded=True,
                    block_14_shaded=False,
                    user_installer_responsibilities_boilerplate_present=True,
                    serial_number="SN-CFM-88912"
                )
            )

        if "removal" in stem_lower or "tag" in stem_lower:
            return BtBDocument(
                document_id=p.stem,
                doc_type=DocumentType.REMOVAL_TAG,
                file_path=str(file_path),
                extracted_date="2026-02-10",
                part_number="322-049-204-0",
                serial_number="SN-CFM-88912",
                removal_tag=RemovalTag(
                    document_id=p.stem,
                    tag_number="TAG-7721",
                    date="2026-02-10",
                    removing_organization="United Airlines SFO Line Maint",
                    aircraft_registration="N14206",
                    engine_serial_number="ESN-874211",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-88912",
                    reason_for_removal="Engine scheduled shop visit",
                    part_hours_tsn=12500.0,
                    part_cycles_csn=5400,
                    inspector_name="T. Miller",
                    inspector_certificate_no="A&P 3488210"
                )
            )

        if "work_order" in stem_lower or "wo" in stem_lower:
            return BtBDocument(
                document_id=p.stem,
                doc_type=DocumentType.WORK_ORDER,
                file_path=str(file_path),
                extracted_date="2026-03-01",
                part_number="322-049-204-0",
                serial_number="SN-CFM-88912",
                work_order=WorkOrder(
                    document_id=p.stem,
                    work_order_no="WO-998214",
                    date="2026-03-01",
                    repair_station_name="Delta TechOps",
                    repair_station_cert="CRS DALR026A",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-88912",
                    work_performed="NDI inspection, ultrasonic test, bushing dimensional restoration",
                    incoming_tsn=12500.0,
                    incoming_csn=5400,
                    outgoing_tsn=12500.0,
                    outgoing_csn=5400,
                    authorized_signoff="J. Henderson"
                )
            )

        if "bill_of_sale" in stem_lower or "bos" in stem_lower or "sale" in stem_lower:
            return BtBDocument(
                document_id=p.stem,
                doc_type=DocumentType.BILL_OF_SALE,
                file_path=str(file_path),
                extracted_date="2026-03-20",
                part_number="322-049-204-0",
                serial_number="SN-CFM-88912",
                bill_of_sale=BillOfSale(
                    document_id=p.stem,
                    document_no="BOS-2026-042",
                    date="2026-03-20",
                    seller="United Airlines Asset Management",
                    buyer="Apex Aerospace Components LLC",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-88912",
                    has_non_incident_statement=True,
                    trace_affidavit_present=True
                )
            )

        # Default fallback
        return BtBDocument(
            document_id=p.stem,
            doc_type=doc_type or DocumentType.UNKNOWN,
            file_path=str(file_path),
            extracted_date="2026-01-01",
            raw_payload={"mock_notice": f"Generic extraction for {file_path}"}
        )
