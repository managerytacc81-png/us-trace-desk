"""
Test Suite: Block 11 Status/Work Term Legality (Post-2025 FAA/EASA Standard).
FAA Order 8130.21J para 3-5(k) & 14 CFR 43.3.
"""
import pytest
from trace_desk.models.forms import Form8130_3
from trace_desk.models.package import BtBTracePackage
from trace_desk.models.exceptions import ExceptionSeverity
from trace_desk.rules.term_legality import TermLegalityChecker


@pytest.fixture
def base_package() -> BtBTracePackage:
    return BtBTracePackage(
        package_id="PKG-TERM-TEST",
        part_number="322-049-204-0",
        serial_number="SN-TERM-01"
    )


@pytest.fixture
def base_maint_form() -> Form8130_3:
    return Form8130_3(
        document_id="DOC-TERM-8130",
        block_1_country="USA / FAA",
        block_2_org_name_address="Delta TechOps",
        block_3_form_tracking_no="FTN-01",
        block_4_org_cert_no="CRS DALR026A",
        block_7_description="BUSHING SHRD (IGV)",
        block_8_part_number="322-049-204-0",
        block_11_status="OVERHAULED",
        block_12_remarks="Overhauled.",
        block_14a_part_43_cert=True,
        block_14b_signature="J. Smith",
        block_14c_approval_no="CRS DALR026A",
        block_14d_name="John Smith",
        block_14e_date="2026-01-15",
        block_13_shaded=True,
        block_14_shaded=False,
        user_installer_responsibilities_boilerplate_present=True
    )


@pytest.mark.parametrize("legal_term", ["OVERHAULED", "REPAIRED", "INSPECTED", "TESTED", "MODIFIED"])
def test_authorized_maintenance_terms_pass(base_maint_form, base_package, legal_term):
    base_maint_form.block_11_status = legal_term
    exceptions = TermLegalityChecker.check_form(base_maint_form, base_package)
    assert len(exceptions) == 0


def test_serviceable_is_strictly_prohibited(base_maint_form, base_package):
    # 'SERVICEABLE' is a classic warehouse error prohibited on FAA Form 8130-3 Block 11
    base_maint_form.block_11_status = "SERVICEABLE"
    exceptions = TermLegalityChecker.check_form(base_maint_form, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-TERM-01-PROHIBITED" in rule_ids
    assert any("SERVICEABLE" in e.finding for e in exceptions)
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)


@pytest.mark.parametrize("prohibited_term", ["AS REMOVED", "AR", "REBUILT", "CHECKED", "OVERHAUL", "REPAIR"])
def test_other_prohibited_terms_flagged(base_maint_form, base_package, prohibited_term):
    base_maint_form.block_11_status = prohibited_term
    exceptions = TermLegalityChecker.check_form(base_maint_form, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-TERM-01-PROHIBITED" in rule_ids


def test_maintenance_release_cannot_claim_new(base_maint_form, base_package):
    # A Part 145 repair station cannot certify a part as NEW in Block 14
    base_maint_form.block_11_status = "NEW"
    exceptions = TermLegalityChecker.check_form(base_maint_form, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-TERM-02-MAINT-NEW-CONFLICT" in rule_ids
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in exceptions)


def test_production_release_cannot_claim_overhauled(base_package):
    # Production release in Block 13 cannot release as OVERHAULED
    prod_form = Form8130_3(
        document_id="DOC-PROD-OVERHAULED",
        block_1_country="USA / FAA",
        block_2_org_name_address="CFM Factory",
        block_3_form_tracking_no="FTN-PROD-01",
        block_4_org_cert_no="PC-42",
        block_7_description="BUSHING SHRD (IGV)",
        block_8_part_number="322-049-204-0",
        block_11_status="OVERHAULED",
        block_12_remarks="Remarks",
        block_13a_part_21_cert=True,
        block_13b_signature="M. Vance",
        block_13c_approval_no="PC-42",
        block_13d_name="Mark Vance",
        block_13e_date="2026-01-10",
        block_13_shaded=False,
        block_14_shaded=True,
        user_installer_responsibilities_boilerplate_present=True
    )
    exceptions = TermLegalityChecker.check_form(prod_form, base_package)
    rule_ids = [e.rule_id for e in exceptions]
    assert "R-TERM-04-PROD-MAINT-CONFLICT" in rule_ids
