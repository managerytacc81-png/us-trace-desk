"""
Abstract Base OCR Backend Interface.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
from trace_desk.models.package import BtBDocument, BtBTracePackage, DocumentType


class BaseOCRBackend(ABC):
    """Abstract OCR and Document Extraction Backend."""

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """Extracts raw text content from a PDF or image file."""
        pass

    @abstractmethod
    def extract_document(
        self,
        file_path: str,
        doc_type: Optional[DocumentType] = None
    ) -> BtBDocument:
        """Parses a single file into a structured BtBDocument."""
        pass

    def extract_package(
        self,
        file_paths: List[str],
        package_id: str,
        part_number: str,
        serial_number: str,
        description: str = "Aviation Component",
        is_life_limited: bool = False,
        life_limit_cycles: Optional[int] = None,
        life_limit_hours: Optional[float] = None
    ) -> BtBTracePackage:
        """Processes multiple files into a unified BtBTracePackage."""
        documents: List[BtBDocument] = []
        for path in file_paths:
            doc = self.extract_document(path)
            documents.append(doc)

        return BtBTracePackage(
            package_id=package_id,
            part_number=part_number,
            serial_number=serial_number,
            description=description,
            is_life_limited=is_life_limited,
            life_limit_cycles=life_limit_cycles,
            life_limit_hours=life_limit_hours,
            documents=documents
        )
