"""
Compliance views — Risk Dashboard, exports, Unfold context callback.
"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext

from apps.experts.models import ExpertProfile
from apps.visas.models import (
    CarteDeTravail, FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa,
)
from apps.compliance.models import PenaltyLedger
from apps.organization.models import Company, UserCompanyMembership
from apps.compliance.services.quota_service import QuotaService


# ═══════════════════════════════════════════════════════════════
#  RISK SCORE — documented weights
# ═══════════════════════════════════════════════════════════════
#  HARD CAPS (take MINIMUM ceiling):
#    • Quota breach         → ceiling 25  (only if workforce data is complete)
#    • Expired passport     → ceiling 40
#    • Expired carte        → ceiling 45
#    • Unresolved penalty   → ceiling 60
#
#  SOFT DEDUCTIONS (from ceiling, cannot go below 0):
#    • Expired yellow fever : -8 each
#    • Passport ≤ 30 days   : -5 each
#    • Passport ≤ 60 days   : -3 each
#    • Passport ≤ 90 days   : -1 each
#    • Carte ≤ 30 days      : -4 each
#    • Carte ≤ 90 days      : -1 each
#    • Visa ≤ 30 days       : -4 each
#    • Visa ≤ 90 days       : -1 each
# ═══════════════════════════════════════════════════════════════

def compute_risk_score(
        passports_expired=0,
        cartes_expired=0,
        yellow_fever_expired=0,
        passports_t30=0,
        passports_t60=0,
        passports_t90=0,
        cartes_t30=0,
        cartes_t90=0,
        visas_t30=0,
        visas_t90=0,
        unresolved_penalties=0,
        quota_breached=False,
        workforce_data_complete=True,
):
    """
    Returns a dict:
        {
            'score': int,
            'ceiling': int,
            'hard_caps': [{'reason': str, 'ceiling': int}, ...],
            'soft_deductions': [{'reason': str, 'points': int}, ...],
            'workforce_warning': str or None,
        }
    """
    hard_caps = []
    soft = []

    # ── HARD CAPS ─────────────────────────────────────────────
    if quota_breached and workforce_data_complete:
        hard_caps.append({
            'reason': gettext("Expat quota breached (>6.5%)"),
            'ceiling': 25,
        })

    if passports_expired > 0:
        hard_caps.append({
            'reason': gettext("{n} expired passport(s)").format(n=passports_expired),
            'ceiling': 40,
        })

    if cartes_expired > 0:
        hard_caps.append({
            'reason': gettext("{n} expired Carte(s) de Travail").format(n=cartes_expired),
            'ceiling': 45,
        })

    if unresolved_penalties > 0:
        hard_caps.append({
            'reason': gettext("{n} unresolved DGM penalty(ies)").format(n=unresolved_penalties),
            'ceiling': 60,
        })

    # Determine the effective ceiling (minimum of all applicable caps)
    ceiling = 100
    for cap in hard_caps:
        ceiling = min(ceiling, cap['ceiling'])

    # ── SOFT DEDUCTIONS ──────────────────────────────────────
    if yellow_fever_expired > 0:
        soft.append({
            'reason': gettext("{n} expired Yellow Fever card(s)").format(n=yellow_fever_expired),
            'points': -8 * yellow_fever_expired,
        })
    if passports_t30 > 0:
        soft.append({
            'reason': gettext("{n} passport(s) expiring in ≤30 days").format(n=passports_t30),
            'points': -5 * passports_t30,
        })
    if passports_t60 > 0:
        soft.append({
            'reason': gettext("{n} passport(s) expiring in ≤60 days").format(n=passports_t60),
            'points': -3 * passports_t60,
        })
    if passports_t90 > 0:
        soft.append({
            'reason': gettext("{n} passport(s) expiring in ≤90 days").format(n=passports_t90),
            'points': -1 * passports_t90,
        })
    if cartes_t30 > 0:
        soft.append({
            'reason': gettext("{n} carte(s) expiring in ≤30 days").format(n=cartes_t30),
            'points': -4 * cartes_t30,
        })
    if cartes_t90 > 0:
        soft.append({
            'reason': gettext("{n} carte(s) expiring in ≤90 days").format(n=cartes_t90),
            'points': -1 * cartes_t90,
        })
    if visas_t30 > 0:
        soft.append({
            'reason': gettext("{n} visa(s) expiring in ≤30 days").format(n=visas_t30),
            'points': -4 * visas_t30,
        })
    if visas_t90 > 0:
        soft.append({
            'reason': gettext("{n} visa(s) expiring in ≤90 days").format(n=visas_t90),
            'points': -1 * visas_t90,
        })

    total_soft = sum(s['points'] for s in soft)
    score = max(0, min(100, ceiling + total_soft))

    workforce_warning = None
    if not workforce_data_complete:
        workforce_warning = gettext(
            "Workforce data incomplete. The quota hard cap was NOT applied. "
            "Please record a recent workforce snapshot."
        )

    return {
        'score': score,
        'ceiling': ceiling,
        'hard_caps': hard_caps,
        'soft_deductions': soft,
        'workforce_warning': workforce_warning,
    }


def _risk_label(score):
    """Return (label, color)."""
    if score >= 85:
        return (gettext("LOW"), "#2A9D8F")
    if score >= 60:
        return (gettext("MODERATE"), "#F4A261")
    if score >= 30:
        return (gettext("HIGH"), "#E76F51")
    return (gettext("CRITICAL"), "#E63946")


# ═══════════════════════════════════════════════════════════════
#  COMPLIANCE BOARD (with scope and company filter)
# ═══════════════════════════════════════════════════════════════

def _get_workforce_status(company):
    """
    Returns (is_complete, snapshot, warning_msg).
    Complete = snapshot exists AND is <31 days old.
    """
    if not company:
        return False, None, "No company selected."
    snap = company.workforce_snapshots.first()
    if not snap:
        return False, None, "No workforce snapshot recorded for this company."
    if snap.is_stale:
        from django.utils import timezone
        days = (timezone.now().date() - snap.snapshot_date).days
        return False, snap, f"Workforce snapshot is {days} days old. Please update."
    return True, snap, None


def _is_super_admin(user):
    """Super-admin / DGM / Ministry can see across companies."""
    if user.is_superuser:
        return True
    return False


@login_required
def dashboard(request):
    today = timezone.now().date()
    t90 = today + timedelta(days=90)
    t60 = today + timedelta(days=60)
    t30 = today + timedelta(days=30)

    # ── Scope resolution (FIXED) ──────────────────────────────
    is_super = _is_super_admin(request.user)
    selected_company_id = request.GET.get('company')

    if selected_company_id:
        # If a specific company is requested via the dropdown
        company = Company.objects.filter(id=selected_company_id, is_active=True).first()
    else:
        # Default to the user's assigned company
        membership = UserCompanyMembership.objects.filter(
            user=request.user, is_active=True
        ).select_related('company').first()

        if membership:
            company = membership.company
        elif is_super:
            company = None  # All companies for superusers with no membership
        else:
            company = None  # No access

    if not company and not is_super:
        return render(request, "compliance/dashboard.html", {
            "no_company": True, "is_super_admin": is_super,
        })

    # ── Managers ──────────────────────────────────────────────
    expert_mgr = ExpertProfile.objects
    if hasattr(expert_mgr, "unscoped"):
        expert_mgr = expert_mgr.unscoped()

    carte_mgr = CarteDeTravail.objects
    if hasattr(carte_mgr, "unscoped"):
        carte_mgr = carte_mgr.unscoped()

    penalty_mgr = PenaltyLedger.objects
    if hasattr(penalty_mgr, "unscoped"):
        penalty_mgr = penalty_mgr.unscoped()

    # ── Scoped querysets ──────────────────────────────────────
    if company:
        active_experts = expert_mgr.filter(is_active=True, company=company)
        cartes_all = carte_mgr.filter(is_active=True, expert__company=company)
        penalties_qs = penalty_mgr.filter(expert__company=company, resolved=False)
    else:
        # Super-admin "All Companies" view
        active_experts = expert_mgr.filter(is_active=True)
        cartes_all = carte_mgr.filter(is_active=True)
        penalties_qs = penalty_mgr.filter(resolved=False)

    total_experts = active_experts.count()

    # ── Passports ─────────────────────────────────────────────
    passports_expiring = list(
        active_experts.filter(
            passport_expiry_date__gte=today,
            passport_expiry_date__lte=t90,
        ).order_by("passport_expiry_date").distinct()
    )
    for e in passports_expiring:
        e.passport_days_left = (e.passport_expiry_date - today).days

    passports_expired = active_experts.filter(passport_expiry_date__lt=today).distinct()

    # ── Yellow fever ──────────────────────────────────────────
    yellow_fever_expired = active_experts.filter(
        yellow_fever_expiry_date__lt=today, yellow_fever_expiry_date__isnull=False,
    ).distinct()

    # ── Cartes ────────────────────────────────────────────────
    cartes_expired = cartes_all.filter(expiry_date__lt=today)
    cartes_expiring = list(
        cartes_all.filter(expiry_date__gte=today, expiry_date__lte=t90)
        .order_by("expiry_date").distinct()
    )

    # ── Visas ─────────────────────────────────────────────────
    visas_expiring = []
    visas_expired_count = 0
    for model in [FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa]:
        mgr = model.objects
        if hasattr(mgr, "unscoped"):
            mgr = mgr.unscoped()
        v_qs = mgr.filter(expiry_date__gte=today, expiry_date__lte=t90)
        if company:
            v_qs = v_qs.filter(expert__company=company)
        for v in v_qs.exclude(status__in=["CANCELLED", "EXPIRED"]).distinct():
            v.visa_model_label = model._meta.verbose_name
            visas_expiring.append(v)
        e_qs = mgr.filter(expiry_date__lt=today, status="ACTIVE")
        if company:
            e_qs = e_qs.filter(expert__company=company)
        visas_expired_count += e_qs.distinct().count()
    visas_expiring.sort(key=lambda x: x.expiry_date)

    # ── Penalties ─────────────────────────────────────────────
    active_penalties = list(penalties_qs)
    total_penalty_usd = sum(p.total_amount_usd for p in active_penalties)

    # ── Quota & Workforce ─────────────────────────────────────
    workforce_data_complete = False
    workforce_snapshot = None
    workforce_warning = None
    quota_breached = False
    quota_pct = 0.0
    quota_cap = 6.5

    # Per-company quota table (for super-admin "All Companies" view)
    company_quota_rows = []

    if company:
        workforce_data_complete, workforce_snapshot, workforce_warning = _get_workforce_status(company)
        if workforce_data_complete and workforce_snapshot:
            quota_pct = workforce_snapshot.expat_pct
            quota_cap = getattr(__import__('django.conf', fromlist=['settings']).settings, 'DRC_EXPAT_QUOTA_CAP', 6.5)
            quota_breached = quota_pct > quota_cap
    elif is_super:
        # Build per-company table
        for c in Company.objects.filter(is_active=True):
            complete, snap, _ = _get_workforce_status(c)
            row = {
                'company': c,
                'snapshot_date': snap.snapshot_date if snap else None,
                'expat': snap.total_expat_staff if snap else 0,
                'congolese': snap.total_congolese_staff if snap else 0,
                'workforce': snap.total_workforce if snap else 0,
                'pct': snap.expat_pct if snap else 0.0,
                'compliant': (snap.expat_pct <= quota_cap) if (complete and snap) else None,
                'data_complete': complete,
            }
            company_quota_rows.append(row)

    # ── Risk score ────────────────────────────────────────────
    risk = compute_risk_score(
        passports_expired=passports_expired.count(),
        cartes_expired=cartes_expired.count(),
        yellow_fever_expired=yellow_fever_expired.count(),
        passports_t30=sum(1 for e in passports_expiring if e.passport_days_left <= 30),
        passports_t60=sum(1 for e in passports_expiring if 30 < e.passport_days_left <= 60),
        passports_t90=sum(1 for e in passports_expiring if 60 < e.passport_days_left <= 90),
        cartes_t30=sum(1 for c in cartes_expiring if (c.expiry_date - today).days <= 30),
        cartes_t90=sum(1 for c in cartes_expiring if (c.expiry_date - today).days > 30),
        visas_t30=sum(1 for v in visas_expiring if v.expiry_date <= t30),
        visas_t90=sum(1 for v in visas_expiring if v.expiry_date > t30),
        unresolved_penalties=len(active_penalties),
        quota_breached=quota_breached,
        workforce_data_complete=workforce_data_complete,
    )
    risk_label, risk_color = _risk_label(risk['score'])

    context = {
        "today": today,
        "company": company,
        "is_super_admin": is_super,
        "selected_company_id": selected_company_id,
        "all_companies": Company.objects.filter(is_active=True) if is_super else [],
        "scope_label": company.name if company else "All Companies",
        "company_quota_rows": company_quota_rows,

        "workforce_data_complete": workforce_data_complete,
        "workforce_snapshot": workforce_snapshot,
        "workforce_warning": workforce_warning,

        "total_experts": total_experts,
        "passports_expiring_count": len(passports_expiring),
        "passports_expired_count": passports_expired.count(),
        "yellow_fever_expired_count": yellow_fever_expired.count(),
        "cartes_expiring_count": len(cartes_expiring),
        "cartes_expired_count": cartes_expired.count(),
        "visas_expiring_count": len(visas_expiring),
        "visas_expired_count": visas_expired_count,
        "penalty_count": len(active_penalties),
        "total_penalty_usd": float(total_penalty_usd),

        "compliance_score": risk['score'],
        "risk_ceiling": risk['ceiling'],
        "risk_hard_caps": risk['hard_caps'],
        "risk_soft_deductions": risk['soft_deductions'],
        "risk_label": risk_label,
        "risk_color": risk_color,

        "quota_pct": quota_pct,
        "quota_cap": quota_cap,
        "quota_breached": quota_breached,

        "passports_expiring": passports_expiring[:8],
        "cartes_expiring": cartes_expiring[:8],
        "visas_expiring": visas_expiring[:8],
        "active_penalties": active_penalties[:8],
    }
    return render(request, "compliance/dashboard.html", context)


# In apps/compliance/views.py, inside dashboard_context function

def dashboard_context(request, *args, **kwargs):
    """Context for Unfold's admin homepage dashboard callback."""
    from django.contrib.admin.models import LogEntry
    from apps.documents.models import DocumentVersion

    expert_mgr = ExpertProfile.objects
    if hasattr(expert_mgr, "unscoped"):
        expert_mgr = expert_mgr.unscoped()

    return {
        "kpi_experts": expert_mgr.filter(is_active=True).count(),
        "kpi_cartes": CarteDeTravail.objects.count(),
        "kpi_penalties": PenaltyLedger.objects.filter(resolved=False).count(),
        "kpi_documents": DocumentVersion.objects.count(),
        # FIXED: Removed list() to prevent slicing errors in Unfold template
        "log_entries": (
            LogEntry.objects
            .select_related("user", "content_type")
            .order_by("-action_time")[:10]
        ),
    }