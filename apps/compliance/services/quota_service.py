"""
Expatriate Quota Service — mathematically correct, per-company and per-site.

Legal basis:
  • Ministerial Order No 33 (Aug 2025): 6.5% sector-wide cap for extractive industries
  • Ministerial Decree 2005: per-category caps (2%, 2.5%, 2%)

Math:
  Let C = Congolese staff count, E = expat count.
  Legal ratio: E / (C + E) ≤ 0.065
  Solving for E: E ≤ C × 0.065 / 0.935 = C × 0.0695...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN
from enum import Enum

from django.core.cache import cache

from apps.experts.models import ExpertProfile
from apps.organization.models import Company, Site

logger = logging.getLogger(__name__)


# ─── Legal constants ──────────────────────────────────────────
SECTOR_QUOTA_PCT = Decimal("6.5")

CATEGORY_QUOTA_PCT = {
    ExpertProfile.JobCategory.CLASS_I_V: Decimal("2.0"),
    ExpertProfile.JobCategory.SUPERVISOR: Decimal("2.5"),
    ExpertProfile.JobCategory.MANAGEMENT: Decimal("2.0"),
}

# Derived: maximum expat-to-local ratio for legal compliance
_MAX_EXPAT_PER_LOCAL = SECTOR_QUOTA_PCT / (Decimal("100") - SECTOR_QUOTA_PCT)


class QuotaRiskLevel(str, Enum):
    GREEN = "GREEN"        # < 5.5%
    YELLOW = "YELLOW"      # 5.5% – 6.0%
    ORANGE = "ORANGE"      # 6.0% – 6.5%
    RED = "RED"            # > 6.5% — breach
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CategoryQuota:
    category: str
    label: str
    legal_pct: Decimal
    actual_pct: Decimal
    expat_count: int
    total_in_category: int
    headroom: int
    is_compliant: bool


@dataclass(frozen=True)
class SiteQuota:
    """Quota snapshot for one specific site."""
    site_id: str
    site_name: str
    congolese_count: int
    expatriate_count: int
    sector_pct: Decimal
    max_allowed: int
    headroom: int
    is_compliant: bool
    risk_level: QuotaRiskLevel


@dataclass(frozen=True)
class QuotaReport:
    """Company-wide quota report with per-site and per-category breakdowns."""
    company_id: str
    company_name: str
    # ── Company totals ────────────────────────────────────
    congolese_staff: int           # from Company.congolese_staff_count
    expatriate_count: int          # live from ExpertProfile
    total_workforce: int           # congolese + expat
    # ── Ratios ────────────────────────────────────────────
    sector_pct: Decimal            # expat / total * 100
    sector_cap: Decimal            # 6.5
    max_expats_allowed: int        # what the math says the ceiling is
    headroom: int                  # max_allowed - current
    is_compliant: bool
    risk_level: QuotaRiskLevel
    # ── Breakdowns ────────────────────────────────────────
    categories: list[CategoryQuota] = field(default_factory=list)
    sites: list[SiteQuota] = field(default_factory=list)
    cache_hit: bool = False


class QuotaService:
    """
    Computes expatriate quota compliance for a company, its sites, and its
    job categories.

    Usage:
        report = QuotaService(company).compute()
        if not report.is_compliant:
            ...
    """

    CACHE_TTL_SECONDS = 300

    def __init__(self, company: Company) -> None:
        self.company = company
        self._log = logger.getChild(f"QuotaService[{company.slug}]")

    # ────────────────────────────────────────────────────────
    # PUBLIC
    # ────────────────────────────────────────────────────────

    def compute(self, *, use_cache: bool = True) -> QuotaReport:
        cache_key = f"quota:report:v2:{self.company.id}"

        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return QuotaReport(**{**cached.__dict__, "cache_hit": True})

        report = self._compute_uncached()
        cache.set(cache_key, report, self.CACHE_TTL_SECONDS)
        return report

    def invalidate_cache(self) -> None:
        cache.delete(f"quota:report:v2:{self.company.id}")

    # ────────────────────────────────────────────────────────
    # CORE MATH
    # ────────────────────────────────────────────────────────

    @staticmethod
    def max_expats_for(congolese_count: int) -> int:
        """
        Solve E / (C + E) <= 0.065 for E.

        E <= C * 0.065 / 0.935
        """
        if congolese_count <= 0:
            return 0
        return int(
            (Decimal(congolese_count) * _MAX_EXPAT_PER_LOCAL).to_integral_value(
                rounding=ROUND_DOWN
            )
        )

    @staticmethod
    def classify(pct: Decimal) -> QuotaRiskLevel:
        if pct > SECTOR_QUOTA_PCT:
            return QuotaRiskLevel.RED
        if pct >= Decimal("6.0"):
            return QuotaRiskLevel.ORANGE
        if pct >= Decimal("5.5"):
            return QuotaRiskLevel.YELLOW
        return QuotaRiskLevel.GREEN

    # ────────────────────────────────────────────────────────
    # COMPUTE
    # ────────────────────────────────────────────────────────

    def _compute_uncached(self) -> QuotaReport:
        base_qs = ExpertProfile.objects.unscoped().filter(
            company=self.company, is_active=True,
        )

        expat_count = base_qs.count()
        congolese = self.company.congolese_staff_count or 0
        total_workforce = congolese + expat_count

        pct = (
            (Decimal(expat_count) / Decimal(total_workforce) * 100).quantize(Decimal("0.01"))
            if total_workforce > 0
            else Decimal("0.00")
        )

        max_allowed = self.max_expats_for(congolese)
        headroom = max(0, max_allowed - expat_count)
        is_compliant = expat_count <= max_allowed and pct <= SECTOR_QUOTA_PCT

        categories = self._compute_categories(base_qs)
        sites = self._compute_sites()

        return QuotaReport(
            company_id=str(self.company.id),
            company_name=self.company.name,
            congolese_staff=congolese,
            expatriate_count=expat_count,
            total_workforce=total_workforce,
            sector_pct=pct,
            sector_cap=SECTOR_QUOTA_PCT,
            max_expats_allowed=max_allowed,
            headroom=headroom,
            is_compliant=is_compliant,
            risk_level=self.classify(pct),
            categories=categories,
            sites=sites,
        )

    def _compute_categories(self, base_qs) -> list[CategoryQuota]:
        out: list[CategoryQuota] = []
        for value, label in ExpertProfile.JobCategory.choices:
            legal = CATEGORY_QUOTA_PCT[value]
            qs_cat = base_qs.filter(job_category=value)
            cat_total = qs_cat.count()
            cat_expats = qs_cat.filter(is_expatriate=True).count()

            # Category cap is applied to the category size
            max_in_cat = int(Decimal(cat_total) * legal / 100)

            actual = (
                (Decimal(cat_expats) / Decimal(cat_total) * 100).quantize(Decimal("0.01"))
                if cat_total > 0 else Decimal("0.00")
            )

            out.append(CategoryQuota(
                category=value,
                label=str(label),
                legal_pct=legal,
                actual_pct=actual,
                expat_count=cat_expats,
                total_in_category=cat_total,
                headroom=max(0, max_in_cat - cat_expats),
                is_compliant=actual <= legal,
            ))
        return out

    def _compute_sites(self) -> list[SiteQuota]:
        """Compute quota per site, using the company's aggregate Congolese/Expat ratio."""
        sites: list[SiteQuota] = []
        for site in Site.objects.filter(company=self.company):
            site_qs = ExpertProfile.objects.unscoped().filter(
                company=self.company, site=site, is_active=True,
            )
            site_expats = site_qs.filter(is_expatriate=True).count()
            site_total = site_qs.count()

            # Use site-specific Congolese count if HR has recorded it — else fall back
            # to the company-wide ratio applied to this site's expert count.
            site_congolese = getattr(site, "congolese_staff_count", None)
            if site_congolese is None:
                site_congolese = site_total - site_expats

            if site_congolese > 0 or site_expats > 0:
                workforce = site_congolese + site_expats
                pct = (
                    (Decimal(site_expats) / Decimal(workforce) * 100).quantize(Decimal("0.01"))
                    if workforce > 0 else Decimal("0.00")
                )
                max_allowed = self.max_expats_for(site_congolese)
            else:
                pct = Decimal("0.00")
                max_allowed = 0

            sites.append(SiteQuota(
                site_id=str(site.id),
                site_name=site.name,
                congolese_count=site_congolese,
                expatriate_count=site_expats,
                sector_pct=pct,
                max_allowed=max_allowed,
                headroom=max(0, max_allowed - site_expats),
                is_compliant=pct <= SECTOR_QUOTA_PCT,
                risk_level=self.classify(pct),
            ))
        return sites