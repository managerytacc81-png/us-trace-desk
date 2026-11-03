"""
Test Suite: End-to-End Pipeline & CLI Verification.
"""
import pytest
from pathlib import Path
from trace_desk.pipeline import TraceAuditPipeline
from trace_desk.ocr.mock_backend import DeterministicMockBackend
from trace_desk.cli import create_demo_clean_package, create_demo_forged_package
from trace_desk.models.exceptions import AuditDisposition, ExceptionSeverity


def test_pipeline_clean_package_execution(tmp_path):
    pipeline = TraceAuditPipeline(backend=DeterministicMockBackend())
    clean_pkg = create_demo_clean_package()

    report = pipeline.audit_package(clean_pkg, output_dir=str(tmp_path))
    assert report.disposition == AuditDisposition.PASS
    assert report.audit_score == 100.0
    assert len(report.exceptions) == 0

    # Verify generated report files
    prefix = f"{clean_pkg.package_id}_EXCEPTION_REPORT"
    assert (tmp_path / f"{prefix}.json").exists()
    assert (tmp_path / f"{prefix}.md").exists()
    assert (tmp_path / f"{prefix}.pdf").exists()


def test_pipeline_forged_package_execution(tmp_path):
    pipeline = TraceAuditPipeline(backend=DeterministicMockBackend())
    forged_pkg = create_demo_forged_package()

    report = pipeline.audit_package(forged_pkg, output_dir=str(tmp_path))
    assert report.disposition == AuditDisposition.REJECT_SUP_ALERT
    assert report.audit_score <= 50.0
    assert len(report.exceptions) >= 3

    # Ensure critical severity items exist
    assert any(e.severity == ExceptionSeverity.CRITICAL for e in report.exceptions)


def test_pipeline_from_file_paths(tmp_path):
    pipeline = TraceAuditPipeline(backend=DeterministicMockBackend())
    report = pipeline.audit_files(
        file_paths=["mock_8130.pdf", "mock_removal_tag.pdf"],
        package_id="PKG-MULTI-DOC",
        part_number="322-049-204-0",
        serial_number="SN-CFM-88912",
        output_dir=str(tmp_path)
    )
    assert report.total_documents_analyzed == 2
    assert report.audit_id.startswith("AUD-PKG-MULTI-DOC")
