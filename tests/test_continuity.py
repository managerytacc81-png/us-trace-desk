"""
Test Suite: Chain of Custody & Continuity Rules.
FAA Order 8130.21J, 14 CFR 43.10, AC 120-84, and AC 43-9D.
"""
import pytest
from trace_desk.models.package import BtBTracePackage, BtBDocument, DocumentType
from trace_desk.models.forms import (
    RemovalTag, WorkOrder, BillOfSale, Form8130_3
)
from trace_desk.models.exceptions import ExceptionSeverity
from trace_desk.rules.continuity import ContinuityChecker


@pytest.fixture
def clean_llp_package() -> BtBTracePackage:
    return BtBTracePackage(
        package_id="PKG-LLP-CONTINUOUS",
        part_number="322-049-204-0",
        serial_number="SN-CFM-88912",
        description="BUSHING SHRD (IGV)",
        is_life_limited=True,
        life_limit_cycles=20000,
        life_limit_hours=50000.0,
        documents=[
            BtBDocument(
                document_id="DOC-01-REMOVAL",
                doc_type=DocumentType.REMOVAL_TAG,
                extracted_date="2025-10-10",
                part_number="322-049-204-0",
                serial_number="SN-CFM-88912",
                removal_tag=RemovalTag(
                    document_id="DOC-01-REMOVAL",
                    tag_number="TAG-01",
                    date="2025-10-10",
                    removing_organization="United Airlines",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-88912",
                    reason_for_removal="Engine scheduled removal",
                    part_hours_tsn=12000.0,
                    part_cycles_csn=5000,
                    inspector_name="T. Miller"
                )
            ),
            BtBDocument(
                document_id="DOC-02-BOS-AIRLINE",
                doc_type=DocumentType.BILL_OF_SALE,
                extracted_date="2025-11-01",
                part_number="322-049-204-0",
                serial_number="SN-CFM-88912",
                bill_of_sale=BillOfSale(
                    document_id="DOC-02-BOS-AIRLINE",
                    document_no="BOS-01",
                    date="2025-11-01",
                    seller="United Airlines",
                    buyer="AeroCore LLC",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-88912",
                    has_non_incident_statement=True,
                    trace_affidavit_present=True
                )
            ),
            BtBDocument(
                document_id="DOC-03-WORK-ORDER",
                doc_type=DocumentType.WORK_ORDER,
                extracted_date="2025-12-05",
                part_number="322-049-204-0",
                serial_number="SN-CFM-88912",
                work_order=WorkOrder(
                    document_id="DOC-03-WORK-ORDER",
                    work_order_no="WO-991",
                    date="2025-12-05",
                    repair_station_name="Delta TechOps",
                    repair_station_cert="CRS DALR026A",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-88912",
                    work_performed="Overhaul per CMM",
                    incoming_tsn=12000.0,
                    incoming_csn=5000,
                    outgoing_tsn=12000.0,
                    outgoing_csn=5000,
                    authorized_signoff="J. Smith"
                )
            )
        ]
    )


def test_clean_continuity_passes(clean_llp_package):
    exceptions = ContinuityChecker.check_package(clean_llp_package)
    assert len(exceptions) == 0


def test_serial_number_mismatch_detected(clean_llp_package):
    # Alter serial on doc 3
    clean_llp_package.documents[2].serial_number = "SN-CFM-99999" # Mismatched serial!
    clean_llp_package.documents[2].work_order.serial_number = "SN-CFM-99999"

    exceptions = ContinuityChecker.check_package(clean_llp_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-COC-02-SN-MISMATCH" in rule_ids
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)


def test_part_number_mismatch_detected(clean_llp_package):
    clean_llp_package.documents[0].part_number = "WRONG-PN-111"
    clean_llp_package.documents[0].removal_tag.part_number = "WRONG-PN-111"

    exceptions = ContinuityChecker.check_package(clean_llp_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-COC-01-PN-MISMATCH" in rule_ids


def test_negative_cycle_accumulation_discontinuity(clean_llp_package):
    # Event 1 in Oct 2025 has CSN 5000
    # Make Event 3 in Dec 2025 have CSN 3500 (cycles decreased by 1500!)
    clean_llp_package.documents[2].work_order.incoming_csn = 3500
    clean_llp_package.documents[2].work_order.outgoing_csn = 3500

    exceptions = ContinuityChecker.check_package(clean_llp_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-COC-04-CYCLE-DISCONTINUITY" in rule_ids
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)


def test_negative_hour_accumulation_discontinuity(clean_llp_package):
    # Event 1 in Oct 2025 has TSN 12000.0 hrs
    # Make Event 3 in Dec 2025 have TSN 9000.0 hrs (decreased!)
    clean_llp_package.documents[2].work_order.incoming_tsn = 9000.0
    clean_llp_package.documents[2].work_order.outgoing_tsn = 9000.0

    exceptions = ContinuityChecker.check_package(clean_llp_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-COC-05-HOUR-DISCONTINUITY" in rule_ids


def test_llp_life_limit_exceeded(clean_llp_package):
    clean_llp_package.life_limit_cycles = 10000
    clean_llp_package.documents[2].work_order.outgoing_csn = 10500 # Exceeds 10,000 limit

    exceptions = ContinuityChecker.check_package(clean_llp_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-COC-06-LIFE-LIMIT-EXCEEDED" in rule_ids
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)


def test_broken_ownership_chain(clean_llp_package):
    # Add a second Bill of Sale where seller != buyer of previous BOS
    # Previous BOS transferred to "AeroCore LLC"
    gap_bos = BtBDocument(
        document_id="DOC-04-BOS-GAP",
        doc_type=DocumentType.BILL_OF_SALE,
        extracted_date="2026-01-10",
        part_number="322-049-204-0",
        serial_number="SN-CFM-88912",
        bill_of_sale=BillOfSale(
            document_id="DOC-04-BOS-GAP",
            document_no="BOS-02",
            date="2026-01-10",
            seller="Untraced Foreign Broker LLC", # Gap: not AeroCore LLC!
            buyer="Final Dealer Inc",
            part_number="322-049-204-0",
            serial_number="SN-CFM-88912",
            has_non_incident_statement=True
        )
    )
    clean_llp_package.documents.append(gap_bos)

    exceptions = ContinuityChecker.check_package(clean_llp_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-COC-07-OWNERSHIP-GAP" in rule_ids


def test_missing_non_incident_statement(clean_llp_package):
    clean_llp_package.documents[1].bill_of_sale.has_non_incident_statement = False

    exceptions = ContinuityChecker.check_package(clean_llp_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-COC-08-NO-INCIDENT-STATEMENT" in rule_ids
