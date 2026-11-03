"""
Block 11 Status/Work Term Legality Rules Engine (Post-2025 FAA/EASA Split).
Complies with FAA Order 8130.21J para 3-5(k) & para 3-6/3-7, AC 43-9D, and EASA Bilateral Guidance.
"""
from typing import List, Set
from trace_desk.models.exceptions import (
    AuditException, ExceptionSeverity, ExceptionCategory
)
from trace_desk.models.forms import Form8130_3
from trace_desk.models.package import BtBTracePackage

# Authorized terms for Maintenance Release (Block 14)
LEGAL_MAINTENANCE_TERMS: Set[str] = {
    "OVERHAULED",
    "REPAIRED",
    "INSPECTED",
    "TESTED",
    "MODIFIED",
    "INSPECTED/TESTED"
}

# Authorized terms for Production Release (Block 13)
LEGAL_PRODUCTION_TERMS: Set[str] = {
    "NEW",
    "PROTOTYPE"
}

# Strictly prohibited terms in Block 11 per Order 8130.21J
PROHIBITED_TERMS: Set[str] = {
    "SERVICEABLE",       # Prohibited on Form 8130-3 Block 11; frequent yellow-tag confusion
    "AS REMOVED",        # Prohibited
    "AR",                # Prohibited
    "REBUILT",           # Restricted to original manufacturer under 14 CFR 43.3; repair stations cannot use
    "CHECKED",           # Deprecated / illegal; must be INSPECTED or TESTED
    "OVERHAUL",          # Must use past participle OVERHAULED
    "REPAIR",            # Must use past participle REPAIRED
    "CALIBRATED",        # Non-conforming release term
    "STORAGE",           # Non-conforming release term
    "CLEANED",           # Non-conforming release term
    "UNKNOWN",           # Prohibited
    "SCRAP"              # Prohibited on airworthiness release
}


