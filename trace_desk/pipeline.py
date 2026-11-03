"""
End-to-End BtB Trace Audit Pipeline.
Coordinates Document Ingestion -> Rules Engine -> Exception Report Generation.
"""
import os
from pathlib import Path
from typing import List, Optional, Union
from trace_desk.models.package import BtBTracePackage, BtBDocument
from trace_desk.models.exceptions import ExceptionReport
from trace_desk.rules.engine import RulesEngine
from trace_desk.ocr.base import BaseOCRBackend
from trace_desk.ocr.mock_backend import DeterministicMockBackend
from trace_desk.ocr.vision_backend import VisionLLMBackend
from trace_desk.report.generator import ReportGenerator


class TraceAuditPipeline:
    """
    Orchestrates the entire BtB trace exception audit from scanned files to final report.
    """

    def __init__(
        self,
        backend: Optional[BaseOCRBackend] = None,
        auditor_name: str = "USM Trace Exception-Audit Desk v1.0"
    ):
        self.backend = backend or VisionLLMBackend()
        self.engine = RulesEngine(auditor_name=auditor_name)

    def audit_package(
        self,
        package: BtBTracePackage,
        output_dir: Optional[str] = None,
        generate_pdf: bool = True
    ) -> ExceptionReport:
        """Runs compliance audit on an instantiated BtBTracePackage and optionally saves reports."""
        report = self.engine.audit(package)

        if output_dir:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)

            prefix = f"{package.package_id}_EXCEPTION_REPORT"
            json_path = out_p / f"{prefix}.json"
            md_path = out_p / f"{prefix}.md"
            pdf_path = out_p / f"{prefix}.pdf"

            ReportGenerator.save_json(report, str(json_path))
            ReportGenerator.save_markdown(report, str(md_path))
            if generate_pdf:
                try:
                    ReportGenerator.to_pdf(report, str(pdf_path))
                except Exception as e:
                    print(f"Warning: PDF generation failed: {e}")

        return report

    def audit_files(
        self,
        file_paths: List[str],
        package_id: str,
        part_number: str,
        serial_number: str,
        description: str = "Aviation Article",
        is_life_limited: bool = False,
        life_limit_cycles: Optional[int] = None,
        life_limit_hours: Optional[float] = None,
        output_dir: Optional[str] = None,
        generate_pdf: bool = True
    ) -> ExceptionReport:
        """Ingests files via OCR backend and audits the resulting trace package."""
        package = self.backend.extract_package(
            file_paths=file_paths,
            package_id=package_id,
            part_number=part_number,
            serial_number=serial_number,
            description=description,
            is_life_limited=is_life_limited,
            life_limit_cycles=life_limit_cycles,
            life_limit_hours=life_limit_hours
        )
        return self.audit_package(package, output_dir=output_dir, generate_pdf=generate_pdf)
