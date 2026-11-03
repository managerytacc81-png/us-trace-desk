"""
Synthetic Fixture Generator for BtB Trace Audit Suite.
Generates sample PDF and JSON files representing various audit scenarios.
"""
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_synthetic_pdf(filepath: str, title: str, blocks_text: dict):
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(p), pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, title)
    c.setFont("Helvetica", 9)
    y = 720
    for label, val in blocks_text.items():
        c.drawString(50, y, f"{label}: {val}")
        y -= 18
    c.save()


def generate_all_fixtures(fixtures_dir: str):
    f_dir = Path(fixtures_dir)
    f_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean FAA Form 8130-3 PDF
    generate_synthetic_pdf(
        str(f_dir / "clean_8130.pdf"),
        "FAA Form 8130-3 AIRWORTHINESS APPROVAL TAG",
        {
            "1. Approving Competent Authority / Country": "USA / FAA",
            "2. Organization Name and Address": "StandardAero San Antonio CRS 8SDR091K",
            "3. Form Tracking Number": "SA-8130-2026-9921",
            "4. Organization Certificate": "CRS 8SDR091K",
            "5. Work Order": "WO-77123",
            "7. Description": "BUSHING SHRD (IGV)",
            "8. Part Number": "322-049-204-0",
            "10. Quantity": "1",
            "11. Status/Work": "OVERHAULED",
            "12. Remarks": "Overhauled in accordance with CFM56-7B CMM 72-21-01. TSN: 11200.0, CSN: 5100",
            "14. Return to Service": "14 CFR 43.9 Return to Service certified. Signer: Dan Morgan, CRS 8SDR091K, 2026-02-18",
            "User Responsibilities": "It is important to understand that the existence of this document alone does not automatically constitute authority to install..."
        }
    )

    # 2. Forged AOG Technics 8130-3 PDF (Missing boilerplate, generic nomenclature 'bushing', mismatched cert)
    generate_synthetic_pdf(
        str(f_dir / "forged_aog_8130.pdf"),
        "FAA Form 8130-3 AIRWORTHINESS APPROVAL TAG",
        {
            "1. Approving Competent Authority / Country": "USA / FAA",
            "2. Organization Name and Address": "AOG Technics Ltd / Releasing CRS",
            "3. Form Tracking Number": "AOG-2023-FORGED-01",
            "4. Organization Certificate": "CRS 8OFR272Y",
            "5. Work Order": "WO-4412",
            "7. Description": "bushing", # generic red flag
            "8. Part Number": "322-049-204-0",
            "10. Quantity": "1",
            "11. Status/Work": "OVERHAULED",
            "12. Remarks": "Overhauled component.",
            "14. Return to Service": "Signer: F. Smith, Approval No: CRS 999FAKE88, Date: 2026-01-01"
            # Note: No User Responsibilities boilerplate!
        }
    )

    # 3. Clean Trace Package JSON
    clean_pkg_json = {
        "package_id": "PKG-FIXTURE-CFM56-CLEAN",
        "part_number": "322-049-204-0",
        "serial_number": "SN-88210",
        "description": "BUSHING SHRD (IGV)",
        "is_life_limited": True,
        "life_limit_cycles": 20000,
        "life_limit_hours": 50000.0,
        "documents": [
            {
                "document_id": "DOC-01-REMOVAL",
                "doc_type": "REMOVAL_TAG",
                "extracted_date": "2026-01-10",
                "part_number": "322-049-204-0",
                "serial_number": "SN-88210",
                "removal_tag": {
                    "document_id": "DOC-01-REMOVAL",
                    "tag_number": "TAG-101",
                    "date": "2026-01-10",
                    "removing_organization": "Delta TechOps",
                    "part_number": "322-049-204-0",
                    "serial_number": "SN-88210",
                    "reason_for_removal": "Shop visit",
                    "part_hours_tsn": 10000.0,
                    "part_cycles_csn": 4000,
                    "inspector_name": "T. Jones"
                }
            },
            {
                "document_id": "DOC-02-8130",
                "doc_type": "FORM_8130_3",
                "extracted_date": "2026-02-01",
                "part_number": "322-049-204-0",
                "serial_number": "SN-88210",
                "form_8130": {
                    "document_id": "DOC-02-8130",
                    "block_1_country": "USA / FAA",
                    "block_2_org_name_address": "StandardAero San Antonio",
                    "block_3_form_tracking_no=":"SA-2026-001",
                    "block_4_org_cert_no": "CRS 8SDR091K",
                    "block_5_work_order": "WO-5512",
                    "block_7_description": "BUSHING SHRD (IGV)",
                    "block_8_part_number": "322-049-204-0",
                    "block_10_quantity": 1,
                    "block_11_status": "OVERHAULED",
                    "block_12_remarks": "Overhauled. TSN: 10000.0, CSN: 4000",
                    "block_14a_part_43_cert": True,
                    "block_14b_signature": "D. Morgan",
                    "block_14c_approval_no": "CRS 8SDR091K",
                    "block_14d_name": "Dan Morgan",
                    "block_14e_date": "2026-02-01",
                    "block_13_shaded": True,
                    "block_14_shaded": False,
                    "user_installer_responsibilities_boilerplate_present": True,
                    "serial_number": "SN-88210"
                }
            }
        ]
    }
    (f_dir / "clean_package.json").write_text(json.dumps(clean_pkg_json, indent=2), encoding="utf-8")


if __name__ == "__main__":
    generate_all_fixtures("/home/user/revenue-eval/submissions/us-trace-desk/fixtures")
    print("Fixtures generated successfully.")
