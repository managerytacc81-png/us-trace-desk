"""
Trace Audit Rules Engine Coordinator.
Executes all compliance suites, tallies scores, and generates ExceptionReport.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from trace_desk.models.exceptions import (
    AuditDisposition, AuditException, ExceptionReport, ExceptionSeverity, ExceptionCategory
)
from trace_desk.models.package import BtBTracePackage
from trace_desk.rules.block_completeness import BlockCompletenessChecker
from trace_desk.rules.sup_forgery import SupForgeryChecker
from trace_desk.rules.continuity import ContinuityChecker, parse_doc_date
from trace_desk.rules.term_legality import TermLegalityChecker


class RulesEngine:
    """
    Coordinates regulatory audit checks across all ingested documents in a package.
    """

    def __init__(self, auditor_name: str = "USM Trace Exception-Audit Engine v1.0"):
        self.auditor_name = auditor_name

    def audit(self, package: BtBTracePackage) -> ExceptionReport:
        exceptions: List[AuditException] = []

        # 1. Block Completeness Checks
        for doc in package.documents:
            if doc.form_8130:
                exceptions.extend(BlockCompletenessChecker.check_form_8130(doc.form_8130, package))

        # 2. SUP Forgery Red Flag Checks
        for doc in package.documents:
            if doc.form_8130:
                exceptions.extend(SupForgeryChecker.check_form(doc.form_8130, package))

        # 3. Block 11 Status Term Legality
        for doc in package.documents:
            if doc.form_8130:
                exceptions.extend(TermLegalityChecker.check_form(doc.form_8130, package))

        # 4. Chain of Custody & Continuity
        exceptions.extend(ContinuityChecker.check_package(package))

        # Deduplicate exceptions by (rule_id, document_id, block_ref)
        seen = set()
        deduped_exceptions: List[AuditException] = []
        for exc in exceptions:
            key = (exc.rule_id, exc.document_id, exc.block_ref)
            if key not in seen:
                seen.add(key)
                deduped_exceptions.append(exc)

        # Calculate Audit Score
        score = 100.0
        has_critical = False
        has_major = False

        severity_counts = {
            ExceptionSeverity.CRITICAL: 0,
            ExceptionSeverity.MAJOR: 0,
            ExceptionSeverity.MINOR: 0,
            ExceptionSeverity.WARNING: 0,
            ExceptionSeverity.INFO: 0
        }

        category_counts = {cat.value: 0 for cat in ExceptionCategory}

        for exc in deduped_exceptions:
            severity_counts[exc.severity] += 1
            category_counts[exc.category.value] += 1

            if exc.severity == ExceptionSeverity.CRITICAL:
                has_critical = True
                score -= 35.0
            elif exc.severity == ExceptionSeverity.MAJOR:
                has_major = True
                score -= 15.0
            elif exc.severity == ExceptionSeverity.MINOR:
                score -= 5.0
            elif exc.severity == ExceptionSeverity.WARNING:
                score -= 2.0

        score = max(0.0, min(100.0, score))

        # Determine Final Operational Disposition
        if has_critical:
            disposition = AuditDisposition.REJECT_SUP_ALERT
        elif has_major or score < 85.0:
            disposition = AuditDisposition.CONDITIONAL_PASS
        else:
            disposition = AuditDisposition.PASS

        # Calculate flight totals / remaining cycles
        current_tsn: Optional[float] = None
        current_csn: Optional[int] = None
        remaining_cycles: Optional[int] = None

        # Build chronological timeline
        chrono_docs = package.get_chronological_events()
        custody_summary: List[Dict[str, Any]] = []

        for doc in chrono_docs:
            d_date = doc.get_event_date() or "Undated"
            h, c = doc.get_hours_cycles()
            if h is not None and (current_tsn is None or h > current_tsn):
                current_tsn = h
            if c is not None and (current_csn is None or c > current_csn):
                current_csn = c

            entity = "Unknown"
            notes = doc.doc_type.value
            if doc.form_8130:
                entity = doc.form_8130.block_2_org_name_address or "Authorized Facility"
                notes = f"8130-3 ({doc.form_8130.block_11_status or 'Release'})"
            elif doc.easa_form_1:
                entity = doc.easa_form_1.organization_name_address or "EASA Facility"
                notes = f"EASA Form 1 ({doc.easa_form_1.status_work or 'Release'})"
            elif doc.removal_tag:
                entity = doc.removal_tag.removing_organization or "Airline / MRO"
                notes = f"Removal Tag (Reason: {doc.removal_tag.reason_for_removal or 'N/A'})"
            elif doc.work_order:
                entity = doc.work_order.repair_station_name or "Repair Station"
                notes = f"Work Order ({doc.work_order.work_performed or 'Shop Visit'})"
            elif doc.bill_of_sale:
                entity = f"{doc.bill_of_sale.seller} -> {doc.bill_of_sale.buyer}"
                notes = "Bill of Sale (Title Transfer)"
            elif doc.logbook:
                entity = doc.logbook.aircraft_registration or doc.logbook.engine_serial_number or "Aircraft Log"
                notes = f"Logbook ({doc.logbook.action_type})"

            custody_summary.append({
                "date": d_date,
                "document_id": doc.document_id,
                "doc_type": doc.doc_type.value,
                "entity": entity,
                "flight_hours_tsn": h,
                "flight_cycles_csn": c,
                "summary": notes
            })

        if package.is_life_limited and package.life_limit_cycles is not None:
            c_val = current_csn if current_csn is not None else 0
            remaining_cycles = max(0, package.life_limit_cycles - c_val)

        rule_summary = {
            "by_severity": {k.value: v for k, v in severity_counts.items()},
            "by_category": category_counts
        }

        now_utc = datetime.now(timezone.utc).isoformat()
        audit_id = f"AUD-{package.package_id}-{int(datetime.now(timezone.utc).timestamp())}"

        return ExceptionReport(
            audit_id=audit_id,
            package_name=package.package_id,
            timestamp=now_utc,
            auditor=self.auditor_name,
            part_number=package.part_number,
            serial_number=package.serial_number,
            part_description=package.description,
            is_life_limited=package.is_life_limited,
            life_limit_cycles=package.life_limit_cycles,
            life_limit_hours=package.life_limit_hours,
            current_tsn=current_tsn,
            current_csn=current_csn,
            remaining_cycles=remaining_cycles,
            total_documents_analyzed=len(package.documents),
            audit_score=round(score, 1),
            disposition=disposition,
            exceptions=deduped_exceptions,
            custody_chain_summary=custody_summary,
            rule_summary=rule_summary
        )
