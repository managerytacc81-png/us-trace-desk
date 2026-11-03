"""
Chain of Custody Continuity & Life-Limited Part (LLP) Trace Rules Engine.
Complies with FAA Order 8130.21J, AC 120-84, and AC 43-9D.
Audits date monotonicity, cycle/hour accumulation, serial matching, and title chain integrity.
"""
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from trace_desk.models.exceptions import (
    AuditException, ExceptionSeverity, ExceptionCategory
)
from trace_desk.models.package import BtBTracePackage, BtBDocument


def parse_doc_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses various aviation date formats into datetime object."""
    if not date_str or not date_str.strip():
        return None
    d_clean = date_str.strip().upper()
    formats = [
        "%Y-%m-%d", "%d/%b/%Y", "%d-%b-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%d %b %Y", "%Y/%m/%d", "%d.%m.%Y", "%b %d, %Y", "%B %d, %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(d_clean, fmt)
        except ValueError:
            pass
    return None


class ContinuityChecker:
    """
    Validates end-to-end back-to-birth continuity across all ingested trace documents.
    """

    @classmethod
    def check_package(cls, package: BtBTracePackage) -> List[AuditException]:
        exceptions: List[AuditException] = []
        target_pn = package.part_number.strip().upper()
        target_sn = package.serial_number.strip().upper()

        # 1. Target Part Number & Serial Number Matching across all documents
        for doc in package.documents:
            doc_id = doc.document_id
            doc_type_name = doc.doc_type.value

            # Extract doc part number and serial number
            doc_pn = (doc.part_number or "").strip().upper()
            doc_sn = (doc.serial_number or "").strip().upper()

            if doc.form_8130:
                doc_pn = doc_pn or (doc.form_8130.block_8_part_number or "").strip().upper()
                doc_sn = doc_sn or (doc.form_8130.serial_number or "").strip().upper()
            elif doc.easa_form_1:
                doc_pn = doc_pn or (doc.easa_form_1.part_number or "").strip().upper()
                doc_sn = doc_sn or (doc.easa_form_1.serial_number or "").strip().upper()
            elif doc.logbook:
                doc_pn = doc_pn or (doc.logbook.part_number or "").strip().upper()
                doc_sn = doc_sn or (doc.logbook.serial_number or "").strip().upper()
            elif doc.removal_tag:
                doc_pn = doc_pn or (doc.removal_tag.part_number or "").strip().upper()
                doc_sn = doc_sn or (doc.removal_tag.serial_number or "").strip().upper()
            elif doc.work_order:
                doc_pn = doc_pn or (doc.work_order.part_number or "").strip().upper()
                doc_sn = doc_sn or (doc.work_order.serial_number or "").strip().upper()
            elif doc.bill_of_sale:
                doc_pn = doc_pn or (doc.bill_of_sale.part_number or "").strip().upper()
                doc_sn = doc_sn or (doc.bill_of_sale.serial_number or "").strip().upper()

            # Verify Part Number Match
            if doc_pn and doc_pn != target_pn:
                exceptions.append(AuditException(
                    exception_id=f"EXP-COC-PN-MISMATCH-{doc_id}",
                    rule_id="R-COC-01-PN-MISMATCH",
                    rule_name="Part Number Discrepancy Across Trace Package",
                    category=ExceptionCategory.DATA_DISCREPANCY,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type=doc_type_name,
                    block_ref="Part Number",
                    finding=f"Document {doc_id} cites part number '{doc_pn}' but package target is '{target_pn}'.",
                    regulatory_ref="FAA AC 120-84 para 6 / FAA Order 8130.21J",
                    details=f"Part number does not match audit dossier. Unless an authorized SB/modification "
                            f"re-identification is documented, this package cannot be traced.",
                    recommendation="Confirm whether part underwent Service Bulletin re-identification or if wrong document was inserted."
                ))

            # Verify Serial Number Match
            if doc_sn and doc_sn != target_sn:
                exceptions.append(AuditException(
                    exception_id=f"EXP-COC-SN-MISMATCH-{doc_id}",
                    rule_id="R-COC-02-SN-MISMATCH",
                    rule_name="Serial Number Discrepancy Across Trace Package",
                    category=ExceptionCategory.DATA_DISCREPANCY,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type=doc_type_name,
                    block_ref="Serial Number",
                    finding=f"Document {doc_id} cites serial number '{doc_sn}' but package target is '{target_sn}'.",
                    regulatory_ref="FAA AC 43-9D / AC 120-84 para 6",
                    details=f"Serial number divergence detected. Back-to-birth continuity is broken for serial '{target_sn}'.",
                    recommendation="REJECT. Package contains records from an unrelated serialized article."
                ))

        # 2. Chronological Ordering and Date Monotonicity
        dated_docs: List[Tuple[datetime, BtBDocument]] = []
        undated_docs: List[BtBDocument] = []

        for doc in package.documents:
            d_raw = doc.get_event_date()
            dt = parse_doc_date(d_raw)
            if dt:
                dated_docs.append((dt, doc))
            else:
                undated_docs.append(doc)

        # Flag undated critical documents
        for u_doc in undated_docs:
            exceptions.append(AuditException(
                exception_id=f"EXP-COC-UNDATED-{u_doc.document_id}",
                rule_id="R-COC-03-UNDATED-RECORD",
                rule_name="Missing Event Date on Operational Record",
                category=ExceptionCategory.CHAIN_OF_CUSTODY,
                severity=ExceptionSeverity.MAJOR,
                document_id=u_doc.document_id,
                document_type=u_doc.doc_type.value,
                block_ref="Date",
                finding=f"Document {u_doc.document_id} has no valid event date.",
                regulatory_ref="FAA AC 120-84 para 7",
                details="Trace record lacks an event date, preventing chronological sequencing.",
                recommendation="Obtain date-stamped certified original."
            ))

        # Sort chronological events
        dated_docs.sort(key=lambda x: x[0])

        # 3. LLP Flight Hours and Cycles Monotonicity (CSN / TSN Non-Decreasing)
        prev_dt: Optional[datetime] = None
        prev_doc: Optional[BtBDocument] = None
        prev_hours: Optional[float] = None
        prev_cycles: Optional[int] = None
        max_seen_cycles: int = 0
        max_seen_hours: float = 0.0

        for dt, doc in dated_docs:
            hours, cycles = doc.get_hours_cycles()

            # Also check 8130-3 remarks for parsed hours/cycles if not in doc helper
            if doc.form_8130 and (hours is None or cycles is None):
                rem = doc.form_8130.block_12_remarks or ""
                # Attempt light parsing of TSN / CSN from remarks
                # e.g. "TSN: 14200.5, CSN: 6800"
                import re
                tsn_match = re.search(r"TSN[:\s=]+([0-9,.]+)", rem, re.IGNORECASE)
                csn_match = re.search(r"CSN[:\s=]+([0-9,]+)", rem, re.IGNORECASE)
                if tsn_match and hours is None:
                    try:
                        hours = float(tsn_match.group(1).replace(",", ""))
                    except ValueError:
                        pass
                if csn_match and cycles is None:
                    try:
                        cycles = int(csn_match.group(1).replace(",", ""))
                    except ValueError:
                        pass

            if cycles is not None:
                if cycles > max_seen_cycles:
                    max_seen_cycles = cycles
                if prev_cycles is not None and cycles < prev_cycles:
                    exceptions.append(AuditException(
                        exception_id=f"EXP-COC-CYCLE-REGRESS-{doc.document_id}",
                        rule_id="R-COC-04-CYCLE-DISCONTINUITY",
                        rule_name="Negative Flight Cycle Accumulation (CSN Regression)",
                        category=ExceptionCategory.CHAIN_OF_CUSTODY,
                        severity=ExceptionSeverity.CRITICAL,
                        document_id=doc.document_id,
                        document_type=doc.doc_type.value,
                        block_ref="CSN / Flight Cycles",
                        finding=f"Cycles Since New (CSN) dropped from {prev_cycles} (in {prev_doc.document_id} on {prev_dt.strftime('%Y-%m-%d')}) "
                                f"to {cycles} (in {doc.document_id} on {dt.strftime('%Y-%m-%d')}).",
                        regulatory_ref="14 CFR 43.10 / FAA AC 120-84 para 6(b)",
                        details=f"Physically impossible cycle reduction of {prev_cycles - cycles} cycles detected. "
                                f"Indicates record falsification, odometer rollback, or mixed trace documents.",
                        recommendation="QUARANTINE LLP ARTICLE. Reject package. An LLP with discontinuous cycles cannot be installed on any civil aircraft."
                    ))
                prev_cycles = cycles

            if hours is not None:
                if hours > max_seen_hours:
                    max_seen_hours = hours
                if prev_hours is not None and hours < prev_hours:
                    exceptions.append(AuditException(
                        exception_id=f"EXP-COC-HOUR-REGRESS-{doc.document_id}",
                        rule_id="R-COC-05-HOUR-DISCONTINUITY",
                        rule_name="Negative Flight Hour Accumulation (TSN Regression)",
                        category=ExceptionCategory.CHAIN_OF_CUSTODY,
                        severity=ExceptionSeverity.CRITICAL,
                        document_id=doc.document_id,
                        document_type=doc.doc_type.value,
                        block_ref="TSN / Flight Hours",
                        finding=f"Time Since New (TSN) decreased from {prev_hours:.1f} hrs (in {prev_doc.document_id} on {prev_dt.strftime('%Y-%m-%d')}) "
                                f"to {hours:.1f} hrs (in {doc.document_id} on {dt.strftime('%Y-%m-%d')}).",
                        regulatory_ref="14 CFR 43.10 / FAA AC 120-84 para 6(b)",
                        details=f"Hours regressed by {prev_hours - hours:.1f} hrs across chronological sequence.",
                        recommendation="Hold inventory. Reconcile with airline master engineering records."
                    ))
                prev_hours = hours

            prev_dt = dt
            prev_doc = doc

        # 4. Mandatory Life Limit Exceeded Check
        if package.is_life_limited and package.life_limit_cycles is not None:
            if max_seen_cycles >= package.life_limit_cycles:
                exceptions.append(AuditException(
                    exception_id=f"EXP-COC-LIFE-LIMIT-EXCEEDED-{package.package_id}",
                    rule_id="R-COC-06-LIFE-LIMIT-EXCEEDED",
                    rule_name="Mandatory LLP Cycle Life Limit Exceeded",
                    category=ExceptionCategory.CHAIN_OF_CUSTODY,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=package.package_id,
                    document_type="LLP Summary",
                    block_ref="Life Limit",
                    finding=f"Part accumulated {max_seen_cycles} cycles, exceeding mandatory life limit of {package.life_limit_cycles} cycles.",
                    regulatory_ref="14 CFR 43.10 / FAA Order 8130.21J para 3-5",
                    details=f"Part is time-expired / life-expired. Over-limit by {max_seen_cycles - package.life_limit_cycles} cycles.",
                    recommendation="SCRAP MANDATORY. Part must be permanently mutilated or decommissioned per 14 CFR 43.10."
                ))

        # 5. Ownership Chain & Bill of Sale Continuity
        bills_of_sale = package.get_ownership_transfers()
        if len(bills_of_sale) > 1:
            for idx in range(len(bills_of_sale) - 1):
                bos_curr = bills_of_sale[idx]
                bos_next = bills_of_sale[idx + 1]
                buyer = (bos_curr.buyer or "").strip().lower()
                seller_next = (bos_next.seller or "").strip().lower()

                if buyer and seller_next and buyer != seller_next:
                    exceptions.append(AuditException(
                        exception_id=f"EXP-COC-OWNERSHIP-GAP-{bos_next.document_id}",
                        rule_id="R-COC-07-OWNERSHIP-GAP",
                        rule_name="Broken Chain of Title / Ownership Gap",
                        category=ExceptionCategory.CHAIN_OF_CUSTODY,
                        severity=ExceptionSeverity.MAJOR,
                        document_id=bos_next.document_id,
                        document_type="Bill of Sale",
                        block_ref="Seller / Buyer",
                        finding=f"Ownership gap detected: Document {bos_curr.document_id} transferred to '{bos_curr.buyer}', "
                                f"but subsequent Document {bos_next.document_id} was sold by '{bos_next.seller}'.",
                        regulatory_ref="ASA-100 Standard / AC 120-84 para 5",
                        details="Missing bill of sale or transfer affidavit between intermediary entities.",
                        recommendation="Obtain bridging bill of sale or certified chain-of-title affidavit."
                    ))

        # Check Non-Incident Statements on Bills of Sale
        for bos in bills_of_sale:
            if not bos.has_non_incident_statement:
                exceptions.append(AuditException(
                    exception_id=f"EXP-COC-NO-NIS-{bos.document_id}",
                    rule_id="R-COC-08-NO-INCIDENT-STATEMENT",
                    rule_name="Missing Non-Incident / Non-Accident Statement (NIS)",
                    category=ExceptionCategory.CHAIN_OF_CUSTODY,
                    severity=ExceptionSeverity.MAJOR,
                    document_id=bos.document_id,
                    document_type="Bill of Sale",
                    block_ref="Non-Incident Statement",
                    finding=f"Bill of Sale {bos.document_id} lacks certified Non-Incident / Non-Accident Statement (NIS).",
                    regulatory_ref="FAA AC 120-84 para 8 / ASA-100 Standard",
                    details="Commercial transfer affidavit does not certify part was not subjected to extreme stress, heat, fire, or accident.",
                    recommendation="Request seller execute a standard ATA/ASA Non-Incident Statement."
                ))

        return exceptions
