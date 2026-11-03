"""
Test Suite: Suspected Unapproved Parts (SUP) & Forgery Red Flags.
Covers AOG Technics case indicators: boilerplate omissions, ungrayed blocks,
OEM nomenclature mismatches, and signatory cert discrepancies.
"""
import pytest
from trace_desk.models.forms import Form8130_3
from trace_desk.models.package import BtBTracePackage
from trace_desk.models.exceptions import ExceptionSeverity, ExceptionCategory
from trace_desk.rules.sup_forgery import SupForgeryChecker


@pytest.fixture
def base_package() -> BtBTracePackage:
    return BtBTracePackage(
        package_id="PKG-SUP-TEST",
        part_number="322-049-204-0",
        serial_number="SN-CFM-88912",
        description="BUSHING SHRD (IGV)"
    )


def test_clean_form_no_sup_red_flags(base_package):
    form = Form8130_3(
        document_id="DOC-CLEAN-SUP",
        block_1_country="USA / FAA",
        block_2_org_name_address="Delta TechOps",
        block_3_form_tracking_no="DAL-9921",
        block_4_org_cert_no="CRS DALR026A",
        block_7_description="BUSHING SHRD (IGV)",
        block_8_part_number="322-049-204-0",
        block_11_status="OVERHAULED",
        block_12_remarks="Overhauled per CMM.",
        block_14a_part_43_cert=True,
        block_14b_signature="J. Smith",
        block_14c_approval_no="CRS DALR026A",
        block_14d_name="John Smith",
        block_14e_date="2026-01-20",
        block_13_shaded=True,
        block_14_shaded=False,
        user_installer_responsibilities_boilerplate_present=True,
        serial_number="SN-CFM-88912"
    )
    exceptions = SupForgeryChecker.check_form(form, base_package)
    assert len(exceptions) == 0


def test_missing_user_installer_boilerplate_flagged(base_package):
    form = Form8130_3(
        document_id="DOC-AOG-BOILERPLATE-OMITTED",
        block_1_country="USA / FAA",
        block_2_org_name_address="AOG Technics Ltd",
        block_3_form_tracking_no="AOG-001",
        block_4_org_cert_no="CRS AOG123",
        block_7_description="BUSHING SHRD (IGV)",
        block_8_part_number="322-049-204-0",
        block_11_status="OVERHAULED",
        block_12_remarks="Remarks text",
        block_14a_part_43_cert=True,
        block_14b_signature="F. Smith",
        block_14c_approval_no="CRS AOG123",
        block_14d_name="F. Smith",
        block_14e_date="2026-01-20",
        block_13_shaded=True,
        block_14_shaded=False,
        user_installer_responsibilities_boilerplate_present=False # Flagged!
    )
    exceptions = SupForgeryChecker.check_form(form, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-SUP-01-BOILERPLATE" in rule_ids
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)


def test_unshaded_block_13_in_maintenance_release(base_package):
    form = Form8130_3(
        document_id="DOC-UNSHADED-BOX",
        block_1_country="USA / FAA",
        block_2_org_name_address="Dubious MRO",
        block_3_form_tracking_no="DUB-001",
        block_4_org_cert_no="CRS DUB123",
        block_7_description="BUSHING SHRD (IGV)",
        block_8_part_number="322-049-204-0",
        block_11_status="OVERHAULED",
        block_12_remarks="Remarks text",
        block_14a_part_43_cert=True,
        block_14b_signature="Signer",
        block_14c_approval_no="CRS DUB123",
        block_14d_name="Signer",
        block_14e_date="2026-01-20",
        block_13_shaded=False, # Box NOT shaded!
        block_14_shaded=False,
        user_installer_responsibilities_boilerplate_present=True
    )
    exceptions = SupForgeryChecker.check_form(form, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-SUP-02-SHADING" in rule_ids


def test_oem_terminology_mismatch_bushing(base_package):
    # Prompt specific requirement: 'bushing' vs 'bushing shrd (IGV)'
    form = Form8130_3(
        document_id="DOC-NOMENCLATURE-TRAP",
        block_1_country="USA / FAA",
        block_2_org_name_address="Delta TechOps",
        block_3_form_tracking_no="DAL-001",
        block_4_org_cert_no="CRS DALR026A",
        block_7_description="bushing", # Generic lay term instead of BUSHING SHRD (IGV)
        block_8_part_number="322-049-204-0",
        block_11_status="OVERHAULED",
        block_12_remarks="Remarks",
        block_14a_part_43_cert=True,
        block_14b_signature="Signer",
        block_14c_approval_no="CRS DALR026A",
        block_14d_name="Signer",
        block_14e_date="2026-01-20",
        block_13_shaded=True,
        user_installer_responsibilities_boilerplate_present=True
    )
    exceptions = SupForgeryChecker.check_form(form, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-SUP-03-NOMENCLATURE" in rule_ids
    assert any("BUSHING SHRD (IGV)" in e.finding for e in exceptions)


def test_block_4_vs_block_14c_cert_mismatch(base_package):
    form = Form8130_3(
        document_id="DOC-CERT-MISMATCH",
        block_1_country="USA / FAA",
        block_2_org_name_address="Legitimate MRO Name",
        block_3_form_tracking_no="LEG-001",
        block_4_org_cert_no="CRS 8OFR272Y", # Real CRS cited in Block 4
        block_7_description="BUSHING SHRD (IGV)",
        block_8_part_number="322-049-204-0",
        block_11_status="OVERHAULED",
        block_12_remarks="Remarks",
        block_14a_part_43_cert=True,
        block_14b_signature="Signer",
        block_14c_approval_no="CRS 999FAKE88", # Fraudulent signer cert in Block 14c!
        block_14d_name="Signer",
        block_14e_date="2026-01-20",
        block_13_shaded=True,
        user_installer_responsibilities_boilerplate_present=True
    )
    exceptions = SupForgeryChecker.check_form(form, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-SUP-04-CERT-MISMATCH" in rule_ids
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)
