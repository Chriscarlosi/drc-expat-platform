"""
Travel exports — DGM manifest PDF for every charter flight.

Produces a government-ready manifest matching DGM requirements:
  • Flight details (number, route, aircraft, operator)
  • Full passenger roster with passport numbers, nationalities, DOB
  • Crew vs expat vs dependant breakdown
  • Report number + timestamp
  • Signature blocks for pilot + HR officer
"""

from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)

from .models import CharterFlight


@staff_member_required
def export_dgm_manifest(request, flight_id):
    """Generate the DGM flight manifest PDF for one flight."""
    try:
        flight = CharterFlight.objects.select_related(
            "operator", "aircraft", "route",
        ).get(pk=flight_id)
    except CharterFlight.DoesNotExist:
        return HttpResponse("Flight not found", status=404)

    passengers = list(
        flight.passengers.select_related("expert", "dependant").order_by("seat_number")
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title=f"DGM Manifest — {flight.flight_number}",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleX", parent=styles["Title"], fontSize=16,
        textColor=colors.HexColor("#0B132B"), alignment=1, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "SubX", parent=styles["Normal"], fontSize=10,
        textColor=colors.HexColor("#64748B"), alignment=1, spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "SectionX", parent=styles["Normal"], fontSize=11,
        textColor=colors.HexColor("#0B132B"), fontName="Helvetica-Bold",
        spaceAfter=6, spaceBefore=10,
    )
    cell_style = ParagraphStyle(
        "CellX", parent=styles["Normal"], fontSize=8, leading=10,
    )
    cell_small = ParagraphStyle(
        "CellSmall", parent=styles["Normal"], fontSize=7, leading=9,
    )
    header_style = ParagraphStyle(
        "HeaderX", parent=styles["Normal"], fontSize=8, leading=10,
        textColor=colors.white, fontName="Helvetica-Bold",
    )
    footer_style = ParagraphStyle(
        "FootX", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#64748B"), alignment=1,
    )

    elements = []

    # ══════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════
    elements.append(Paragraph("RÉPUBLIQUE DÉMOCRATIQUE DU CONGO", title_style))
    elements.append(Paragraph(
        "Direction Générale de Migration (DGM) — Flight Manifest / "
        "Manifeste de Vol",
        sub_style,
    ))

    # Reference line
    report_ref = f"DGM-{flight.departure_datetime.strftime('%Y%m%d')}-{flight.flight_number}"
    elements.append(Paragraph(
        f"<b>Reference:</b> {report_ref} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Generated:</b> {timezone.now().strftime('%B %d, %Y at %H:%M')} (Kinshasa time)",
        cell_style,
    ))
    elements.append(Spacer(1, 10))

    # ══════════════════════════════════════════════════════
    # FLIGHT DETAILS
    # ══════════════════════════════════════════════════════
    elements.append(Paragraph("FLIGHT DETAILS / DÉTAILS DU VOL", section_style))

    flight_data = [
        [
            Paragraph("<b>Flight Number</b>", header_style),
            Paragraph("<b>Operator</b>", header_style),
            Paragraph("<b>Aircraft</b>", header_style),
            Paragraph("<b>Route</b>", header_style),
            Paragraph("<b>Departure</b>", header_style),
            Paragraph("<b>Arrival</b>", header_style),
            Paragraph("<b>Status</b>", header_style),
        ],
        [
            Paragraph(flight.flight_number, cell_style),
            Paragraph(flight.operator.name, cell_style),
            Paragraph(
                f"{flight.aircraft.registration if flight.aircraft else '—'}<br/>"
                f"{flight.aircraft.model_name if flight.aircraft else ''}",
                cell_small,
            ),
            Paragraph(
                f"{flight.route.origin_iata} → {flight.route.destination_iata}<br/>"
                f"<font size='7'>{flight.route.origin_name} → {flight.route.destination_name}</font>",
                cell_small,
            ),
            Paragraph(
                flight.departure_datetime.strftime("%b %d, %Y<br/>%H:%M"),
                cell_small,
            ),
            Paragraph(
                flight.arrival_datetime.strftime("%b %d, %Y<br/>%H:%M"),
                cell_small,
            ),
            Paragraph(flight.get_status_display(), cell_small),
        ],
    ]

    flight_table = Table(
        flight_data,
        colWidths=[2.5*cm, 3.5*cm, 4*cm, 5*cm, 3*cm, 3*cm, 2.5*cm],
    )
    flight_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B132B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(flight_table)

    # ══════════════════════════════════════════════════════
    # PASSENGER MANIFEST
    # ══════════════════════════════════════════════════════
    elements.append(Paragraph(
        f"PASSENGER MANIFEST / MANIFESTE DES PASSAGERS ({len(passengers)} passengers)",
        section_style,
    ))

    if passengers:
        headers = [
            "#", "Seat", "Type", "Full Name / Nom complet", "Nationality",
            "Passport No.", "Date of Birth", "Status",
        ]
        data = [[Paragraph(h, header_style) for h in headers]]

        for i, p in enumerate(passengers, 1):
            # Compute passport / DOB
            if p.expert:
                passport = p.expert.passport_number or "—"
                dob = p.expert.date_of_birth.strftime("%Y-%m-%d") if p.expert.date_of_birth else "—"
                nationality = p.expert.nationality
            elif p.dependant:
                passport = p.dependant.passport_number or "—"
                dob = p.dependant.date_of_birth.strftime("%Y-%m-%d") if p.dependant.date_of_birth else "—"
                nationality = p.dependant.nationality
            else:
                passport = "—"
                dob = "—"
                nationality = "—"

            data.append([
                Paragraph(str(i), cell_small),
                Paragraph(p.seat_number or "—", cell_small),
                Paragraph(p.get_passenger_type_display(), cell_small),
                Paragraph(p.passenger_name, cell_small),
                Paragraph(nationality, cell_small),
                Paragraph(str(passport)[:20], cell_small),
                Paragraph(dob, cell_small),
                Paragraph(p.get_status_display(), cell_small),
            ])

        manifest_table = Table(
            data,
            colWidths=[0.8*cm, 1.2*cm, 2.2*cm, 5.5*cm, 3*cm, 3.5*cm, 2.5*cm, 2.5*cm],
            repeatRows=1,
        )
        manifest_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B132B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(manifest_table)
    else:
        elements.append(Paragraph(
            "<i>No passengers registered for this flight.</i>",
            cell_style,
        ))

    # ══════════════════════════════════════════════════════
    # BREAKDOWN
    # ══════════════════════════════════════════════════════
    expert_count = sum(1 for p in passengers if p.passenger_type == "EXPERT")
    dependant_count = sum(1 for p in passengers if p.passenger_type == "DEPENDANT")
    crew_count = sum(1 for p in passengers if p.passenger_type == "CREW")

    elements.append(Paragraph("SUMMARY / RÉSUMÉ", section_style))
    summary_data = [[
        Paragraph(f"<b>Expatriates:</b> {expert_count}", cell_style),
        Paragraph(f"<b>Dependants:</b> {dependant_count}", cell_style),
        Paragraph(f"<b>Crew:</b> {crew_count}", cell_style),
        Paragraph(f"<b>Total:</b> {len(passengers)}", cell_style),
    ]]
    summary_table = Table(summary_data, colWidths=[5*cm, 5*cm, 5*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)

    # ══════════════════════════════════════════════════════
    # SIGNATURE BLOCKS
    # ══════════════════════════════════════════════════════
    elements.append(Spacer(1, 20))

    sig_data = [[
        Paragraph(
            "<b>Pilot in Command / Commandant de bord</b><br/><br/>"
            "Name: ___________________________<br/><br/>"
            "Signature: ___________________________<br/><br/>"
            "Date: ___________________________",
            cell_style,
        ),
        Paragraph(
            "<b>HR / Compliance Officer</b><br/><br/>"
            "Name: ___________________________<br/><br/>"
            "Signature: ___________________________<br/><br/>"
            "Date: ___________________________",
            cell_style,
        ),
        Paragraph(
            "<b>DGM Officer / Agent DGM</b><br/><br/>"
            "Name: ___________________________<br/><br/>"
            "Signature: ___________________________<br/><br/>"
            "Date: ___________________________",
            cell_style,
        ),
    ]]
    sig_table = Table(sig_data, colWidths=[8*cm, 8*cm, 8*cm])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#0B132B")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(sig_table)

    # ══════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════
    elements.append(Spacer(1, 16))
    elements.append(Paragraph(
        "This manifest is generated by the DRC Expat Compliance Platform. "
        "Any alteration after signature voids the document. "
        "Ce manifeste est généré par la Plateforme de Conformité DRC Expat. "
        "Toute altération après signature annule le document.",
        footer_style,
    ))

    doc.build(elements)
    buffer.seek(0)

    filename = f"DGM_Manifest_{flight.flight_number}_{flight.departure_datetime.strftime('%Y%m%d')}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response