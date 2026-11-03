"""
Suspected Unapproved Parts (SUP) & Forgery Red-Flag Rules Engine.
Derived from FAA Unapproved Parts Notice (AOG Technics case),
EASA SIB 2023-09, and FAA Order 8130.21J anti-forgery mandates.
"""
import re
from typing import List, Dict, Tuple
from trace_desk.models.exceptions import (
    AuditException, ExceptionSeverity, ExceptionCategory
)
from trace_desk.models.forms import Form8130_3
from trace_desk.models.package import BtBTracePackage


# Canonical OEM IPC Nomenclature Dictionary
# Maps known part numbers or part families to official IPC catalog nomenclature
# Used to catch colloquial/generic counterfeiting descriptions (e.g. 'bushing' vs 'bushing shrd (IGV)')
OEM_IPC_DICTIONARY: Dict[str, Dict[str, str]] = {
    "322-049-204-0": {
        "official_ipc": "BUSHING SHRD (IGV)",
        "generic_trap": ["bushing", "sleeve", "plain bushing"],
        "oem": "CFM International"
    },
    "317-640-101-0": {
        "official_ipc": "BUSHING, SHROUD INNER",
        "generic_trap": ["bushing", "inner bushing"],
        "oem": "CFM International"
    },
    "335-014-501-0": {
        "official_ipc": "BLADE, ROTOR, HPT STAGE 1",
        "generic_trap": ["blade", "turbine blade", "hpt blade"],
        "oem": "CFM International"
    },
    "1B8462": {
        "official_ipc": "VANE, STATOR, COMPRESSOR STAGE 4",
        "generic_trap": ["vane", "stator", "air vane"],
        "oem": "Pratt & Whitney"
    },
    "9356M32P01": {
        "official_ipc": "SEAL, LABYRINTH, INTERSTAGE",
        "generic_trap": ["seal", "ring seal", "gasket"],
        "oem": "GE Aviation"
    },
    "FK28405": {
        "official_ipc": "BEARING, BALL, THRUST DUPLEX",
        "generic_trap": ["bearing", "ball bearing"],
        "oem": "Rolls-Royce"
    }
}

GENERIC_SUSPECT_WORDS = {
    "bushing": "BUSHING SHRD (IGV) or official IPC shroud nomenclature",
    "blade": "BLADE, ROTOR / FAN with stage specification per IPC",
    "vane": "VANE, STATOR with stage specification per IPC",
    "seal": "SEAL, LABYRINTH / HONEYCOMB per IPC specification",
    "bearing": "BEARING, BALL / ROLLER DUPLEX per IPC specification"
}


def normalize_cert_number(cert: str) -> str:
    """Normalizes FAA certificate numbers for comparison (removes whitespace, dashes, uppercase)."""
    if not cert:
        return ""
    return re.sub(r"[^A-Z0-9]", "", cert.upper())


