"""
Expatriate Quota Service.

Business logic for computing compliance against:
    - 6.5% sector-wide cap (Ministerial Order No 33 / Aug 2025)
    - Per-category caps (Ministerial Decree 2005)

This is a SERVICE. It must not be called from templates.
Views call it. Tests cover it. It has no DB writes — pure computation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional

from django.core.cache import cache

from apps.experts.models import ExpertProfile
from apps.organization.models import Company

logger = logging.getLogger(__name__)


# ─── Legal constants (DRC law) ────────────────────────────────────
SECTOR_QUOTA_PCT = Decimal("6.5")

CATEGORY_QUOTA_PCT = {
    ExpertProfile.JobCategory.CLASS_I_V: Decimal("2.0"),
    ExpertProfile.JobCategory.SUPERVISOR: Decimal("2.5"),
    ExpertProfile.JobCategory.MANAGEMENT: Decimal("2.0"),
}


class QuotaRiskLevel(str, Enum):
    GREEN = "GREEN"       # < 5.5% — comfortable
    YELLOW = "YELLOW"     # 5.5% – 6.0% — watch
    ORANGE = "ORANGE"     # 6.0% – 6.5% — near cap
    RED = "RED"           # > 6.5% — breach
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CategoryQuota:
    """Per-category quota status."""
    category: str
    label: str
    legal_pct: Decimal
    actual_pct: Decimal
    expat_count: int
    total_in_category: int
    headroom: int
    is_compliant: bool


@dataclass(frozen=True)
class QuotaReport:
    """Full compliance snapshot for one company."""
    company_id: str
    company_name: str
    total_staff: int
    congolese_count: int
    expatriate_count: int
    sector_pct: Decimal
    sector_cap: Decimal
    sector_headroom: int
    sector_compliant: bool
    risk_level: QuotaRiskLevel
    categories: list[CategoryQuota] = field(default_factory=list)
    cache_hit: bool = False


# ─── Service ──────────────────────────────────────────────────────

class QuotaService:
    """
    Computes expatriate quota compliance for a given company.

    Usage:
        report = QuotaService(company).compute()
        if not report.sector_compliant:
            ...
    """

    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(self, company: Company) -> None:
        self.company = company
        self._log = logger.getChild(f"QuotaService[{company.slug}]")

    def compute(self, *, use_cache: bool = True) -> QuotaReport:
        """Return the compliance snapshot, optionally using cache."""
        cache_key = f"quota:report:{self.company.id}"

        if use_cache:
            cached: Optional[QuotaReport] = cache.get(cache_key)
            if cached is not None:
                return QuotaReport(
                    **{**cached.__dict__, "cache_hit": True}
                )

        report = self._compute_uncached()
        cache.set(cache_key, report, self.CACHE_TTL_SECONDS)

        self._log.info(
            "Quota computed",
            extra={
                "company_id": str(self.company.id),
                "sector_pct": str(report.sector_pct),
                "compliant": report.sector_compliant,
                "risk": report.risk_level.value,
            },
        )
        return report

    def invalidate_cache(self) -> None:
        cache.delete(f"quota:report:{self.company.id}")

    # ─── Private ──────────────────────────────────────────────────

    def _compute_uncached(self) -> QuotaReport:
        base_qs = ExpertProfile.objects.filter(
            company=self.company, is_active=True,
        )

        total = base_qs.count()
        expats = base_qs.filter(is_expatriate=True).count()
        congolese = total - expats

        sector_pct = (
            (Decimal(expats) / Decimal(total) * 100).quantize(Decimal("0.01"))
            if total > 0 else Decimal("0.00")
        )

        # Headroom = how many more expats can be added before breach
        max_expats_allowed = int(
            (Decimal(total + self.company.congolese_staff_count)
             * SECTOR_QUOTA_PCT / 100)
        ) if (total + self.company.congolese_staff_count) > 0 else 0
        headroom = max(0, max_expats_allowed - expats)

        sector_compliant = sector_pct <= SECTOR_QUOTA_PCT
        risk = self._classify_risk(sector_pct)

        categories = self._compute_categories(base_qs)

        return QuotaReport(
            company_id=str(self.company.id),
            company_name=self.company.name,
            total_staff=total,
            congolese_count=congolese,
            expatriate_count=expats,
            sector_pct=sector_pct,
            sector_cap=SECTOR_QUOTA_PCT,
            sector_headroom=headroom,
            sector_compliant=sector_compliant,
            risk_level=risk,
            categories=categories,
        )

    def _compute_categories(self, base_qs) -> list[CategoryQuota]:
        out: list[CategoryQuota] = []
        for cat_value, cat_label in ExpertProfile.JobCategory.choices:
            legal_pct = CATEGORY_QUOTA_PCT[cat_value]
            in_cat = base_qs.filter(job_category=cat_value)
            cat_total = in_cat.count()
            cat_expats = in_cat.filter(is_expatriate=True).count()
            actual_pct = (
                (Decimal(cat_expats) / Decimal(cat_total) * 100).quantize(Decimal("0.01"))
                if cat_total > 0 else Decimal("0.00")
            )
            out.append(
                CategoryQuota(
                    category=cat_value,
                    label=str(cat_label),
                    legal_pct=legal_pct,
                    actual_pct=actual_pct,
                    expat_count=cat_expats,
                    total_in_category=cat_total,
                    headroom=max(0, int(cat_total * legal_pct / 100) - cat_expats),
                    is_compliant=actual_pct <= legal_pct,
                )
            )
        return out

    @staticmethod
    def _classify_risk(pct: Decimal) -> QuotaRiskLevel:
        if pct > SECTOR_QUOTA_PCT:
            return QuotaRiskLevel.RED
        if pct >= Decimal("6.0"):
            return QuotaRiskLevel.ORANGE
        if pct >= Decimal("5.5"):
            return QuotaRiskLevel.YELLOW
        return QuotaRiskLevel.GREEN