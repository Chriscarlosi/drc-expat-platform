"""Enterprise Risk & Penalty Mitigation Dashboard."""

from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q

from apps.experts.models import ExpertProfile
from apps.visas.models import (
    CarteDeTravail, FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa,
    VisaRecord, VisaTypeCatalog,
)
from apps.compliance.models import PenaltyLedger
from apps.organization.models import Company
from apps.compliance.services.quota_service import QuotaService

try:
    from auditlog.models import LogEntry
    HAS_AUDITLOG = True
except ImportError:
    HAS_AUDITLOG = False


@staff_member_required
def dashboard(request):
    today = timezone.now().date()
    t90 = today + timedelta(days=90)
    t60 = today + timedelta(days=60)
    t30 = today + timedelta(days=30)

    active_experts = ExpertProfile.objects.filter(is_active=True)
    total_experts = active_experts.count()

    passports_expiring = active_experts.filter(
        passport_expiry_date__gte=today,
        passport_expiry_date__lte=t90,
    ).order_by("passport_expiry_date")

    passports_expired = active_experts.filter(passport_expiry_date__lt=today)

    yellow_fever_expiring = active_experts.filter(
        yellow_fever_expiry_date__gte=today,
        yellow_fever_expiry_date__lte=t90,
    )

    cartes_expiring = CarteDeTravail.objects.filter(
        is_active=True, expiry_date__gte=today, expiry_date__lte=t90,
    ).order_by("expiry_date")

    visas_expiring = []
    for model in [FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa]:
        for v in model.objects.filter(
            expiry_date__gte=today, expiry_date__lte=t90,
        ).exclude(status__in=["CANCELLED", "EXPIRED"]):
            v.visa_model_label = model._meta.verbose_name
            visas_expiring.append(v)
    visas_expiring.sort(key=lambda x: x.expiry_date)

    active_penalties = list(PenaltyLedger.objects.filter(resolved=False))
    total_penalty_usd = sum(p.total_amount_usd for p in active_penalties)

    t30_count = (
        passports_expiring.filter(passport_expiry_date__lte=t30).count()
        + cartes_expiring.filter(expiry_date__lte=t30).count()
        + sum(1 for v in visas_expiring if v.expiry_date <= t30)
    )

    score = max(0, min(100, 100
        - passports_expired.count() * 10
        - t30_count * 5
        - len(active_penalties) * 3))
    risk_label, risk_color = _risk(score)

    # Quota (for first active company)
    company = Company.objects.filter(is_active=True).first()
    quota_report = QuotaService(company).compute() if company else None

    # ─── Trend data — documents expiring per 15-day window (6 buckets over 90d)
    trend_labels = ["0-15d", "16-30d", "31-45d", "46-60d", "61-75d", "76-90d"]
    trend_passports = [0] * 6
    for e in passports_expiring:
        d = (e.passport_expiry_date - today).days
        idx = min(d // 15, 5)
        trend_passports[idx] += 1
    trend_cartes = [0] * 6
    for c in cartes_expiring:
        d = (c.expiry_date - today).days
        idx = min(d // 15, 5)
        trend_cartes[idx] += 1
    trend_visas = [0] * 6
    for v in visas_expiring:
        d = (v.expiry_date - today).days
        idx = min(d // 15, 5)
        trend_visas[idx] += 1

    # ─── Activity feed — recent audit entries
    activity_feed = []
    if HAS_AUDITLOG:
        for entry in LogEntry.objects.select_related("actor").order_by("-timestamp")[:12]:
            activity_feed.append({
                "timestamp": entry.timestamp,
                "actor": entry.actor.username if entry.actor else "system",
                "action": entry.get_action_display(),
                "model": entry.content_type.model if entry.content_type else "—",
                "object_repr": entry.object_repr or "",
            })

    # ─── Category breakdown for heatmap
    cat_breakdown = []
    for cat_value, cat_label in ExpertProfile.JobCategory.choices:
        in_cat = active_experts.filter(job_category=cat_value)
        cat_total = in_cat.count()
        cat_expats = in_cat.filter(is_expatriate=True).count()
        cat_breakdown.append({
            "label": str(cat_label).split(" — ")[0],
            "total": cat_total,
            "expats": cat_expats,
            "congolese": cat_total - cat_expats,
        })

    context = {
        "today": today,
        "total_experts": total_experts,
        "passports_expiring_count": passports_expiring.count(),
        "passports_expired_count": passports_expired.count(),
        "yellow_fever_expiring_count": yellow_fever_expiring.count(),
        "cartes_expiring_count": cartes_expiring.count(),
        "visas_expiring_count": len(visas_expiring),
        "penalty_count": len(active_penalties),
        "total_penalty_usd": float(total_penalty_usd),
        "t30_count": t30_count,
        "compliance_score": score,
        "risk_label": risk_label,
        "risk_color": risk_color,
        "passports_expiring": passports_expiring[:8],
        "cartes_expiring": cartes_expiring[:8],
        "visas_expiring": visas_expiring[:8],
        "active_penalties": active_penalties[:8],
        "quota": quota_report,
        "activity_feed": activity_feed,
        "cat_breakdown": cat_breakdown,
        # Chart data
        "trend_labels": trend_labels,
        "trend_passports": trend_passports,
        "trend_cartes": trend_cartes,
        "trend_visas": trend_visas,
    }
    return render(request, "compliance/dashboard.html", context)


def _risk(score):
    if score >= 85:
        return ("LOW", "#2A9D8F")
    if score >= 60:
        return ("MODERATE", "#F4A261")
    if score >= 30:
        return ("HIGH", "#E76F51")
    return ("CRITICAL", "#E63946")