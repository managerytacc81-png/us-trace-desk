"""
Test Suite: Report Generator (JSON, Markdown, and 2-page PDF).
"""
import pytest
import json
from pathlib import Path
from trace_desk.models.exceptions import (
    ExceptionReport, AuditDisposition, AuditException, ExceptionSeverity, ExceptionCategory
)
from trace_desk.report.generator import ReportGenerator


@pytest.fixture
def sample_report() -> ExceptionReport:
    return ExceptionReport(
        audit_id="AUD-SAMPLE-001",
        package_name="SAMPLE-CFM56-PACKAGE",
        timestamp="2026-11-03T18:00:00Z",
        part_number="322-049-204-0",
        serial_number="SN-CFM-88912",
        part_description="BUSHING SHRD (IGV)",
        is_life_limited=True,
        life_limit_cycles=20000,
        life_limit_hours=50000.0,
        current_tsn=14200.0,
        current_csn=6100,
        remaining_cycles=13900,
        total_documents_analyzed=3,
        audit_score=65.0,
        disposition=AuditDisposition.REJECT_SUP_ALERT,
        exceptions=[
            AuditException(
                exception_id="EXP-SUP-01",
                rule_id="R-SUP-01-BOILERPLATE",
                rule_name="Missing Mandatory Boilerplate",
                category=ExceptionCategory.SUP_FORGERY_RED_FLAG,
                severity=ExceptionSeverity.CRITICAL,
                document_id="DOC-8130",
                document_type="Form 8130-3",
                block_ref="Boilerplate",
                finding="Mandatory installer disclaimer missing.",
                regulatory_ref="FAA Order 8130.21J",
                details="Unapproved template detected.",
                recommendation="Quarantine article immediately."
            )
        ],
        custody_chain_summary=[
            {
                "date": "2026-01-10",
                "document_id": "DOC-TAG",
                "doc_type": "REMOVAL_TAG",
                "entity": "United Airlines",
                "flight_hours_tsn": 14200.0,
                "flight_cycles_csn": 6100,
                "summary": "Teardown removal"
            }
        ],
        rule_summary={"by_severity": {"CRITICAL": 1}, "by_category": {"SUP_FORGERY_RED_FLAG": 1}}
    )


def test_json_generation_and_loading(sample_report, tmp_path):
    json_path = tmp_path / "report.json"
    ReportGenerator.save_json(sample_report, str(json_path))
    assert json_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["audit_id"] == "AUD-SAMPLE-001"
    assert data["disposition"] == "REJECT_SUP_ALERT"
    assert len(data["exceptions"]) == 1


def test_markdown_generation(sample_report, tmp_path):
    md_str = ReportGenerator.to_markdown(sample_report)
    assert "# USM Back-to-Birth Trace Exception Report" in md_str
    assert "322-049-204-0" in md_str
    assert "REJECT - SUP ALERT" in md_str
    assert "EXP-SUP-01" in md_str


def test_pdf_generation_2_page(sample_report, tmp_path):
    pdf_path = tmp_path / "report.pdf"
    res_path = ReportGenerator.to_pdf(sample_report, str(pdf_path))
    assert Path(res_path).exists()
    assert Path(res_path).stat().st_size > 1000

    # Verify PDF has exactly 2 pages with pypdf
    import pypdf
    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 2
