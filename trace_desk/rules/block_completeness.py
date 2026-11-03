"""
FAA Form 8130-3 Block Completeness Rules Engine.
Compliant with FAA Order 8130.21J and AC 43-9D.
Supports printed label mapping across older form revisions.
"""
from typing import List, Dict, Any, Optional
from trace_desk.models.exceptions import (
    AuditException, ExceptionSeverity, ExceptionCategory
)
from trace_desk.models.forms import Form8130_3
from trace_desk.models.package import BtBTracePackage


# Standard label synonyms across FAA Order 8130.21 revisions (Rev G, H, J)
LABEL_MAPPINGS = {
    "block_1_country": [
        "approving competent authority", "approving country", "approving national aviation authority",
        "civil aviation authority", "block 1", "country"
    ],
    "block_2_org_name_address": [
        "organization name and address", "issuing organization", "block 2", "organization"
    ],
    "block_3_form_tracking_no": [
        "form tracking number", "tracking number", "tracking no", "block 3"
    ],
    "block_4_org_cert_no": [
        "organization certificate", "approval/authorization number", "certificate number",
        "cert no", "block 4", "approval no"
    ],
    "block_5_work_order": [
        "work order", "contract", "invoice", "block 5", "work order / contract"
    ],
    "block_6_item": [
        "item", "item number", "line item", "block 6"
    ],
    "block_7_description": [
        "description", "nomenclature", "item description", "block 7", "part description"
    ],
    "block_8_part_number": [
        "part number", "part no", "p/n", "block 8"
    ],
    "block_9_eligibility": [
        "eligibility", "block 9", "aircraft eligibility"
    ],
    "block_10_quantity": [
        "quantity", "qty", "block 10"
    ],
    "block_11_status": [
        "status/work", "status", "work", "condition", "block 11"
    ],
    "block_12_remarks": [
        "remarks", "block 12", "remarks / observations"
    ],
    "block_13_production": [
        "part 21", "certifies that the new parts", "block 13", "production release"
    ],
    "block_14_maintenance": [
        "part 43", "return to service", "14 cfr 43.9", "block 14", "maintenance release"
    ]
}


def normalize_by_labels(form: Form8130_3) -> Form8130_3:
    """
    If raw printed label mappings are provided (e.g. from older editions),
    maps them onto missing standard attributes.
    """
    if not form.raw_labels_mapping:
        return form

    raw_lower = {k.lower().strip(): v for k, v in form.raw_labels_mapping.items()}

    for target_field, synonyms in LABEL_MAPPINGS.items():
        current_val = getattr(form, target_field, None)
        if current_val is None or current_val == "" or (target_field == "block_10_quantity" and any(syn in k for k in raw_lower for syn in synonyms)):
            for syn in synonyms:
                matched_key = next((k for k in raw_lower if syn in k), None)
                if matched_key and raw_lower[matched_key]:
                    val = raw_lower[matched_key]
                    if target_field == "block_10_quantity":
                        try:
                            val = int(val)
                        except (ValueError, TypeError):
                            val = 1
                    setattr(form, target_field, val)
                    break

    return form


