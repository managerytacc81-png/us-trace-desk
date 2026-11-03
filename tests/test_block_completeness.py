"""
Test Suite: FAA Form 8130-3 Block Completeness Rules.
FAA Order 8130.21J and AC 43-9D.
"""
import pytest
from trace_desk.models.forms import Form8130_3
from trace_desk.models.package import BtBTracePackage, BtBDocument, DocumentType
from trace_desk.models.exceptions import ExceptionSeverity, ExceptionCategory
from trace_desk.rules.block_completeness import BlockCompletenessChecker, normalize_by_labels


@pytest.fixture
def base_package() -> BtBTracePackage:
    return BtBTracePackage(
        package_id="PKG-TEST-001",
        part_number="322-049-204-0",
        serial_number="SN-TEST-01",
        description="BUSHING SHRD (IGV)"
    )


@pytest.fixture
def valid_8130() -> Form8130_3:
    return Form8130_3(
        document_id="DOC-8130-VALID",
        block_1_country="USA / FAA",
        block_2_org_name_address="Delta TechOps, Atlanta GA",
        block_3_form_tracking_no="DAL-2026-001",
        block_4_org_cert_no="CRS DALR026A",
        block_5_work_order="WO-1001",
        block_7_description="BUSHING SHRD (IGV)",
        block_8_part_number="322-049-204-0",
        block_10_quantity=1,
        block_11_status="OVERHAULED",
        block_12_remarks="Overhauled per CMM. TSN: 5000, CSN: 2000",
        block_14a_part_43_cert=True,
        block_14b_signature="J. Smith",
        block_14c_approval_no="CRS DALR026A",
        block_14d_name="John Smith",
        block_14e_date="2026-01-15",
        block_13_shaded=True,
        block_14_shaded=False,
        user_installer_responsibilities_boilerplate_present=True,
        serial_number="SN-TEST-01"
    )


def test_valid_8130_passes_completeness(valid_8130, base_package):
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    assert len(exceptions) == 0


def test_missing_block_1_fails(valid_8130, base_package):
    valid_8130.block_1_country = ""
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-BLK-01" in rule_ids
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)


def test_missing_block_2_org_address(valid_8130, base_package):
    valid_8130.block_2_org_name_address = None
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-BLK-02" in rule_ids


def test_missing_block_3_tracking_no(valid_8130, base_package):
    valid_8130.block_3_form_tracking_no = ""
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-BLK-03" in rule_ids


def test_missing_block_4_cert_no(valid_8130, base_package):
    valid_8130.block_4_org_cert_no = ""
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-BLK-04" in rule_ids
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)


def test_missing_block_8_part_number(valid_8130, base_package):
    valid_8130.block_8_part_number = ""
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-BLK-08" in rule_ids


def test_missing_block_11_status(valid_8130, base_package):
    valid_8130.block_11_status = None
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-BLK-11" in rule_ids


def test_missing_block_12_remarks(valid_8130, base_package):
    valid_8130.block_12_remarks = ""
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-BLK-12" in rule_ids


def test_unsigned_neither_13_nor_14(valid_8130, base_package):
    # Strip both Block 13 and 14
    valid_8130.block_14a_part_43_cert = False
    valid_8130.block_14b_signature = None
    valid_8130.block_14c_approval_no = None
    valid_8130.block_14d_name = None
    valid_8130.block_14e_date = None

    valid_8130.block_13a_part_21_cert = False
    valid_8130.block_13b_signature = None

    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-NO-RELEASE" in rule_ids


def test_incomplete_block_14_signature(valid_8130, base_package):
    valid_8130.block_14b_signature = None # Missing signature
    exceptions = BlockCompletenessChecker.check_form_8130(valid_8130, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-8130-BLK14-INCOMP" in rule_ids


def test_production_block_13_release(base_package):
    prod_8130 = Form8130_3(
        document_id="DOC-PROD-8130",
        block_1_country="USA / FAA",
        block_2_org_name_address="CFM International Evendale OH",
        block_3_form_tracking_no="CFM-2026-900",
        block_4_org_cert_no="PC-42",
        block_7_description="BUSHING SHRD (IGV)",
        block_8_part_number="322-049-204-0",
        block_10_quantity=1,
        block_11_status="NEW",
        block_12_remarks="Factory new production conformity release.",
        block_13a_part_21_cert=True,
        block_13b_signature="M. Vance",
        block_13c_approval_no="PC-42",
        block_13d_name="Mark Vance",
        block_13e_date="2026-02-01",
        block_13_shaded=False,
        block_14_shaded=True,
        user_installer_responsibilities_boilerplate_present=True,
        serial_number="SN-NEW-01"
    )
    exceptions = BlockCompletenessChecker.check_form_8130(prod_8130, base_package)
    assert len(exceptions) == 0


def test_legacy_printed_label_normalization():
    # Simulate older edition where block fields were labeled differently
    legacy_form = Form8130_3(
        document_id="DOC-LEGACY-01",
        raw_labels_mapping={
            "Approving Competent Authority / Country": "USA / FAA",
            "Organization Name and Address": "Vintage CRS 123",
            "Form Tracking Number": "LEG-9912",
            "Organization Certificate": "CRS VNT123",
            "Description": "BUSHING SHRD (IGV)",
            "Part Number": "322-049-204-0",
            "Quantity": "2",
            "Status / Work": "OVERHAULED",
            "Remarks": "Legacy tag remarks"
        }
    )
    normalized = normalize_by_labels(legacy_form)
    assert normalized.block_1_country == "USA / FAA"
    assert normalized.block_2_org_name_address == "Vintage CRS 123"
    assert normalized.block_8_part_number == "322-049-204-0"
    assert normalized.block_10_quantity == 2
