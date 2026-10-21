"""
Generate the procurement PDF for mining companies (Kibali-ready).

Run: python manage.py generate_procurement_pdf

Output: media/reports/DRC_Expat_Platform_Proposal.pdf

Uses ReportLab (already installed). Customize by editing the
styles, colors, or section content below.
"""

from datetime import date
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Image,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


# ═══════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════

NAVY = colors.HexColor("#0B132B")
TEAL = colors.HexColor("#0D9488")
TEAL_LIGHT = colors.HexColor("#CCFBF1")
SLATE = colors.HexColor("#475569")
SLATE_LIGHT = colors.HexColor("#F1F5F9")
BORDER = colors.HexColor("#E2E8F0")
DANGER = colors.HexColor("#DC2626")
SUCCESS = colors.HexColor("#16A34A")


class Command(BaseCommand):
    help = "Generate the DRC Expat Platform procurement PDF."

    def handle(self, *args, **options):
        output_dir = Path(settings.MEDIA_ROOT) / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "DRC_Expat_Platform_Proposal.pdf"

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
            title="DRC Expat Compliance Platform — Proposal",
            author="DRC Expat Platform",
        )

        styles = self._build_styles()
        story = []

        # ── Cover ─────────────────────────────────────────
        self._cover(story, styles)

        # ── Contents ──────────────────────────────────────
        self._section_table_of_contents(story, styles)

        PageBreak_marker = PageBreak()

        # ── Main sections ────────────────────────────────
        story.append(PageBreak_marker)
        self._section_1_executive_summary(story, styles)

        story.append(PageBreak())
        self._section_2_problem(story, styles)

        story.append(PageBreak())
        self._section_3_platform(story, styles)

        story.append(PageBreak())
        self._section_4_modules(story, styles)

        story.append(PageBreak())
        self._section_5_security(story, styles)

        story.append(PageBreak())
        self._section_6_architecture(story, styles)

        story.append(PageBreak())
        self._section_7_multitenancy(story, styles)

        story.append(PageBreak())
        self._section_8_audit(story, styles)

        story.append(PageBreak())
        self._section_9_implementation(story, styles)

        story.append(PageBreak())
        self._section_10_commercial(story, styles)

        story.append(PageBreak())
        self._section_11_next_steps(story, styles)

        # ── Build with page numbers ─────────────────────
        doc.build(
            story,
            onFirstPage=self._page_footer,
            onLaterPages=self._page_footer,
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Proposal generated:\n   {output_path}\n"
        ))

    # ═══════════════════════════════════════════════════════════
    # STYLES
    # ═══════════════════════════════════════════════════════════

    def _build_styles(self):
        s = getSampleStyleSheet()

        s.add(ParagraphStyle(
            "CoverTitle", parent=s["Title"], fontName="Helvetica-Bold",
            fontSize=32, textColor=NAVY, leading=38, alignment=TA_LEFT,
            spaceAfter=6,
        ))
        s.add(ParagraphStyle(
            "CoverSub", parent=s["Normal"], fontName="Helvetica",
            fontSize=16, textColor=TEAL, leading=22, spaceAfter=30,
        ))
        s.add(ParagraphStyle(
            "CoverMeta", parent=s["Normal"], fontName="Helvetica",
            fontSize=11, textColor=SLATE, leading=16,
        ))
        s.add(ParagraphStyle(
            "SectionTitle", parent=s["Heading1"], fontName="Helvetica-Bold",
            fontSize=22, textColor=NAVY, leading=28, spaceBefore=0,
            spaceAfter=4,
        ))
        s.add(ParagraphStyle(
            "SectionSub", parent=s["Normal"], fontName="Helvetica",
            fontSize=12, textColor=SLATE, leading=16, spaceAfter=24,
        ))
        s.add(ParagraphStyle(
            "H2", parent=s["Heading2"], fontName="Helvetica-Bold",
            fontSize=14, textColor=NAVY, leading=20, spaceBefore=16,
            spaceAfter=8,
        ))
        s.add(ParagraphStyle(
            "H3", parent=s["Heading3"], fontName="Helvetica-Bold",
            fontSize=11, textColor=TEAL, leading=15, spaceBefore=12,
            spaceAfter=4,
        ))
        s.add(ParagraphStyle(
            "Body", parent=s["Normal"], fontName="Helvetica",
            fontSize=10, textColor=SLATE, leading=15, spaceAfter=8,
            alignment=TA_JUSTIFY,
        ))
        s.add(ParagraphStyle(
            "BulletBody", parent=s["Normal"], fontName="Helvetica",
            fontSize=10, textColor=SLATE, leading=15, leftIndent=14,
            bulletIndent=4, spaceAfter=4,
        ))
        s.add(ParagraphStyle(
            "TableCell", parent=s["Normal"], fontName="Helvetica",
            fontSize=9, textColor=SLATE, leading=12,
        ))
        s.add(ParagraphStyle(
            "TableCellBold", parent=s["Normal"], fontName="Helvetica-Bold",
            fontSize=9, textColor=NAVY, leading=12,
        ))
        s.add(ParagraphStyle(
            "CalloutTitle", parent=s["Normal"], fontName="Helvetica-Bold",
            fontSize=11, textColor=colors.white, leading=14,
        ))
        s.add(ParagraphStyle(
            "CalloutBody", parent=s["Normal"], fontName="Helvetica",
            fontSize=10, textColor=colors.white, leading=14,
        ))
        return s

    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════

    def _h1(self, text, styles):
        return [
            Paragraph(text, styles["SectionTitle"]),
            Table(
                [[""]],
                colWidths=[17 * cm],
                rowHeights=[2 * mm],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), TEAL),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]),
            ),
            Spacer(1, 14),
        ]

    def _bullet(self, text, styles):
        return Paragraph(f"• {text}", styles["BulletBody"])

    def _data_table(self, rows, styles, col_widths=None):
        """rows = list of [col1, col2, ...] with headers on row 0"""
        col_widths = col_widths or [6 * cm] * len(rows[0])
        t = Table(rows, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), SLATE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SLATE_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    def _page_footer(self, canvas, doc):
        """Draw footer with page number on every page."""
        canvas.saveState()
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, 1.4 * cm, 19 * cm, 1.4 * cm)

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(SLATE)
        canvas.drawString(2 * cm, 1 * cm, "DRC Expat Compliance Platform")
        canvas.drawRightString(19 * cm, 1 * cm, f"Page {doc.page}")

        canvas.restoreState()

    # ═══════════════════════════════════════════════════════════
    # COVER
    # ═══════════════════════════════════════════════════════════

    def _cover(self, story, styles):
        # Top accent bar
        accent = Table([[""]], colWidths=[17 * cm], rowHeights=[4 * mm],
                       style=TableStyle([
                           ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                       ]))
        story.append(accent)
        story.append(Spacer(1, 60))

        story.append(Paragraph(
            "DRC EXPAT COMPLIANCE PLATFORM",
            styles["CoverTitle"],
        ))
        story.append(Paragraph(
            "Enterprise Visa, Permit &amp; Charter Management<br/>for Mining Operations in the DRC",
            styles["CoverSub"],
        ))

        story.append(Spacer(1, 30))

        # Proposals details block
        details_data = [
            [Paragraph("<b>Prepared for</b>", styles["TableCellBold"]),
             Paragraph("Kibali Gold Mine — Compliance &amp; IT Teams", styles["TableCell"])],
            [Paragraph("<b>Prepared by</b>", styles["TableCellBold"]),
             Paragraph("DRC Expat Platform", styles["TableCell"])],
            [Paragraph("<b>Document type</b>", styles["TableCellBold"]),
             Paragraph("Commercial &amp; Technical Proposal", styles["TableCell"])],
            [Paragraph("<b>Version</b>", styles["TableCellBold"]),
             Paragraph("1.0", styles["TableCell"])],
            [Paragraph("<b>Date</b>", styles["TableCellBold"]),
             Paragraph(date.today().strftime("%B %d, %Y"), styles["TableCell"])],
            [Paragraph("<b>Validity</b>", styles["TableCellBold"]),
             Paragraph("90 days from issue", styles["TableCell"])],
        ]
        details = Table(details_data, colWidths=[4 * cm, 13 * cm])
        details.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER),
        ]))
        story.append(details)

        story.append(Spacer(1, 80))

        # Bottom tag
        story.append(Paragraph(
            "Confidential — Contains proprietary information",
            ParagraphStyle("Conf", parent=styles["CoverMeta"],
                          textColor=SLATE, fontSize=8),
        ))

    # ═══════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ═══════════════════════════════════════════════════════════

    def _section_table_of_contents(self, story, styles):
        story.append(PageBreak())
        story.extend(self._h1("Contents", styles))
        story.append(Spacer(1, 10))

        toc_rows = [
            ["1", "Executive Summary", "3"],
            ["2", "The DRC Compliance Problem", "4"],
            ["3", "Platform Overview", "5"],
            ["4", "Core Modules", "6"],
            ["5", "Security &amp; Compliance Posture", "8"],
            ["6", "Technical Architecture", "9"],
            ["7", "Multi-Tenancy Model", "10"],
            ["8", "Audit &amp; Evidence Trail", "11"],
            ["9", "Implementation &amp; Timeline", "12"],
            ["10", "Commercial Framework", "13"],
            ["11", "Next Steps", "14"],
        ]
        toc = Table(toc_rows, colWidths=[1 * cm, 14 * cm, 2 * cm])
        toc.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (-1, -1), SLATE),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
        ]))
        story.append(toc)

    # ═══════════════════════════════════════════════════════════
    # 1. EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════

    def _section_1_executive_summary(self, story, styles):
        story.extend(self._h1("1 · Executive Summary", styles))

        story.append(Paragraph(
            "The DRC Expat Compliance Platform is a purpose-built software-as-a-service "
            "solution for mining companies operating in the Democratic Republic of Congo. "
            "It centralises every compliance obligation imposed on foreign staff by the "
            "Direction Générale de Migration (DGM), the Ministry of Labour, and the ONEM "
            "labour registry — and it eliminates the manual workflows that expose mining "
            "operators to daily DGM fines, audit failures, and expatriate quota breaches.",
            styles["Body"],
        ))

        story.append(Paragraph(
            "Unlike generic HR platforms, the DRC Expat Platform is engineered around "
            "Congolese regulations from the first line of code. It enforces the 6.5% "
            "expatriate quota (Ministerial Order No 33 of 2025), the Ministry of Labour "
            "permit prerequisite for work visas, and the DGM manifest requirements for "
            "every domestic charter flight.",
            styles["Body"],
        ))

        story.append(Paragraph("What We Deliver", styles["H2"]))

        story.append(self._bullet(
            "<b>Real-time compliance score</b> — a single number from 0 to 100 that "
            "measures your exposure across every expert, document, and ministry.",
            styles,
        ))
        story.append(self._bullet(
            "<b>Automated T-90 / T-60 / T-30 alerts</b> — bilingual email and SMS "
            "reminders 90, 60, and 30 days before every document expires.",
            styles,
        ))
        story.append(self._bullet(
            "<b>Cross-ministry validation</b> — the platform refuses to mark a work "
            "visa active without a valid Carte de Travail, exactly as the law requires.",
            styles,
        ))
        story.append(self._bullet(
            "<b>One-click DGM manifests</b> — government-ready PDF manifests for every "
            "charter flight, signed by pilot, HR, and DGM officer.",
            styles,
        ))
        story.append(self._bullet(
            "<b>SOC 2-grade audit chain</b> — every action, hash-chained, tamper-proof, "
            "and available to inspectors on demand.",
            styles,
        ))

        story.append(Spacer(1, 16))

        # Highlight box
        callout = Table(
            [[Paragraph(
                "<b>The bottom line:</b> For a mining operator with 200–300 expatriate "
                "staff, unmanaged compliance exposes the company to an estimated "
                "<b>$450,000 to $2,000,000 per year</b> in DGM overstay fines, "
                "regulatory penalties, and administrative downtime. The DRC Expat "
                "Platform pays for itself within the first prevented incident.",
                styles["Body"],
            )]],
            colWidths=[17 * cm],
        )
        callout.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LINEBEFORE", (0, 0), (0, -1), 4, TEAL),
        ]))
        story.append(callout)

    # ═══════════════════════════════════════════════════════════
    # 2. THE PROBLEM
    # ═══════════════════════════════════════════════════════════

    def _section_2_problem(self, story, styles):
        story.extend(self._h1("2 · The DRC Compliance Problem", styles))

        story.append(Paragraph(
            "Mining companies in the DRC face a compliance landscape that is uniquely "
            "complex, multi-authority, and unforgiving. Every foreign expert is subject "
            "to at least six overlapping regulatory obligations, each with its own "
            "expiry cycle and its own authority.",
            styles["Body"],
        ))

        story.append(Paragraph("The Six Regulatory Authorities", styles["H2"]))

        rows = [
            ["Authority", "Obligation", "Failure Consequence"],
            ["DGM", "Visa validity (13 codes, incl. Prolongations)", "$100–$300/day per expat"],
            ["Ministry of Labour", "Carte de Travail permit", "Employment illegality, closure"],
            ["DGM + Labour", "6.5% expatriate quota cap", "Ministerial sanctions"],
            ["ONEM", "Labour registry declaration", "Administrative fines"],
            ["DGM", "Charter flight manifests", "Flight grounding"],
            ["Ministry of Health", "Yellow fever vaccination", "Entry refusal"],
        ]
        story.append(self._data_table(rows, styles, col_widths=[3.5 * cm, 8 * cm, 5.5 * cm]))

        story.append(Paragraph("Why Spreadsheets Fail", styles["H2"]))
        story.append(self._bullet(
            "Passports, cartes, and visas expire on different dates. Excel cannot alert "
            "at the right time, in the right language, to the right person.",
            styles,
        ))
        story.append(self._bullet(
            "The DGM ↔ Ministry of Labour dependency is bidirectional: a Work Visa "
            "cannot be active without a valid Carte, and a Carte renewal requires proof "
            "of employment. Excel does not enforce dependencies.",
            styles,
        ))
        story.append(self._bullet(
            "Every expert has 4–6 documents. With 200 experts, that's 1,200+ dates to "
            "track manually. Human error is not a possibility — it's a certainty.",
            styles,
        ))
        story.append(self._bullet(
            "Audit evidence is scattered across email inboxes and shared drives. When "
            "an inspector arrives, assembling a defensible file takes days, not minutes.",
            styles,
        ))

    # ═══════════════════════════════════════════════════════════
    # 3. PLATFORM OVERVIEW
    # ═══════════════════════════════════════════════════════════

    def _section_3_platform(self, story, styles):
        story.extend(self._h1("3 · Platform Overview", styles))

        story.append(Paragraph(
            "The DRC Expat Compliance Platform is a multi-tenant SaaS application "
            "delivered as a web interface. It is built on a modern Python/Django stack, "
            "uses PostgreSQL for relational data, Redis for task queues, and Celery for "
            "scheduled notifications. It is deployable on-premise in DRC or hosted in "
            "the cloud, with your choice of region.",
            styles["Body"],
        ))

        story.append(Paragraph("At a Glance", styles["H2"]))
        rows = [
            ["Attribute", "Detail"],
            ["Deployment model", "Multi-tenant SaaS, or dedicated single-tenant instance"],
            ["Access", "Web browser (Chrome, Edge, Firefox) + mobile-responsive"],
            ["Languages", "English &amp; French (fully bilingual, switchable per user)"],
            ["Hosting options", "Kinshasa DC, Johannesburg, Nairobi, or EU (your choice)"],
            ["Data encryption", "AES-256 at rest, TLS 1.3 in transit"],
            ["Audit", "Immutable SHA-256 hash-chained log of every action"],
            ["Compliance readiness", "SOC 2 Type II, ISO 27001, GDPR"],
            ["Integration", "REST API, Excel/CSV import/export, SSO-ready"],
        ]
        story.append(self._data_table(rows, styles, col_widths=[4 * cm, 13 * cm]))

    # ═══════════════════════════════════════════════════════════
    # 4. CORE MODULES
    # ═══════════════════════════════════════════════════════════

    def _section_4_modules(self, story, styles):
        story.extend(self._h1("4 · Core Modules", styles))

        story.append(Paragraph(
            "The platform ships with eleven production modules. Every module is "
            "available on day one of your pilot — no incremental licensing.",
            styles["Body"],
        ))

        story.append(Paragraph("4.1 — Visa Engine", styles["H3"]))
        story.append(Paragraph(
            "All 13 DRC visa codes supported: VV, VV2+, PVV3+, VV6, VSR+, VA, VVD, "
            "VET, VEO, DT, E-VVL, E-VETS, HOL-EX. Each visa is validated against its "
            "legal validity window, and prolongations are tracked as a formal chain.",
            styles["Body"],
        ))

        story.append(Paragraph("4.2 — Expatriate Quota Engine", styles["H3"]))
        story.append(Paragraph(
            "Real-time calculation of your expatriate percentage against the 6.5% "
            "sector-wide cap and per-category caps (2% Class I-V, 2.5% Supervisor, "
            "2% Management). Headroom displayed live. Breach caps the compliance score.",
            styles["Body"],
        ))

        story.append(Paragraph("4.3 — Cross-Ministry Validation", styles["H3"]))
        story.append(Paragraph(
            "A Work Visa cannot be marked Active without a corresponding valid Carte "
            "de Travail. The system additionally flags any case where the Carte expires "
            "before the visa — the exact scenario DGM penalises most heavily.",
            styles["Body"],
        ))

        story.append(Paragraph("4.4 — Document Versioning &amp; Chain of Custody", styles["H3"]))
        story.append(Paragraph(
            "Every passport scan, carte, DGM letter, and receipt is preserved with a "
            "SHA-256 hash. The system can prove no file was altered after upload — a "
            "requirement for both SOC 2 and DGM audits.",
            styles["Body"],
        ))

        story.append(Paragraph("4.5 — Notifications Engine", styles["H3"]))
        story.append(Paragraph(
            "Configurable alert tiers (T-90, T-60, T-30 by default). Bilingual email "
            "and SMS. Idempotent — the same alert never fires twice.",
            styles["Body"],
        ))

        story.append(Paragraph("4.6 — Charter &amp; Travel Management", styles["H3"]))
        story.append(Paragraph(
            "Operators (Kibali fleet, MAF, Bar Aviation, ICCN, Swala, Tracep), "
            "aircraft, routes, and flights. Passenger manifests for experts, "
            "dependants, and crew. One-click DGM-compliant manifest PDF.",
            styles["Body"],
        ))

        story.append(Paragraph("4.7 — Rotation Calendar &amp; Medevac Readiness", styles["H3"]))
        story.append(Paragraph(
            "Visual month grid showing who is on-site vs off-rotation. Medevac "
            "dashboard showing all personnel currently on site with evacuation routes.",
            styles["Body"],
        ))

        story.append(Paragraph("4.8 — Penalty Ledger", styles["H3"]))
        story.append(Paragraph(
            "Daily accrual of DGM overstay fines, tracked per expert. Compliance "
            "score drops automatically when penalties are active — bringing financial "
            "risk to the HR dashboard.",
            styles["Body"],
        ))

        story.append(Paragraph("4.9 — Cost Tracking &amp; Invoicing", styles["H3"]))
        story.append(Paragraph(
            "Every visa fee, carte fee, medical exam, translation, and flight seat "
            "is recorded per expert. Monthly invoicing per company available.",
            styles["Body"],
        ))

        story.append(Paragraph("4.10 — Government-Ready Exports", styles["H3"]))
        story.append(Paragraph(
            "Compliance report in PDF and Excel, DGM manifest in PDF, rotation "
            "roster, penalty ledger — all one-click, all audit-ready.",
            styles["Body"],
        ))

        story.append(Paragraph("4.11 — Risk Dashboard", styles["H3"]))
        story.append(Paragraph(
            "Executive view: compliance score, expat quota, expiring documents, "
            "active penalties, recent activity — refreshed in real time.",
            styles["Body"],
        ))

    # ═══════════════════════════════════════════════════════════
    # 5. SECURITY
    # ═══════════════════════════════════════════════════════════

    def _section_5_security(self, story, styles):
        story.extend(self._h1("5 · Security &amp; Compliance Posture", styles))

        story.append(Paragraph(
            "The platform was designed against the SOC 2 Type II and ISO 27001 "
            "control frameworks from the first line of code. Full audit-ready "
            "documentation is available under NDA.",
            styles["Body"],
        ))

        rows = [
            ["Control Area", "Implementation"],
            ["Data encryption at rest", "AES-256 for all sensitive fields (passport, permit, visa numbers)"],
            ["Data encryption in transit", "TLS 1.3 minimum, HSTS enforced"],
            ["Authentication", "Password + TOTP-based multi-factor authentication (MFA)"],
            ["Session management", "Secure cookies, 15-minute idle timeout, session rotation on privilege change"],
            ["Authorization", "Role-based access control (RBAC) — 5 roles across tenant, department, and site"],
            ["Multi-tenancy isolation", "Row-level scoping; every query filtered by tenant automatically"],
            ["Audit logging", "SHA-256 hash-chained immutable log; every action, actor, IP, timestamp captured"],
            ["Backup &amp; recovery", "Nightly encrypted backups; 30-day retention; quarterly restore drills"],
            ["Vulnerability management", "Dependency scanning (Dependabot), quarterly third-party pen-test"],
            ["Incident response", "24-hour response SLA on security incidents; documented playbook"],
            ["GDPR", "Data subject rights (access, erasure, portability) built into expert records"],
            ["Data residency", "Deployment in Kinshasa, Johannesburg, Nairobi, or EU — your choice"],
        ]
        story.append(self._data_table(rows, styles, col_widths=[4.5 * cm, 12.5 * cm]))

    # ═══════════════════════════════════════════════════════════
    # 6. ARCHITECTURE
    # ═══════════════════════════════════════════════════════════

    def _section_6_architecture(self, story, styles):
        story.extend(self._h1("6 · Technical Architecture", styles))

        story.append(Paragraph(
            "Modern, containerised, and cloud-agnostic. The platform runs identically "
            "in our cloud or on your infrastructure.",
            styles["Body"],
        ))

        rows = [
            ["Layer", "Technology"],
            ["Application", "Django 6, Python 3.13, Django REST Framework"],
            ["Admin UI", "Django Unfold (Tailwind-based enterprise theme)"],
            ["Database", "PostgreSQL 16 (encrypted at rest via pgcrypto)"],
            ["Task queue", "Celery 5 + Redis 7 (notifications, scheduled scans)"],
            ["Scheduler", "Celery Beat with database-backed schedules"],
            ["File storage", "Local / S3-compatible (MinIO for on-premise)"],
            ["Container", "Docker + Docker Compose; Kubernetes-ready"],
            ["Reverse proxy", "Nginx (production)"],
            ["Language/Runtime", "Python 3.13 (Ubuntu 24.04 LTS base image)"],
        ]
        story.append(self._data_table(rows, styles, col_widths=[4.5 * cm, 12.5 * cm]))

        story.append(Paragraph(
            "The platform is delivered as a set of Docker containers and can be "
            "deployed in under an hour on any Linux host meeting the minimum "
            "specifications (4 vCPU, 8 GB RAM, 100 GB SSD).",
            styles["Body"],
        ))

    # ═══════════════════════════════════════════════════════════
    # 7. MULTI-TENANCY
    # ═══════════════════════════════════════════════════════════

    def _section_7_multitenancy(self, story, styles):
        story.extend(self._h1("7 · Multi-Tenancy Model", styles))

        story.append(Paragraph(
            "The platform isolates every mining company at the database query layer. "
            "The isolation is enforced by a custom Django manager that filters every "
            "query by the active tenant — a safety guarantee validated by automated "
            "tests that ship with the codebase.",
            styles["Body"],
        ))

        story.append(Paragraph("Isolation Guarantees", styles["H2"]))
        story.append(self._bullet(
            "Every ExpertProfile, Carte de Travail, Visa, Penalty, Cost, and Document "
            "is linked to exactly one Company.",
            styles,
        ))
        story.append(self._bullet(
            "The middleware resolves the active tenant from the logged-in user's "
            "membership record on every request.",
            styles,
        ))
        story.append(self._bullet(
            "If no tenant is resolved, the manager returns an empty queryset — it fails "
            "safe, never leaks.",
            styles,
        ))
        story.append(self._bullet(
            "Department Managers see only their department. Site Managers see only "
            "their site. HR Managers see their whole company. Super Admins see "
            "everything (for support purposes).",
            styles,
        ))
        story.append(self._bullet(
            "5 automated test cases prove isolation at the ORM level — part of the "
            "shipped codebase, not a marketing promise.",
            styles,
        ))

    # ═══════════════════════════════════════════════════════════
    # 8. AUDIT
    # ═══════════════════════════════════════════════════════════

    def _section_8_audit(self, story, styles):
        story.extend(self._h1("8 · Audit &amp; Evidence Trail", styles))

        story.append(Paragraph(
            "Every action taken in the platform is recorded in an immutable, "
            "hash-chained audit log. Each entry stores the SHA-256 hash of the "
            "previous entry — making tampering mathematically detectable.",
            styles["Body"],
        ))

        story.append(Paragraph("Sample Audit Entry", styles["H3"]))

        sample_data = [
            ["Field", "Value"],
            ["Sequence", "233"],
            ["Timestamp", "2026-10-13 09:42:11 (UTC+1)"],
            ["Actor", "hr_manager@kibali.local"],
            ["Action", "UPDATE"],
            ["Model", "expertprofile"],
            ["Object", "Dupont, Jean (French)"],
            ["IP Address", "10.20.4.17"],
            ["Entry Hash", "8e8dc7b6079d18ab...56307046"],
            ["Previous Hash", "3f2a4b8c1d5e6f7a...e2c1f9a0"],
        ]
        story.append(self._data_table(sample_data, styles, col_widths=[4 * cm, 13 * cm]))

        story.append(Paragraph("Verification", styles["H3"]))
        story.append(Paragraph(
            "The verification is exposed as a management command that can be run at "
            "any time. Example output:",
            styles["Body"],
        ))
        story.append(Paragraph(
            "<font face='Courier' size='8' color='#475569'>"
            "✅ CHAIN INTACT — all entries verified.<br/>"
            "   Total entries : 233<br/>"
            "   Head hash     : 8e8dc7b6079d18ab7e9fc8661e1296beb401cb4f5569de7c726d63cc56307046<br/>"
            "   Head timestamp: 2026-10-13 09:42:11<br/>"
            "   Duration      : 89 ms"
            "</font>",
            styles["Body"],
        ))

        story.append(Paragraph(
            "This is the exact evidence a DGM inspector or a SOC 2 auditor will "
            "request — available in seconds, not days.",
            styles["Body"],
        ))

    # ═══════════════════════════════════════════════════════════
    # 9. IMPLEMENTATION
    # ═══════════════════════════════════════════════════════════

    def _section_9_implementation(self, story, styles):
        story.extend(self._h1("9 · Implementation &amp; Timeline", styles))

        story.append(Paragraph(
            "From signature to production: 6 weeks. The pilot phase can begin in "
            "week 3 with 20–30 of your real experts.",
            styles["Body"],
        ))

        rows = [
            ["Week", "Milestone", "Deliverable"],
            ["1", "Kickoff & discovery", "Refined requirements, integration scope"],
            ["2", "Environment setup", "Production instance provisioned, DNS, TLS"],
            ["3", "Data import — pilot 20-30 experts", "Excel/CSV import, validation, QA"],
            ["4", "User training (HR + Managers)", "2 live sessions, documentation"],
            ["5", "Full data import", "All 200-300 experts migrated"],
            ["6", "Go-live & hypercare", "24/7 support for 2 weeks"],
        ]
        story.append(self._data_table(rows, styles, col_widths=[1.5 * cm, 6 * cm, 9.5 * cm]))

        story.append(Paragraph("Training Included", styles["H2"]))
        story.append(self._bullet(
            "2 live training sessions (HR + Department Managers) — 90 min each.",
            styles,
        ))
        story.append(self._bullet(
            "Written runbook for common tasks (adding experts, uploading documents, "
            "generating manifests).",
            styles,
        ))
        story.append(self._bullet(
            "Video walkthroughs available in English and French.",
            styles,
        ))
        story.append(self._bullet(
            "Ongoing support via email and scheduled calls (see SLA below).",
            styles,
        ))

        story.append(Paragraph("Service Level Agreement", styles["H2"]))
        sla_rows = [
            ["Severity", "Response Time", "Resolution Target"],
            ["Critical (system down)", "1 hour", "4 hours"],
            ["High (major feature unavailable)", "4 hours", "24 hours"],
            ["Medium (degraded performance)", "1 business day", "3 business days"],
            ["Low (questions, minor issues)", "2 business days", "Next release"],
        ]
        story.append(self._data_table(sla_rows, styles, col_widths=[5 * cm, 5 * cm, 7 * cm]))

    # ═══════════════════════════════════════════════════════════
    # 10. COMMERCIAL
    # ═══════════════════════════════════════════════════════════

    def _section_10_commercial(self, story, styles):
        story.extend(self._h1("10 · Commercial Framework", styles))

        story.append(Paragraph(
            "The platform is offered as a monthly or annual subscription, with "
            "implementation and training as one-time fees. Pricing scales with the "
            "number of active experts under management.",
            styles["Body"],
        ))

        rows = [
            ["Tier", "Experts", "Monthly (USD)", "Annual (USD, ~15% off)"],
            ["Pilot", "Up to 30", "$450", "$4,590"],
            ["Standard", "31 – 100", "$1,200", "$12,240"],
            ["Professional", "101 – 250", "$2,400", "$24,480"],
            ["Enterprise", "251 – 500", "$3,900", "$39,780"],
            ["Enterprise Plus", "500+", "Custom", "Custom"],
        ]
        story.append(self._data_table(rows, styles, col_widths=[3.5 * cm, 3 * cm, 4.5 * cm, 6 * cm]))

        story.append(Paragraph("One-Time Fees", styles["H2"]))
        one_time = [
            ["Item", "Fee (USD)"],
            ["Implementation & data migration (up to 300 experts)", "$8,000"],
            ["Additional experts beyond 300", "$15 / expert"],
            ["Custom integrations (SAP, Workday, custom HRMS)", "$4,000 – $12,000"],
            ["On-site training (Kinshasa or Doko)", "$3,500 + travel"],
        ]
        story.append(self._data_table(one_time, styles, col_widths=[12 * cm, 5 * cm]))

        story.append(Paragraph("Notes", styles["H2"]))
        story.append(self._bullet(
            "All prices exclusive of VAT and applicable DRC taxes.",
            styles,
        ))
        story.append(self._bullet(
            "Annual payment attracts a 15% discount.",
            styles,
        ))
        story.append(self._bullet(
            "Pilot tier can be extended up to 6 months before transitioning to Standard.",
            styles,
        ))
        story.append(self._bullet(
            "Dedicated single-tenant instances are priced separately (approximately 40% uplift).",
            styles,
        ))
        story.append(self._bullet(
            "Source code escrow and full data export included at no additional cost.",
            styles,
        ))

    # ═══════════════════════════════════════════════════════════
    # 11. NEXT STEPS
    # ═══════════════════════════════════════════════════════════

    def _section_11_next_steps(self, story, styles):
        story.extend(self._h1("11 · Next Steps", styles))

        story.append(Paragraph(
            "We propose the following sequence to move from this document to a signed "
            "pilot agreement.",
            styles["Body"],
        ))

        steps = [
            ["Step", "Owner", "Target Date"],
            ["Technical deep-dive call (1 hour)", "IT + Compliance teams", "This week"],
            ["30-day pilot scope agreement", "Both parties", "Week 1"],
            ["Pilot agreement signature", "Procurement + Legal", "Week 2"],
            ["Environment provisioning begins", "Us", "Week 2"],
            ["Pilot kickoff", "Both parties", "Week 3"],
        ]
        story.append(self._data_table(steps, styles, col_widths=[8 * cm, 5 * cm, 4 * cm]))

        story.append(Spacer(1, 20))

        story.append(Paragraph("Contact", styles["H2"]))
        contact_data = [
            ["", ""],
            [Paragraph("<b>Commercial</b>", styles["TableCellBold"]),
             Paragraph("[Your name]<br/>[Email] · [Phone]", styles["TableCell"])],
            [Paragraph("<b>Technical</b>", styles["TableCellBold"]),
             Paragraph("[Your name]<br/>[Email] · [Phone]", styles["TableCell"])],
        ]
        contact = Table(contact_data, colWidths=[4 * cm, 13 * cm])
        contact.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(contact)

        story.append(Spacer(1, 30))

        # Sign-off box
        story.append(Paragraph(
            "Thank you for considering the DRC Expat Compliance Platform. "
            "We look forward to the pilot.",
            styles["Body"],
        ))