class TermLegalityChecker:
    """
    Enforces post-2025 legal vocabulary for Form 8130-3 Block 11 (Status/Work).
    """

    @classmethod
    def check_form(cls, form: Form8130_3, package: BtBTracePackage) -> List[AuditException]:
        exceptions: List[AuditException] = []
        doc_id = form.document_id
        raw_status = (form.block_11_status or "").strip().upper()

        if not raw_status:
            # Block completeness handles empty; skip here to avoid duplicate
            return exceptions

        # Determine release channel
        has_block_13 = bool(form.block_13a_part_21_cert or form.block_13b_signature or form.block_13c_approval_no)
        has_block_14 = bool(form.block_14a_part_43_cert or form.block_14b_signature or form.block_14c_approval_no)

        # 1. Check for explicitly prohibited / illegal terms
        if raw_status in PROHIBITED_TERMS:
            # Serviceable is especially pervasive among sloppy brokers
            if raw_status == "SERVICEABLE":
                finding = "Block 11 cites 'SERVICEABLE', which is strictly prohibited on FAA Form 8130-3."
                details = ("FAA Order 8130.21J para 3-5(k) explicitly forbids the generic term 'SERVICEABLE' in Block 11. "
                           "The releasing facility must state the exact work accomplished (OVERHAULED, REPAIRED, INSPECTED, or TESTED). "
                           "Using 'SERVICEABLE' is a common clerical error from warehouse internal tags that invalidates the 8130-3.")
                recommendation = "Reject tag. Require repair station to reissue Form 8130-3 with specific maintenance term (e.g. INSPECTED/TESTED or OVERHAULED)."
            elif raw_status in ("AS REMOVED", "AR"):
                finding = f"Block 11 cites '{raw_status}'. As-removed articles cannot receive an Airworthiness Approval Tag."
                details = "FAA Form 8130-3 cannot be issued for parts in 'As-Removed' status under any circumstance."
                recommendation="REJECT. Tag is legally void."
            elif raw_status == "REBUILT":
                finding = "Block 11 cites 'REBUILT', which is restricted exclusively to original manufacturers."
                details = "Under 14 CFR 43.3 and Order 8130.21J, certificated repair stations cannot release articles as 'REBUILT'."
                recommendation = "Hold inventory. Inquire whether issuing facility is the OEM production certificate holder."
            else:
                finding = f"Block 11 contains prohibited status term '{raw_status}'."
                details = f"Term '{raw_status}' does not comply with authorized 8130.21J nomenclature."
                recommendation = f"Return form for correction to authorized standard terms."

            exceptions.append(AuditException(
                exception_id=f"EXP-TERM-PROHIBITED-{doc_id}",
                rule_id="R-TERM-01-PROHIBITED",
                rule_name="Prohibited Block 11 Status/Work Term",
                category=ExceptionCategory.STATUS_TERM_LEGALITY,
                severity=ExceptionSeverity.CRITICAL,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 11",
                finding=finding,
                regulatory_ref="FAA Order 8130.21J para 3-5(k) & AC 43-9D",
                details=details,
                recommendation=recommendation
            ))
            return exceptions

        # 2. Check Maintenance Release (Block 14) Term Validity
        if has_block_14 and not has_block_13:
            # Part 43 Maintenance Release
            if raw_status == "NEW":
                exceptions.append(AuditException(
                    exception_id=f"EXP-TERM-MAINT-NEW-{doc_id}",
                    rule_id="R-TERM-02-MAINT-NEW-CONFLICT",
                    rule_name="Illegal Maintenance Release for 'NEW' Part",
                    category=ExceptionCategory.STATUS_TERM_LEGALITY,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 11 & Block 14",
                    finding="Block 11 claims status 'NEW', but release was executed in Block 14 (Part 43 Maintenance).",
                    regulatory_ref="FAA Order 8130.21J para 3-6 / para 3-7",
                    details="A Part 145 repair station cannot certify an article as 'NEW' in Block 14. "
                            "New articles must be released by a Part 21 Production Approval Holder under Block 13.",
                    recommendation="QUARANTINE. Suspected fraudulent maintenance tag masquerading as factory-new."
                ))
            elif raw_status not in LEGAL_MAINTENANCE_TERMS:
                exceptions.append(AuditException(
                    exception_id=f"EXP-TERM-MAINT-INVALID-{doc_id}",
                    rule_id="R-TERM-03-INVALID-MAINT-TERM",
                    rule_name="Non-Conforming Maintenance Status Term",
                    category=ExceptionCategory.STATUS_TERM_LEGALITY,
                    severity=ExceptionSeverity.MAJOR,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 11",
                    finding=f"Block 11 status '{raw_status}' is not an authorized Part 43 return-to-service term.",
                    regulatory_ref="FAA Order 8130.21J para 3-5(k)",
                    details=f"Authorized terms are: {', '.join(sorted(LEGAL_MAINTENANCE_TERMS))}.",
                    recommendation="Request issuing repair station reissue tag with conforming term."
                ))

        # 3. Check Production Release (Block 13) Term Validity
        if has_block_13 and not has_block_14:
            # Part 21 Production Release
            if raw_status in ("OVERHAULED", "REPAIRED", "MODIFIED"):
                exceptions.append(AuditException(
                    exception_id=f"EXP-TERM-PROD-MAINT-CONFLICT-{doc_id}",
                    rule_id="R-TERM-04-PROD-MAINT-CONFLICT",
                    rule_name="Maintenance Term in Production Release Block 13",
                    category=ExceptionCategory.STATUS_TERM_LEGALITY,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 11 & Block 13",
                    finding=f"Block 11 cites maintenance term '{raw_status}', but release was executed in Block 13 (Production).",
                    regulatory_ref="FAA Order 8130.21J para 3-6",
                    details="Block 13 is restricted to new products/articles conforming to approved type design. "
                            "Maintenance return-to-service must be executed under Block 14.",
                    recommendation="Reject release. Contact supplier for proper Part 43 or Part 21 documentation."
                ))
            elif raw_status not in LEGAL_PRODUCTION_TERMS:
                exceptions.append(AuditException(
                    exception_id=f"EXP-TERM-PROD-INVALID-{doc_id}",
                    rule_id="R-TERM-05-INVALID-PROD-TERM",
                    rule_name="Non-Conforming Production Status Term",
                    category=ExceptionCategory.STATUS_TERM_LEGALITY,
                    severity=ExceptionSeverity.MAJOR,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 11",
                    finding=f"Block 11 status '{raw_status}' is not an authorized Part 21 production term.",
                    regulatory_ref="FAA Order 8130.21J para 3-5(k)",
                    details=f"Authorized production terms are: {', '.join(sorted(LEGAL_PRODUCTION_TERMS))}.",
                    recommendation="Request production holder reissue conforming airworthiness release."
                ))

        return exceptions
