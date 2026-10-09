from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Immutable Audit Log"

    def ready(self):
        from . import signals  # noqa: F401
        self._register_business_models()

    def _register_business_models(self):
        """Defensively register each model so one bad import won't crash the server."""
        import logging
        from auditlog.registry import auditlog

        logger = logging.getLogger(__name__)
        candidates = []

        # ─── Experts ─────────────────────────────────────────
        try:
            from apps.experts.models import ExpertProfile
            candidates.append(("experts.ExpertProfile", ExpertProfile))
        except Exception as e:
            logger.warning(f"Skip ExpertProfile: {e}")

        # ─── Legacy visa models ─────────────────────────────
        try:
            from apps.visas.models import (
                CarteDeTravail, FlyingVisa, AirportVisa,
                VoyageVisa, EstablishmentVisa,
            )
            candidates += [
                ("visas.CarteDeTravail", CarteDeTravail),
                ("visas.FlyingVisa", FlyingVisa),
                ("visas.AirportVisa", AirportVisa),
                ("visas.VoyageVisa", VoyageVisa),
                ("visas.EstablishmentVisa", EstablishmentVisa),
            ]
        except Exception as e:
            logger.warning(f"Skip legacy visa models: {e}")

        # ─── New visa models ────────────────────────────────
        try:
            from apps.visas.models import (
                VisaTypeCatalog, VisaRecord, VisaProlongation,
            )
            candidates += [
                ("visas.VisaTypeCatalog", VisaTypeCatalog),
                ("visas.VisaRecord", VisaRecord),
                ("visas.VisaProlongation", VisaProlongation),
            ]
        except Exception as e:
            logger.warning(f"Skip new visa models: {e}")

        # ─── Compliance ─────────────────────────────────────
        try:
            from apps.compliance.models import (
                PenaltyLedger, ExpertCost, MonthlyInvoice, CostCategory,
            )
            candidates += [
                ("compliance.PenaltyLedger", PenaltyLedger),
                ("compliance.ExpertCost", ExpertCost),
                ("compliance.MonthlyInvoice", MonthlyInvoice),
                ("compliance.CostCategory", CostCategory),
            ]
        except Exception as e:
            logger.warning(f"Skip compliance models: {e}")

        # ─── Organization (UserCompanyMembership intentionally skipped) ───
        try:
            from apps.organization.models import Company, Site, Department
            candidates += [
                ("organization.Company", Company),
                ("organization.Site", Site),
                ("organization.Department", Department),
            ]
        except Exception as e:
            logger.warning(f"Skip organization models: {e}")

        # ─── Register each ──────────────────────────────────
        for label, model in candidates:
            try:
                if hasattr(model, "_meta") and (
                    model._meta.abstract or model._meta.swapped
                ):
                    continue
                auditlog.register(model)
            except Exception as e:
                logger.warning(f"Skip {label}: {e}")