class SupForgeryChecker:
    """
    Evaluates Form 8130-3 against post-AOG Technics SUP forgery indicators.
    """

    @classmethod
    def check_form(cls, form: Form8130_3, package: BtBTracePackage) -> List[AuditException]:
        exceptions: List[AuditException] = []
        doc_id = form.document_id

        # 1. Missing user/installer responsibilities boilerplate
        # Standard FAA Order 8130.21 mandate: face or reverse MUST contain installer responsibility disclaimer.
        if not form.user_installer_responsibilities_boilerplate_present:
            exceptions.append(AuditException(
                exception_id=f"EXP-SUP-BLRPLATE-{doc_id}",
                rule_id="R-SUP-01-BOILERPLATE",
                rule_name="Missing Mandatory Installer Responsibility Boilerplate",
                category=ExceptionCategory.SUP_FORGERY_RED_FLAG,
                severity=ExceptionSeverity.CRITICAL,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Boilerplate Notice",
                finding="Document lacks mandatory installer/user responsibility disclaimer on face or reverse.",
                regulatory_ref="FAA Order 8130.21J para 3-3 & Appendix A / FAA SUP Notice (AOG Technics)",
                details="AOG Technics forged release forms systematically omitted or truncated the mandatory "
                        "installer responsibility legal notice. Unapproved template detected.",
                recommendation="QUARANTINE PART IMMEDIATELY. Suspected Unapproved Part (SUP) alert; "
                               "verify airworthiness tag directly with issuing CRS or FAA FSDO."
            ))

        # 2. Opposing release box not shaded/grayed out
        # In authentic forms, when new parts are released (Block 13), Block 14 must be shaded/grayed.
        # When maintenance is released (Block 14), Block 13 must be shaded/grayed.
        has_block_13 = bool(form.block_13a_part_21_cert or form.block_13b_signature or form.block_13c_approval_no)
        has_block_14 = bool(form.block_14a_part_43_cert or form.block_14b_signature or form.block_14c_approval_no)

        if has_block_13 and not has_block_14:
            if not form.block_14_shaded:
                exceptions.append(AuditException(
                    exception_id=f"EXP-SUP-BLK14-NOTSHADED-{doc_id}",
                    rule_id="R-SUP-02-SHADING",
                    rule_name="Opposing Release Box Block 14 Not Shaded for New Part",
                    category=ExceptionCategory.SUP_FORGERY_RED_FLAG,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 14",
                    finding="Block 14 is not shaded/grayed out despite new part release executed in Block 13.",
                    regulatory_ref="FAA Order 8130.21J para 3-6(g) / FAA SUP Advisory",
                    details="Failure to shade unused release block violates FAA formatting and matches known "
                            "fraudulent desktop-publishing templates used in AOG Technics distribution.",
                    recommendation="Hold delivery. Contact issuing production certificate holder to confirm authentic release."
                ))

        if has_block_14 and not has_block_13:
            if not form.block_13_shaded:
                exceptions.append(AuditException(
                    exception_id=f"EXP-SUP-BLK13-NOTSHADED-{doc_id}",
                    rule_id="R-SUP-02-SHADING",
                    rule_name="Opposing Release Box Block 13 Not Shaded for Maintenance Release",
                    category=ExceptionCategory.SUP_FORGERY_RED_FLAG,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 13",
                    finding="Block 13 is not shaded/grayed out despite maintenance release executed in Block 14.",
                    regulatory_ref="FAA Order 8130.21J para 3-7(f) / FAA SUP Advisory",
                    details="Failure to shade unused Block 13 allows fraudulent post-release endorsement.",
                    recommendation="Hold delivery. Require issuing repair station to provide properly formatted release."
                ))

        # 3. OEM Terminology Mismatch (AOG Technics Hallmark)
        part_no = (form.block_8_part_number or "").strip()
        desc = (form.block_7_description or "").strip().lower()

        # Check exact known part number IPC dictionary
        if part_no in OEM_IPC_DICTIONARY:
            spec = OEM_IPC_DICTIONARY[part_no]
            official_ipc = spec["official_ipc"].lower()
            generic_traps = [g.lower() for g in spec["generic_trap"]]
            if desc in generic_traps or desc != official_ipc:
                exceptions.append(AuditException(
                    exception_id=f"EXP-SUP-NOMENCLATURE-{doc_id}",
                    rule_id="R-SUP-03-NOMENCLATURE",
                    rule_name="OEM Nomenclature Mismatch - Generic AOG Technics Red Flag",
                    category=ExceptionCategory.SUP_FORGERY_RED_FLAG,
                    severity=ExceptionSeverity.MAJOR,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 7",
                    finding=f"Block 7 description '{form.block_7_description}' does not match official "
                            f"{spec['oem']} IPC nomenclature '{spec['official_ipc']}'.",
                    regulatory_ref="FAA SUP Notice 2023 / CFM International Advisory Notice",
                    details=f"Part number {part_no} corresponds to official OEM nomenclature '{spec['official_ipc']}'. "
                            f"Generic colloquial term '{form.block_7_description}' matches forged tag profile.",
                    recommendation="Quarantine article. Cross-examine illustrated parts catalog and demand OEM trace."
                ))
        else:
            # Check for overly generic terms without modifier when part of critical engine/airframe assemblies
            for generic_term, expected_ctx in GENERIC_SUSPECT_WORDS.items():
                if desc == generic_term:
                    exceptions.append(AuditException(
                        exception_id=f"EXP-SUP-GENERIC-TERM-{doc_id}",
                        rule_id="R-SUP-03-NOMENCLATURE-GENERIC",
                        rule_name="Suspiciously Generic Part Nomenclature",
                        category=ExceptionCategory.SUP_FORGERY_RED_FLAG,
                        severity=ExceptionSeverity.WARNING,
                        document_id=doc_id,
                        document_type="Form 8130-3",
                        block_ref="Block 7",
                        finding=f"Block 7 uses single bare generic term '{form.block_7_description}'.",
                        regulatory_ref="FAA Order 8130.21J para 3-5(g)",
                        details=f"OEM engine catalogs specify precise compound nomenclature (e.g. {expected_ctx}).",
                        recommendation="Review IPC exploded diagram to verify full technical nomenclature."
                    ))

        # 4. Block 4 signer vs Block 13/14 certificate-number mismatch
        block_4_cert = normalize_cert_number(form.block_4_org_cert_no or "")

        # For maintenance release (Block 14): Block 14c Certificate No. must match Block 4
        if has_block_14 and form.block_14c_approval_no:
            block_14_cert = normalize_cert_number(form.block_14c_approval_no)
            if block_4_cert and block_14_cert and block_4_cert != block_14_cert:
                exceptions.append(AuditException(
                    exception_id=f"EXP-SUP-CERT-MISMATCH-14-{doc_id}",
                    rule_id="R-SUP-04-CERT-MISMATCH",
                    rule_name="Certificate Number Mismatch: Block 4 vs Block 14c",
                    category=ExceptionCategory.SUP_FORGERY_RED_FLAG,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 4 & Block 14c",
                    finding=f"Issuing organization certificate in Block 4 ('{form.block_4_org_cert_no}') "
                            f"does not match Block 14c certificate ('{form.block_14c_approval_no}').",
                    regulatory_ref="FAA Order 8130.21J para 3-7(d) / AOG Technics SUP Precedent",
                    details=f"In maintenance releases, Block 14c MUST record the certificate number of the "
                            f"organization named in Block 2 and Block 4. Mismatch indicates unauthorized or fraudulent signature.",
                    recommendation="QUARANTINE. High probability of fraudulent airworthiness approval. File FAA Form 8120-11 SUP report."
                ))

        # For production release (Block 13): Block 13c Approval No. must match or relate to Block 4
        if has_block_13 and form.block_13c_approval_no:
            block_13_cert = normalize_cert_number(form.block_13c_approval_no)
            if block_4_cert and block_13_cert and block_4_cert != block_13_cert:
                # If neither is a prefix or subset of the other (e.g. DAR prefix)
                if block_4_cert not in block_13_cert and block_13_cert not in block_4_cert:
                    exceptions.append(AuditException(
                        exception_id=f"EXP-SUP-CERT-MISMATCH-13-{doc_id}",
                        rule_id="R-SUP-04-CERT-MISMATCH",
                        rule_name="Certificate Number Mismatch: Block 4 vs Block 13c",
                        category=ExceptionCategory.SUP_FORGERY_RED_FLAG,
                        severity=ExceptionSeverity.MAJOR,
                        document_id=doc_id,
                        document_type="Form 8130-3",
                        block_ref="Block 4 & Block 13c",
                        finding=f"Production approval number in Block 4 ('{form.block_4_org_cert_no}') "
                                f"disagrees with Block 13c approval ('{form.block_13c_approval_no}').",
                        regulatory_ref="FAA Order 8130.21J para 3-6(d)",
                        details=f"Block 13c approval must be issued under the authority of the production holder in Block 4.",
                        recommendation="Verify DMIR / DAR delegation letter from the production certificate holder."
                    ))

        return exceptions
