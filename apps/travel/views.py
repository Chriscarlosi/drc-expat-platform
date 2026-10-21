"""
Travel views — cost dashboard + printable manifest.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from .models import (
    CharterFlight, CharterPassenger, CharterRoute, CharterOperator,
)


@staff_member_required
def cost_dashboard(request):
    """Charter cost analytics — spend by route, operator, expert, month."""

    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # ── Base queryset: booked passengers with cost > 0 ──────
    qs = (
        CharterPassenger.objects
        .filter(ticket_cost_usd__gt=0)
        .select_related(
            "flight", "flight__route", "flight__operator",
            "expert", "dependant",
        )
    )

    # ── Totals ──────────────────────────────────────────────
    total_all_time = qs.aggregate(t=Sum("ticket_cost_usd"))["t"] or Decimal("0")
    total_this_month = qs.filter(
        flight__departure_datetime__date__gte=month_start,
    ).aggregate(t=Sum("ticket_cost_usd"))["t"] or Decimal("0")
    total_this_year = qs.filter(
        flight__departure_datetime__date__gte=year_start,
    ).aggregate(t=Sum("ticket_cost_usd"))["t"] or Decimal("0")

    # ── By route ────────────────────────────────────────────
    by_route = (
        qs.values(
            "flight__route__origin_iata",
            "flight__route__destination_iata",
            "flight__route__origin_name",
            "flight__route__destination_name",
        )
        .annotate(
            total=Sum("ticket_cost_usd"),
            passengers=Count("id"),
        )
        .order_by("-total")[:15]
    )

    # ── By operator ─────────────────────────────────────────
    by_operator = (
        qs.values("flight__operator__name", "flight__operator__code")
        .annotate(total=Sum("ticket_cost_usd"), passengers=Count("id"))
        .order_by("-total")
    )

    # ── By expert (top 15) ──────────────────────────────────
    by_expert = (
        qs.filter(expert__isnull=False)
        .values("expert__first_name", "expert__last_name", "expert__nationality")
        .annotate(total=Sum("ticket_cost_usd"), flights=Count("id"))
        .order_by("-total")[:15]
    )

    # ── Monthly trend (last 12 months) ──────────────────────
    monthly = []
    for i in range(11, -1, -1):
        # Calculate month start
        ref = today.replace(day=1) - timedelta(days=i * 30)
        m_start = ref.replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1)

        total = qs.filter(
            flight__departure_datetime__date__gte=m_start,
            flight__departure_datetime__date__lt=m_end,
        ).aggregate(t=Sum("ticket_cost_usd"))["t"] or Decimal("0")

        monthly.append({
            "label": m_start.strftime("%b %Y"),
            "total": float(total),
        })

    # ── JSON for ECharts ────────────────────────────────────
    dashboard_json = {
        "monthly_labels": [m["label"] for m in monthly],
        "monthly_totals": [m["total"] for m in monthly],
        "route_labels": [
            f"{r['flight__route__origin_iata']} → {r['flight__route__destination_iata']}"
            for r in by_route
        ],
        "route_totals": [float(r["total"]) for r in by_route],
        "operator_labels": [o["flight__operator__code"] for o in by_operator],
        "operator_totals": [float(o["total"]) for o in by_operator],
    }

    context = {
        "today": today,
        "total_all_time": total_all_time,
        "total_this_month": total_this_month,
        "total_this_year": total_this_year,
        "by_route": by_route,
        "by_operator": by_operator,
        "by_expert": by_expert,
        "dashboard_json": dashboard_json,
    }
    return render(request, "travel/cost_dashboard.html", context)


@staff_member_required
def flight_manifest_print(request, flight_id):
    """Printable HTML manifest for the departure desk — large print, checkboxes."""
    flight = get_object_or_404(
        CharterFlight.objects.select_related(
            "operator", "aircraft", "route",
        ),
        pk=flight_id,
    )
    passengers = list(
        flight.passengers
        .select_related("expert", "dependant")
        .order_by("seat_number")
    )

    context = {
        "flight": flight,
        "passengers": passengers,
        "generated_at": timezone.now(),
        "expert_count": sum(1 for p in passengers if p.passenger_type == "EXPERT"),
        "dependant_count": sum(1 for p in passengers if p.passenger_type == "DEPENDANT"),
        "crew_count": sum(1 for p in passengers if p.passenger_type == "CREW"),
    }
    return render(request, "travel/manifest_print.html", context)