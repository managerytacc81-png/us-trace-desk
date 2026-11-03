"""
USM Trace Exception-Audit Desk CLI.
"""
import sys
import json
import argparse
from pathlib import Path
from trace_desk.pipeline import TraceAuditPipeline
from trace_desk.ocr.mock_backend import DeterministicMockBackend
from trace_desk.models.package import BtBTracePackage, BtBDocument, DocumentType
from trace_desk.models.forms import (
    Form8130_3, RemovalTag, WorkOrder, BillOfSale
)


def create_demo_clean_package() -> BtBTracePackage:
    """Returns a 100% compliant clean back-to-birth CFM56 LLP package."""
    return BtBTracePackage(
        package_id="DEMO-CLEAN-CFM56",
        part_number="322-049-204-0",
        serial_number="SN-CFM-99100",
        description="BUSHING SHRD (IGV)",
        is_life_limited=True,
        life_limit_cycles=20000,
        life_limit_hours=50000.0,
        documents=[
            BtBDocument(
                document_id="DOC-01-REMOVAL-TAG",
                doc_type=DocumentType.REMOVAL_TAG,
                extracted_date="2026-01-15",
                part_number="322-049-204-0",
                serial_number="SN-CFM-99100",
                removal_tag=RemovalTag(
                    document_id="DOC-01-REMOVAL-TAG",
                    tag_number="TAG-UAL-8812",
                    date="2026-01-15",
                    removing_organization="United Airlines Maintenance SFO",
                    aircraft_registration="N14206",
                    engine_serial_number="ESN-774012",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-99100",
                    reason_for_removal="Engine scheduled teardown",
                    part_hours_tsn=14200.0,
                    part_cycles_csn=6100,
                    inspector_name="M. Davis",
                    inspector_certificate_no="A&P 3288192"
                )
            ),
            BtBDocument(
                document_id="DOC-02-BOS-AIRLINE",
                doc_type=DocumentType.BILL_OF_SALE,
                extracted_date="2026-02-01",
                part_number="322-049-204-0",
                serial_number="SN-CFM-99100",
                bill_of_sale=BillOfSale(
                    document_id="DOC-02-BOS-AIRLINE",
                    document_no="BOS-UAL-2026-90",
                    date="2026-02-01",
                    seller="United Airlines Asset Management",
                    buyer="AeroCore Material LLC",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-99100",
                    has_non_incident_statement=True,
                    trace_affidavit_present=True
                )
            ),
            BtBDocument(
                document_id="DOC-03-WORK-ORDER",
                doc_type=DocumentType.WORK_ORDER,
                extracted_date="2026-02-20",
                part_number="322-049-204-0",
                serial_number="SN-CFM-99100",
                work_order=WorkOrder(
                    document_id="DOC-03-WORK-ORDER",
                    work_order_no="WO-DL-88219",
                    date="2026-02-20",
                    repair_station_name="Delta TechOps MRO",
                    repair_station_cert="CRS DALR026A",
                    part_number="322-049-204-0",
                    serial_number="SN-CFM-99100",
                    work_performed="Overhaul per CFM56 CMM 72-21-01. NDI FPI inspected clean.",
                    incoming_tsn=14200.0,
                    incoming_csn=6100,
                    outgoing_tsn=14200.0,
                    outgoing_csn=6100,
                    authorized_signoff="J. Henderson"
                )
            ),
            BtBDocument(
                document_id="DOC-04-FAA-8130-3",
                doc_type=DocumentType.FORM_8130_3,
                extracted_date="2026-03-05",
                part_number="322-049-204-0",
                serial_number="SN-CFM-99100",
                form_8130=Form8130_3(
                    document_id="DOC-04-FAA-8130-3",
                    block_1_country="USA / FAA",
                    block_2_org_name_address="Delta TechOps, Atlanta GA 30320",
                    block_3_form_tracking_no="DAL-8130-2026-401",
                    block_4_org_cert_no="CRS DALR026A",
                    block_5_work_order="WO-DL-88219",
                    block_7_description="BUSHING SHRD (IGV)",
                    block_8_part_number="322-049-204-0",
                    block_10_quantity=1,
                    block_11_status="OVERHAULED",
                    block_12_remarks="Overhauled per CFM56 CMM 72-21-01. Dual FAA/EASA release. TSN: 14200.0, CSN: 6100.",
                    block_14a_part_43_cert=True,
                    block_14b_signature="J. Henderson",
                    block_14c_approval_no="CRS DALR026A",
                    block_14d_name="John Henderson",
                    block_14e_date="2026-03-05",
                    block_13_shaded=True,
                    block_14_shaded=False,
                    user_installer_responsibilities_boilerplate_present=True,
                    serial_number="SN-CFM-99100"
                )
            )
        ]
    )


