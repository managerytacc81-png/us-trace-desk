"""
Test Suite: OCR Backends (Mock and Vision-LLM/PDF Fallback).
"""
import pytest
from pathlib import Path
from trace_desk.ocr.mock_backend import DeterministicMockBackend
from trace_desk.ocr.vision_backend import VisionLLMBackend
from trace_desk.models.package import BtBDocument, DocumentType
from trace_desk.models.forms import Form8130_3


def test_deterministic_mock_backend_registration():
    backend = DeterministicMockBackend()
    custom_doc = BtBDocument(
        document_id="CUSTOM-MOCK-DOC",
        doc_type=DocumentType.FORM_8130_3,
        part_number="322-049-204-0",
        serial_number="SN-MOCK-01",
        form_8130=Form8130_3(
            document_id="CUSTOM-MOCK-DOC",
            block_1_country="USA / FAA",
            block_2_org_name_address="Mock Facility",
            block_3_form_tracking_no="MOCK-001",
            block_4_org_cert_no="CRS MOCK123",
            block_7_description="BUSHING SHRD (IGV)",
            block_8_part_number="322-049-204-0",
            block_11_status="OVERHAULED",
            block_12_remarks="Mock remarks",
            block_14a_part_43_cert=True,
            block_14b_signature="Signer",
            block_14c_approval_no="CRS MOCK123",
            block_14d_name="Signer",
            block_14e_date="2026-01-01",
            block_13_shaded=True,
            user_installer_responsibilities_boilerplate_present=True
        )
    )
    backend.register("my_mock_doc.pdf", custom_doc)

    doc = backend.extract_document("/tmp/path/my_mock_doc.pdf")
    assert doc.document_id == "CUSTOM-MOCK-DOC"
    assert doc.form_8130.block_4_org_cert_no == "CRS MOCK123"


def test_deterministic_mock_backend_heuristic():
    backend = DeterministicMockBackend()
    doc_8130 = backend.extract_document("/tmp/incoming/tag_8130_scan.pdf")
    assert doc_8130.doc_type == DocumentType.FORM_8130_3
    assert doc_8130.form_8130 is not None

    doc_removal = backend.extract_document("/tmp/incoming/removal_tag_engine.pdf")
    assert doc_removal.doc_type == DocumentType.REMOVAL_TAG
    assert doc_removal.removal_tag is not None


def test_vision_backend_extract_clean_pdf_fixture():
    fixture_path = Path("/home/user/revenue-eval/submissions/us-trace-desk/fixtures/clean_8130.pdf")
    assert fixture_path.exists()

    backend = VisionLLMBackend()
    text = backend.extract_text(str(fixture_path))
    assert "8130-3" in text
    assert "322-049-204-0" in text

    doc = backend.extract_document(str(fixture_path))
    assert doc.doc_type == DocumentType.FORM_8130_3
    assert doc.form_8130 is not None
    assert doc.form_8130.block_8_part_number == "322-049-204-0"
    assert doc.form_8130.block_11_status == "OVERHAULED"
    assert doc.form_8130.user_installer_responsibilities_boilerplate_present is True


def test_vision_backend_extract_forged_pdf_fixture():
    fixture_path = Path("/home/user/revenue-eval/submissions/us-trace-desk/fixtures/forged_aog_8130.pdf")
    assert fixture_path.exists()

    backend = VisionLLMBackend()
    doc = backend.extract_document(str(fixture_path))
    assert doc.doc_type == DocumentType.FORM_8130_3
    assert doc.form_8130 is not None
    # Check that generic 'bushing' was extracted
    assert doc.form_8130.block_7_description.lower() == "bushing"
    # Boilerplate is missing in forged fixture
    assert doc.form_8130.user_installer_responsibilities_boilerplate_present is False