class BlockCompletenessChecker:
    """
    Audits FAA Form 8130-3 for mandatory block completeness
    per FAA Order 8130.21J and AC 43-9D.
    """

    @classmethod
    def check_form_8130(cls, form: Form8130_3, package: BtBTracePackage) -> List[AuditException]:
        exceptions: List[AuditException] = []
        doc_id = form.document_id

        # Normalize via label mapping in case of legacy renumbering
        form = normalize_by_labels(form)

        # 1. Block 1: Approving Competent Authority / Country
        if not form.block_1_country or not form.block_1_country.strip():
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK1-{doc_id}",
                rule_id="R-8130-BLK-01",
                rule_name="Mandatory Block 1 Approving Authority Missing",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.CRITICAL,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 1",
                finding="Block 1 (Approving Competent Authority / Country) is blank or omitted.",
                regulatory_ref="FAA Order 8130.21J para 3-5(a)",
                details=f"Document {doc_id} lacks national aviation authority identification.",
                recommendation="Form invalid for airworthiness release. Reject tag or obtain corrected OEM/CRS replacement."
            ))

        # 2. Block 2: Organization Name and Address
        if not form.block_2_org_name_address or not form.block_2_org_name_address.strip():
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK2-{doc_id}",
                rule_id="R-8130-BLK-02",
                rule_name="Mandatory Block 2 Issuing Organization Missing",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.CRITICAL,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 2",
                finding="Block 2 (Organization Name and Address) is blank or omitted.",
                regulatory_ref="FAA Order 8130.21J para 3-5(b)",
                details="Issuing entity cannot be determined from Block 2.",
                recommendation="Obtain certified duplicate from releasing facility."
            ))

        # 3. Block 3: Form Tracking Number
        if not form.block_3_form_tracking_no or not form.block_3_form_tracking_no.strip():
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK3-{doc_id}",
                rule_id="R-8130-BLK-03",
                rule_name="Mandatory Block 3 Tracking Number Missing",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.MAJOR,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 3",
                finding="Block 3 (Form Tracking Number) is missing.",
                regulatory_ref="FAA Order 8130.21J para 3-5(c)",
                details="Traceability tracking identifier absent on face of document.",
                recommendation="Request issuing repair station / manufacturer re-issue with unique tracking number."
            ))

        # 4. Block 4: Organization Certificate / Approval Number
        if not form.block_4_org_cert_no or not form.block_4_org_cert_no.strip():
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK4-{doc_id}",
                rule_id="R-8130-BLK-04",
                rule_name="Mandatory Block 4 Organization Certificate Number Missing",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.CRITICAL,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 4",
                finding="Block 4 (Organization Certificate / Approval Number) is missing.",
                regulatory_ref="FAA Order 8130.21J para 3-5(d)",
                details="Issuing entity certificate authority (e.g. CRS / PC / PMA number) is missing.",
                recommendation="Reject form. Certificate authorization is legally mandatory for release."
            ))

        # 5. Block 7: Description
        if not form.block_7_description or not form.block_7_description.strip():
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK7-{doc_id}",
                rule_id="R-8130-BLK-07",
                rule_name="Mandatory Block 7 Description Missing",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.MAJOR,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 7",
                finding="Block 7 (Description / Nomenclature) is blank.",
                regulatory_ref="FAA Order 8130.21J para 3-5(g)",
                details="Part nomenclature not stated.",
                recommendation="Verify article description against IPC / maintenance records."
            ))

        # 6. Block 8: Part Number
        if not form.block_8_part_number or not form.block_8_part_number.strip():
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK8-{doc_id}",
                rule_id="R-8130-BLK-08",
                rule_name="Mandatory Block 8 Part Number Missing",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.CRITICAL,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 8",
                finding="Block 8 (Part Number) is blank or omitted.",
                regulatory_ref="FAA Order 8130.21J para 3-5(h)",
                details="Cannot verify identity of released component without Block 8 part number.",
                recommendation="Reject tag. Essential identification data missing."
            ))

        # 7. Block 10: Quantity
        if form.block_10_quantity is None or form.block_10_quantity <= 0:
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK10-{doc_id}",
                rule_id="R-8130-BLK-10",
                rule_name="Invalid Block 10 Quantity",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.MINOR,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 10",
                finding="Block 10 (Quantity) is missing or less than 1.",
                regulatory_ref="FAA Order 8130.21J para 3-5(j)",
                details=f"Observed quantity: {form.block_10_quantity}",
                recommendation="Clarify released unit count with issuing facility."
            ))

        # 8. Block 11: Status / Work
        if not form.block_11_status or not form.block_11_status.strip():
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK11-{doc_id}",
                rule_id="R-8130-BLK-11",
                rule_name="Mandatory Block 11 Status/Work Missing",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.CRITICAL,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 11",
                finding="Block 11 (Status / Work) is blank.",
                regulatory_ref="FAA Order 8130.21J para 3-5(k)",
                details="Airworthiness condition (e.g. OVERHAULED, REPAIRED, NEW) is missing.",
                recommendation="Reject tag. Block 11 is mandatory to establish airworthiness standard."
            ))

        # 9. Block 12: Remarks
        if not form.block_12_remarks or not form.block_12_remarks.strip():
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-BLK12-{doc_id}",
                rule_id="R-8130-BLK-12",
                rule_name="Mandatory Block 12 Remarks Missing",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.MAJOR,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Block 12",
                finding="Block 12 (Remarks) is blank or omitted.",
                regulatory_ref="FAA Order 8130.21J para 3-5(l) & AC 43-9D",
                details="Block 12 must document work details, maintenance manuals used, AD compliance, or TSN/CSN.",
                recommendation="Request shop package details or amended release documentation."
            ))

        # 10. Release Block Execution: Block 13a-e vs Block 14a-e
        has_block_13 = bool(
            form.block_13a_part_21_cert or form.block_13b_signature or
            form.block_13c_approval_no or form.block_13d_name or form.block_13e_date
        )
        has_block_14 = bool(
            form.block_14a_part_43_cert or form.block_14b_signature or
            form.block_14c_approval_no or form.block_14d_name or form.block_14e_date
        )

        if not has_block_13 and not has_block_14:
            exceptions.append(AuditException(
                exception_id=f"EXP-BC-NOREL-{doc_id}",
                rule_id="R-8130-NO-RELEASE",
                rule_name="Uncertified Form - Neither Block 13 nor 14 Executed",
                category=ExceptionCategory.COMPLETENESS_8130,
                severity=ExceptionSeverity.CRITICAL,
                document_id=doc_id,
                document_type="Form 8130-3",
                block_ref="Blocks 13 & 14",
                finding="Form 8130-3 is uncertified; neither Block 13 (Production) nor Block 14 (Maintenance) is signed.",
                regulatory_ref="FAA Order 8130.21J para 3-2",
                details="Document is completely unsigned and conveys zero airworthiness approval.",
                recommendation="Document is invalid. Reject immediately."
            ))

        # Check Block 13 completeness if attempted
        if has_block_13:
            missing_13 = []
            if not form.block_13a_part_21_cert:
                missing_13.append("13a (Part 21 Certification Check)")
            if not form.block_13b_signature:
                missing_13.append("13b (Authorized Signature)")
            if not form.block_13c_approval_no:
                missing_13.append("13c (Approval/Authorization No.)")
            if not form.block_13d_name:
                missing_13.append("13d (Signer Name)")
            if not form.block_13e_date:
                missing_13.append("13e (Date)")

            if missing_13:
                exceptions.append(AuditException(
                    exception_id=f"EXP-BC-BLK13-INCOMP-{doc_id}",
                    rule_id="R-8130-BLK13-INCOMP",
                    rule_name="Incomplete Block 13 Production Release",
                    category=ExceptionCategory.COMPLETENESS_8130,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 13a-e",
                    finding=f"Incomplete Block 13 release: missing {', '.join(missing_13)}.",
                    regulatory_ref="FAA Order 8130.21J para 3-6",
                    details=f"Production release attempted but lacks required signatory fields: {missing_13}.",
                    recommendation="Obtain corrected production release from original manufacturer."
                ))

        # Check Block 14 completeness if attempted
        if has_block_14:
            missing_14 = []
            if not form.block_14a_part_43_cert:
                missing_14.append("14a (Part 43 Return to Service Certification Check)")
            if not form.block_14b_signature:
                missing_14.append("14b (Authorized Signature)")
            if not form.block_14c_approval_no:
                missing_14.append("14c (Certificate No.)")
            if not form.block_14d_name:
                missing_14.append("14d (Signer Name)")
            if not form.block_14e_date:
                missing_14.append("14e (Date)")

            if missing_14:
                exceptions.append(AuditException(
                    exception_id=f"EXP-BC-BLK14-INCOMP-{doc_id}",
                    rule_id="R-8130-BLK14-INCOMP",
                    rule_name="Incomplete Block 14 Maintenance Release",
                    category=ExceptionCategory.COMPLETENESS_8130,
                    severity=ExceptionSeverity.CRITICAL,
                    document_id=doc_id,
                    document_type="Form 8130-3",
                    block_ref="Block 14a-e",
                    finding=f"Incomplete Block 14 release: missing {', '.join(missing_14)}.",
                    regulatory_ref="FAA Order 8130.21J para 3-7",
                    details=f"Maintenance return to service lacks required signatory fields: {missing_14}.",
                    recommendation="Hold inventory. Request corrected Form 8130-3 from certificated repair station."
                ))

        return exceptions
