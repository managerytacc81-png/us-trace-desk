"""
Exception Report Generator.
Outputs structured JSON, GitHub-flavored Markdown, and 2-page executive PDF exception reports.
"""
import os
import json
from pathlib import Path
from typing import Optional
from trace_desk.models.exceptions import (
    ExceptionReport, AuditDisposition, ExceptionSeverity
)

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


class ReportGenerator:
    """Generates JSON, Markdown, and 2-page PDF Exception Reports."""

    @classmethod
    def to_json(cls, report: ExceptionReport, indent: int = 2) -> str:
        """Serializes report to structured JSON string."""
        return report.model_dump_json(indent=indent)

    @classmethod
    def save_json(cls, report: ExceptionReport, file_path: str) -> None:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cls.to_json(report), encoding="utf-8")

    @classmethod
    def to_markdown(cls, report: ExceptionReport) -> str:
        """Formats the audit exception report as GitHub-flavored Markdown."""
        lines = []
        disp_emoji = {
            AuditDisposition.PASS: "🟢 PASS",
            AuditDisposition.CONDITIONAL_PASS: "🟡 CONDITIONAL PASS",
            AuditDisposition.REJECT_SUP_ALERT: "🔴 REJECT - SUP ALERT (QUARANTINE)"
        }.get(report.disposition, str(report.disposition))

        lines.append(f"# USM Back-to-Birth Trace Exception Report")
        lines.append(f"**Audit Docket:** `{report.audit_id}` | **Date:** {report.timestamp[:10]} | **Auditor:** {report.auditor}\n")
        lines.append(f"### Operational Disposition: **{disp_emoji}** (Audit Compliance Score: **{report.audit_score}/100**)\n")

        lines.append("## 1. Article Identification & LLP Status")
        lines.append(f"| Parameter | Value |")
        lines.append(f"| :--- | :--- |")
        lines.append(f"| **Target Part Number** | `{report.part_number}` |")
        lines.append(f"| **Serial Number** | `{report.serial_number}` |")
        lines.append(f"| **Description** | {report.part_description} |")
        lines.append(f"| **Life-Limited Part (LLP)** | {'YES (Mandatory Life Limit)' if report.is_life_limited else 'NO (On-Condition / Hard Time)'} |")
        if report.is_life_limited:
            lines.append(f"| **Mandatory Life Limit (Cycles)** | {report.life_limit_cycles or 'N/A'} cycles |")
            lines.append(f"| **Current Accumulated Cycles (CSN)** | {report.current_csn or 'N/A'} cycles |")
            lines.append(f"| **Remaining Usable Cycles** | **{report.remaining_cycles or 'N/A'} cycles** |")
        lines.append(f"| **Current Flight Hours (TSN)** | {report.current_tsn or 'N/A'} hrs |")
        lines.append(f"| **Total Documents Audited** | {report.total_documents_analyzed} records |\n")

        lines.append("## 2. Regulatory & Forgery Exceptions Matrix")
        if not report.exceptions:
            lines.append("> [!NOTE]\n> **ZERO EXCEPTIONS FOUND**: All documents satisfy FAA Order 8130.21J, AC 43-9D, AC 120-84, and post-AOG Technics SUP anti-counterfeiting verifications.\n")
        else:
            lines.append(f"Found **{len(report.exceptions)} exception(s)** across the back-to-birth package:\n")
            lines.append("| ID | Severity | Category | Doc / Block | Finding & Regulatory Ref | Remedial Action |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for exc in report.exceptions:
                sev_badge = f"**{exc.severity.value}**"
                if exc.severity == ExceptionSeverity.CRITICAL:
                    sev_badge = f"🔴 **CRITICAL**"
                elif exc.severity == ExceptionSeverity.MAJOR:
                    sev_badge = f"🟠 **MAJOR**"
                elif exc.severity == ExceptionSeverity.MINOR:
                    sev_badge = f"🟡 **MINOR**"

                doc_block = f"`{exc.document_id or 'PKG'}` ({exc.block_ref or 'General'})"
                finding_text = f"**{exc.finding}**<br>_{exc.regulatory_ref}_<br>{exc.details}"
                lines.append(f"| `{exc.exception_id}` | {sev_badge} | {exc.category.value} | {doc_block} | {finding_text} | {exc.recommendation} |")
            lines.append("")

        lines.append("## 3. Chronological Chain of Custody Timeline")
        if report.custody_chain_summary:
            lines.append("| Date | Document ID | Type | Entity / Authority | TSN (Hrs) | CSN (Cyc) | Operational Event |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for evt in report.custody_chain_summary:
                tsn_str = f"{evt['flight_hours_tsn']:.1f}" if evt.get('flight_hours_tsn') is not None else "-"
                csn_str = str(evt.get('flight_cycles_csn')) if evt.get('flight_cycles_csn') is not None else "-"
                lines.append(f"| {evt.get('date')} | `{evt.get('document_id')}` | {evt.get('doc_type')} | {evt.get('entity')} | {tsn_str} | {csn_str} | {evt.get('summary')} |")
            lines.append("")

        lines.append("## 4. Quality Manager Action & Remediation Checklist")
        if report.disposition == AuditDisposition.REJECT_SUP_ALERT:
            lines.append("- [ ] **QUARANTINE ARTICLE IMMEDIATELY**: Affix red Rejected/Quarantine tag.")
            lines.append("- [ ] **SUBMIT FAA FORM 8120-11**: File Suspected Unapproved Parts notification with local FSDO.")
            lines.append("- [ ] **VENDOR CHARGEBACK**: Notify supplier of unapproved part rejection; demand commercial refund.")
        elif report.disposition == AuditDisposition.CONDITIONAL_PASS:
            lines.append("- [ ] **REQUEST VENDOR CLERICAL AMENDMENT**: Request corrected Form 8130-3 or bridging bill of sale.")
            lines.append("- [ ] **INTERNAL QA HOLD**: Place inventory on QA hold pending receipt of certified records.")
        else:
            lines.append("- [ ] **GREEN TAG RELEASE**: Back-to-birth package verified compliant. Article cleared for inventory or delivery.")

        lines.append("\n---\n*USM Trace Desk v1.0 — Pair-Audited under Autonomous Aviation Protocol*")
        return "\n".join(lines)

    @classmethod
    def save_markdown(cls, report: ExceptionReport, file_path: str) -> None:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cls.to_markdown(report), encoding="utf-8")

    @classmethod
    def to_pdf(cls, report: ExceptionReport, output_path: str) -> str:
        """
        Generates a concise, executive 2-page PDF Exception Report using ReportLab.
        """
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(p),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        title_style = ParagraphStyle(
            "DocTitle",
            parent=normal,
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold"
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=normal,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569")
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=normal,
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
            spaceBefore=8,
            spaceAfter=4
        )
        cell_style = ParagraphStyle(
            "CellNormal",
            parent=normal,
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1e293b")
        )
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=normal,
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold"
        )
        cell_crit = ParagraphStyle(
            "CellCritical",
            parent=normal,
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#991b1b"),
            fontName="Helvetica-Bold"
        )

        story = []

        # Header Title
        story.append(Paragraph("USM BACK-TO-BIRTH TRACE PRE-AUDIT EXCEPTION REPORT", title_style))
        story.append(Paragraph(
            f"<b>Docket:</b> {report.audit_id} &nbsp;|&nbsp; <b>Date:</b> {report.timestamp[:10]} &nbsp;|&nbsp; "
            f"<b>Auditor:</b> {report.auditor} &nbsp;|&nbsp; <b>Authority:</b> FAA Order 8130.21J / AC 43-9D",
            subtitle_style
        ))
        story.append(Spacer(1, 8))

        # Disposition Banner Box
        disp_bg = colors.HexColor("#dcfce7") # green
        disp_border = colors.HexColor("#16a34a")
        disp_text_color = "#166534"
        disp_label = f"AUDIT STATUS: PASS (Airworthy Back-to-Birth Trace Verified) — Score: {report.audit_score}/100"

        if report.disposition == AuditDisposition.REJECT_SUP_ALERT:
            disp_bg = colors.HexColor("#fee2e2") # red
            disp_border = colors.HexColor("#dc2626")
            disp_text_color = "#991b1b"
            disp_label = f"AUDIT STATUS: REJECT — SUP ALERT / QUARANTINE MANDATORY — Score: {report.audit_score}/100"
        elif report.disposition == AuditDisposition.CONDITIONAL_PASS:
            disp_bg = colors.HexColor("#fef3c7") # yellow
            disp_border = colors.HexColor("#d97706")
            disp_text_color = "#92400e"
            disp_label = f"AUDIT STATUS: CONDITIONAL PASS — Clerical Remediations Required — Score: {report.audit_score}/100"

        disp_p = Paragraph(
            f"<b><font size=10 color='{disp_text_color}'>{disp_label}</font></b>",
            cell_bold
        )
        banner_table = Table([[disp_p]], colWidths=[540])
        banner_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), disp_bg),
            ("BOX", (0, 0), (-1, -1), 1.5, disp_border),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 8))

        # Section 1: Article Metadata Table
        story.append(Paragraph("1. Article Specifications & Life-Limited Part (LLP) Tracking", h2_style))
        meta_data = [
            [
                Paragraph("<b>Part Number:</b>", cell_bold), Paragraph(report.part_number, cell_style),
                Paragraph("<b>Serial Number:</b>", cell_bold), Paragraph(report.serial_number, cell_style)
            ],
            [
                Paragraph("<b>Description:</b>", cell_bold), Paragraph(report.part_description, cell_style),
                Paragraph("<b>LLP Classified:</b>", cell_bold),
                Paragraph("YES (Mandatory Life Limit)" if report.is_life_limited else "NO (On-Condition)", cell_style)
            ],
            [
                Paragraph("<b>Current TSN (Hours):</b>", cell_bold),
                Paragraph(f"{report.current_tsn:.1f} hrs" if report.current_tsn is not None else "N/A", cell_style),
                Paragraph("<b>Current CSN (Cycles):</b>", cell_bold),
                Paragraph(f"{report.current_csn} cyc" if report.current_csn is not None else "N/A", cell_style)
            ],
            [
                Paragraph("<b>Mandatory Limit:</b>", cell_bold),
                Paragraph(f"{report.life_limit_cycles} cyc" if report.life_limit_cycles else "N/A", cell_style),
                Paragraph("<b>Remaining Cycles:</b>", cell_bold),
                Paragraph(f"<b>{report.remaining_cycles} cyc</b>" if report.remaining_cycles is not None else "N/A", cell_bold)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[110, 160, 110, 160])
        meta_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 8))

        # Section 2: Exceptions Table (Top Priority on Page 1)
        story.append(Paragraph(f"2. Audit Findings & Red Flags ({len(report.exceptions)} Discrepancies)", h2_style))

        if not report.exceptions:
            clean_msg = Paragraph("<b>All back-to-birth documents fully verified compliant with zero discrepancies.</b>", cell_style)
            story.append(clean_msg)
        else:
            exc_rows = [[
                Paragraph("<b>ID / Sev</b>", cell_bold),
                Paragraph("<b>Doc / Block</b>", cell_bold),
                Paragraph("<b>Regulatory Rule / Finding</b>", cell_bold),
                Paragraph("<b>Required Action</b>", cell_bold)
            ]]

            for exc in report.exceptions[:7]: # Show primary findings on Page 1/2
                sev_style = cell_crit if exc.severity == ExceptionSeverity.CRITICAL else cell_bold
                sev_p = Paragraph(f"<b>{exc.exception_id}</b><br/>{exc.severity.value}", sev_style)
                doc_p = Paragraph(f"<b>{exc.document_id}</b><br/>{exc.block_ref or 'Tag'}", cell_style)
                find_p = Paragraph(f"<b>{exc.finding}</b><br/><font color='#64748b'><i>{exc.regulatory_ref}</i></font><br/>{exc.details}", cell_style)
                rec_p = Paragraph(f"{exc.recommendation}", cell_style)
                exc_rows.append([sev_p, doc_p, find_p, rec_p])

            exc_table = Table(exc_rows, colWidths=[65, 85, 230, 160])
            exc_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(exc_table)

        # PAGE BREAK FOR PAGE 2
        story.append(PageBreak())

        # Page 2 Header
        story.append(Paragraph("USM BACK-TO-BIRTH TRACE REPORT — PAGE 2 (CUSTODY & DISPATCH)", subtitle_style))
        story.append(Spacer(1, 6))

        # Section 3: Chronological Custody Chain Table
        story.append(Paragraph("3. Back-to-Birth Custody & Flight Accumulation Chronology", h2_style))

        chrono_rows = [[
            Paragraph("<b>Date</b>", cell_bold),
            Paragraph("<b>Doc ID / Type</b>", cell_bold),
            Paragraph("<b>Releasing Entity / Operator</b>", cell_bold),
            Paragraph("<b>TSN (Hrs)</b>", cell_bold),
            Paragraph("<b>CSN (Cyc)</b>", cell_bold),
            Paragraph("<b>Event / Status Summary</b>", cell_bold)
        ]]

        for evt in report.custody_chain_summary:
            tsn_str = f"{evt['flight_hours_tsn']:.1f}" if evt.get('flight_hours_tsn') is not None else "-"
            csn_str = str(evt.get('flight_cycles_csn')) if evt.get('flight_cycles_csn') is not None else "-"
            chrono_rows.append([
                Paragraph(str(evt.get("date")), cell_style),
                Paragraph(f"<b>{evt.get('document_id')}</b><br/>{evt.get('doc_type')}", cell_style),
                Paragraph(str(evt.get("entity")), cell_style),
                Paragraph(tsn_str, cell_style),
                Paragraph(csn_str, cell_style),
                Paragraph(str(evt.get("summary")), cell_style)
            ])

        chrono_table = Table(chrono_rows, colWidths=[60, 95, 140, 50, 50, 145])
        chrono_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(chrono_table)
        story.append(Spacer(1, 10))

        # Section 4: Dealer Quality Manager Sign-Off Block
        story.append(Paragraph("4. Quality Assurance Disposition & Sign-off Block", h2_style))
        qa_data = [
            [
                Paragraph("<b>Pre-Audit Determination:</b>", cell_bold),
                Paragraph(f"<b>{report.disposition.value}</b> (Score: {report.audit_score}/100)", cell_bold),
                Paragraph("<b>Audit Date:</b>", cell_bold),
                Paragraph(f"{report.timestamp[:10]}", cell_style)
            ],
            [
                Paragraph("<b>Audited By:</b>", cell_bold),
                Paragraph(f"{report.auditor}", cell_style),
                Paragraph("<b>QA Inspection Seal:</b>", cell_bold),
                Paragraph("[ CERTIFIED PRE-AUDIT DOSSIER ]", cell_bold)
            ]
        ]
        qa_table = Table(qa_data, colWidths=[120, 150, 110, 160])
        qa_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(qa_table)
        story.append(Spacer(1, 12))

        story.append(Paragraph(
            "<b>Disclaimer:</b> This autonomous pre-audit docket provides automated regulatory compliance screening "
            "per FAA Order 8130.21J, AC 43-9D, and AC 120-84. The certified installer or certificated agency maintains "
            "ultimate responsibility for airworthiness determination prior to aircraft installation.",
            ParagraphStyle("Disclaimer", parent=normal, fontSize=6.5, leading=8.5, textColor=colors.HexColor("#64748b"))
        ))

        doc.build(story)
        return str(p)
