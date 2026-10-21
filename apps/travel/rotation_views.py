"""
Rotation calendar + Medevac readiness views.
"""

from calendar import Calendar
from datetime import date, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone

from apps.experts.models import ExpertProfile
from .models import RotationSchedule, CharterFlight, CharterPassenger


@staff_member_required
def rotation_calendar(request):
    """Month grid showing who's ON-SITE vs OFF for each day."""
    today = timezone.now().date()

    # Parse ?year=&month= or default to current month
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month

    # Validate month
    if month < 1 or month > 12:
        month = today.month

    # Get all active rotations
    rotations = list(
        RotationSchedule.objects
        .filter(is_active=True)
        .select_related("expert")
        .order_by("expert__last_name", "expert__first_name")
    )

    # Build the calendar grid
    cal = Calendar(firstweekday=0)  # Monday first
    month_days = cal.monthdatescalendar(year, month)

    # For each rotation and each day of the month, determine on/off status
    grid = []
    for week in month_days:
        row = []
        for day in week:
            # Determine expert status map for this day
            statuses = []
            for r in rotations:
                status = _rotation_status_on(r, day)
                statuses.append({
                    "expert_id": str(r.expert.id),
                    "name": r.expert.full_name,
                    "on_site": status,
                })
            row.append({
                "date": day,
                "in_month": (day.month == month),
                "is_today": (day == today),
                "statuses": statuses,
            })
        grid.append(row)

    # Rotation summary
    on_site_count = sum(1 for r in rotations if r.is_on_site is True)
    off_site_count = sum(1 for r in rotations if r.is_on_site is False)

    context = {
        "year": year,
        "month": month,
        "month_name": date(year, month, 1).strftime("%B %Y"),
        "grid": grid,
        "rotations": rotations,
        "on_site_count": on_site_count,
        "off_site_count": off_site_count,
        "prev_year": year if month > 1 else year - 1,
        "prev_month": month - 1 if month > 1 else 12,
        "next_year": year if month < 12 else year + 1,
        "next_month": month + 1 if month < 12 else 1,
    }
    return render(request, "travel/rotation_calendar.html", context)


def _rotation_status_on(rotation, target_date):
    """Return True if the expert is ON-SITE on the target date, False otherwise, None if no schedule."""
    if not rotation.cycle_start_date:
        return None

    total = rotation.days_on + rotation.days_off
    if total == 0:
        return None

    days_since_start = (target_date - rotation.cycle_start_date).days
    if days_since_start < 0:
        return False

    phase_day = days_since_start % total
    return phase_day < rotation.days_on


@staff_member_required
def medevac_dashboard(request):
    """Shows who's on site right now + emergency contact readiness."""
    today = timezone.now().date()

    # Experts currently on-site (per rotation)
    on_site = []
    for r in RotationSchedule.objects.filter(is_active=True).select_related(
        "expert", "expert__site", "expert__department",
    ):
        if r.is_on_site is True:
            on_site.append(r.expert)

    # Upcoming medevac-ready flights
    medevac_flights = list(
        CharterFlight.objects
        .filter(
            medevac_ready=True,
            departure_datetime__date__gte=today,
        )
        .select_related("route", "operator", "aircraft")
        .order_by("departure_datetime")[:10]
    )

    # All upcoming flights in next 7 days (for reference)
    upcoming_flights = list(
        CharterFlight.objects
        .filter(
            departure_datetime__date__gte=today,
            departure_datetime__date__lte=today + timedelta(days=7),
        )
        .select_related("route", "operator", "aircraft")
        .order_by("departure_datetime")[:20]
    )

    context = {
        "today": today,
        "on_site": on_site,
        "on_site_count": len(on_site),
        "medevac_flights": medevac_flights,
        "upcoming_flights": upcoming_flights,
    }
    return render(request, "travel/medevac_dashboard.html", context)