def create_demo_forged_package() -> BtBTracePackage:
    """Returns a package with AOG Technics SUP forgery red flags."""
    return BtBTracePackage(
        package_id="DEMO-AOG-TECHNICS-FORGERY",
        part_number="322-049-204-0",
        serial_number="SN-FORGED-001",
        description="bushing", # Suspicious generic term instead of BUSHING SHRD (IGV)
        is_life_limited=False,
        documents=[
            BtBDocument(
                document_id="DOC-FORGED-8130",
                doc_type=DocumentType.FORM_8130_3,
                extracted_date="2026-02-15",
                part_number="322-049-204-0",
                serial_number="SN-FORGED-001",
                form_8130=Form8130_3(
                    document_id="DOC-FORGED-8130",
                    block_1_country="USA / FAA",
                    block_2_org_name_address="AOG Technics Ltd / Fictitious Agency",
                    block_3_form_tracking_no="AOG-FAKE-998",
                    block_4_org_cert_no="CRS FAKE123A",
                    block_5_work_order="WO-9912",
                    block_7_description="bushing", # AOG Technics nomenclature error
                    block_8_part_number="322-049-204-0",
                    block_10_quantity=1,
                    block_11_status="OVERHAULED",
                    block_12_remarks="Overhauled component.",
                    block_14a_part_43_cert=True,
                    block_14b_signature="Bogus Signer",
                    block_14c_approval_no="CRS MISMATCH999B", # Cert mismatch vs Block 4
                    block_14d_name="Bogus Signer",
                    block_14e_date="2026-02-15",
                    block_13_shaded=False, # Unshaded Block 13 box!
                    block_14_shaded=False,
                    user_installer_responsibilities_boilerplate_present=False, # Missing mandatory boilerplate!
                    serial_number="SN-FORGED-001"
                )
            )
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="USM Back-to-Birth Trace Exception-Audit Desk")
    subparsers = parser.add_subparsers(dest="command")

    demo_p = subparsers.add_parser("demo", help="Run audit demonstration with synthetic packages")
    demo_p.add_argument("--out", default="data/demo_reports", help="Output directory for generated reports")

    audit_p = subparsers.add_parser("audit", help="Audit a package JSON or file directory")
    audit_p.add_argument("target", help="Path to package JSON or directory of document scans")
    audit_p.add_argument("--out", default="data/reports", help="Output directory for generated reports")

    args = parser.parse_args()

    pipeline = TraceAuditPipeline(backend=DeterministicMockBackend())

    if args.command == "demo":
        print("=== USM Trace Exception-Audit Desk — Demonstration Mode ===")
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Clean Package
        clean_pkg = create_demo_clean_package()
        rep_clean = pipeline.audit_package(clean_pkg, output_dir=str(out_dir))
        print(f"[CLEAN AUDIT] Package: {clean_pkg.package_id} -> Disposition: {rep_clean.disposition.value} (Score: {rep_clean.audit_score}/100)")

        # 2. Forged Package (AOG Technics SUP)
        forged_pkg = create_demo_forged_package()
        rep_forged = pipeline.audit_package(forged_pkg, output_dir=str(out_dir))
        print(f"[FORGERY AUDIT] Package: {forged_pkg.package_id} -> Disposition: {rep_forged.disposition.value} (Score: {rep_forged.audit_score}/100)")
        print(f"  Exceptions caught: {len(rep_forged.exceptions)}")
        for e in rep_forged.exceptions:
            print(f"   * [{e.severity.value}] {e.rule_name} ({e.block_ref}): {e.finding}")

        print(f"\n[COMPLETE] Exception reports saved to {out_dir.resolve()}/")
        sys.exit(0)

    elif args.command == "audit":
        p = Path(args.target)
        if not p.exists():
            print(f"Error: target {args.target} not found.", file=sys.stderr)
            sys.exit(1)

        if p.is_file() and p.suffix.lower() == ".json":
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            pkg = BtBTracePackage.model_validate(data)
            rep = pipeline.audit_package(pkg, output_dir=args.out)
            print(f"Audit completed: {rep.package_name} -> {rep.disposition.value} (Score: {rep.audit_score}/100)")
            sys.exit(0)
        else:
            print("Directory ingestion via OCR backend...")
            files = list(p.glob("*")) if p.is_dir() else [p]
            rep = pipeline.audit_files(
                file_paths=[str(f) for f in files],
                package_id=p.stem,
                part_number="GENERIC-PN",
                serial_number="GENERIC-SN",
                output_dir=args.out
            )
            print(f"Audit completed: {rep.package_name} -> {rep.disposition.value} (Score: {rep.audit_score}/100)")
            sys.exit(0)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
