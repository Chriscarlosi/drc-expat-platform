"""Public-facing frontend views."""
import json
import logging
import csv
import io
import base64
import qrcode
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib import messages
from django.views.generic import CreateView, TemplateView, UpdateView
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.models import User

from apps.travel.models import CharterFlight, CharterPassenger
from apps.travel.services import ManifestValidator  # NEW IMPORT
from apps.audit.models import ImmutableAuditLog
from apps.experts.models import ExpertProfile, Dependant
from apps.experts.forms import DependantForm, ExpertProfileForm
from apps.visas.models import CarteDeTravail, VisaProlongation, VisaRecord, VisaTypeCatalog
from apps.visas.forms import VisaProlongationForm
from apps.compliance.models import PenaltyLedger
from apps.organization.models import Company, UserCompanyMembership, WorkforceSnapshot
from apps.organization.forms import WorkforceSnapshotForm
from apps.documents.models import DocumentVersion
from .forms import CSVImportForm, InviteUserForm, UserProfileForm, CustomPasswordChangeForm
from .models import InspectionSession, InspectionAuditLog

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# PUBLIC
# ═══════════════════════════════════════════════════════════════

def landing(request):
    """Public landing page."""
    context = {
        "visa_count": VisaTypeCatalog.objects.filter(is_active=True).count(),
    }
    return render(request, "frontend/landing.html", context)


# ═══════════════════════════════════════════════════════════════
# EXECUTIVE DASHBOARD (with role routing)
# ═══════════════════════════════════════════════════════════════

@login_required
def executive_dashboard(request):
    """Route by role, then render the Executive / GM view for EXECUTIVE + VIEWER."""
    from apps.compliance.views import compute_risk_score, _risk_label as get_risk_label

    today = timezone.now().date()
    t90 = today + timedelta(days=90)
    t30 = today + timedelta(days=30)
    t60 = today + timedelta(days=60)

    membership = (
        UserCompanyMembership.objects
        .filter(user=request.user, is_active=True)
        .select_related("company")
        .first()
    )

    if membership:
        role = membership.role
        if role == UserCompanyMembership.Role.EXPERT:
            return redirect("/my-portal/")
        if role in (
                UserCompanyMembership.Role.ADMIN,
                UserCompanyMembership.Role.OWNER,
                UserCompanyMembership.Role.HR_MANAGER,
                UserCompanyMembership.Role.DEPARTMENT_MANAGER,
                UserCompanyMembership.Role.SITE_MANAGER,
        ):
            return redirect("/admin/")
        company = membership.company
    else:
        company = Company.objects.filter(is_active=True).first()

    if not company:
        return redirect("/admin/")

    qs = ExpertProfile.objects.unscoped().filter(company=company, is_active=True)

    total_experts = qs.count()
    expat_count = qs.filter(is_expatriate=True).count()

    # ── Workforce snapshot (auditable, historical) ────────────
    snapshot = company.workforce_snapshots.first()
    workforce_data_complete = bool(snapshot and not snapshot.is_stale)

    if snapshot:
        congolese_count = snapshot.total_congolese_staff
        expat_count_from_snapshot = snapshot.total_expat_staff
    else:
        congolese_count = 0
        expat_count_from_snapshot = expat_count

    total_workforce = congolese_count + expat_count_from_snapshot
    quota_pct = round(expat_count_from_snapshot / total_workforce * 100, 2) if total_workforce > 0 else 0.0
    quota_cap = getattr(settings, 'DRC_EXPAT_QUOTA_CAP', 6.5)
    quota_compliant = (not workforce_data_complete) or (quota_pct <= quota_cap)
    quota_breached = workforce_data_complete and (quota_pct > quota_cap)

    if congolese_count > 0:
        max_allowed = int(congolese_count * quota_cap / (100 - quota_cap))
        quota_headroom = max(0, max_allowed - expat_count_from_snapshot)
    else:
        quota_headroom = 0

    # ── Documents ─────────────────────────────────────────────
    passports_expiring = qs.filter(passport_expiry_date__gte=today, passport_expiry_date__lte=t90).count()
    passports_expired = qs.filter(passport_expiry_date__lt=today).count()
    cartes_expiring = CarteDeTravail.objects.filter(expert__company=company, is_active=True, expiry_date__gte=today,
                                                    expiry_date__lte=t90).count()
    cartes_expired = CarteDeTravail.objects.filter(expert__company=company, is_active=True,
                                                   expiry_date__lt=today).count()
    yellow_fever_expired = qs.filter(yellow_fever_expiry_date__lt=today, yellow_fever_expiry_date__isnull=False).count()

    passports_t30 = qs.filter(passport_expiry_date__gte=today, passport_expiry_date__lte=t30).count()
    passports_t60 = qs.filter(passport_expiry_date__gt=t30, passport_expiry_date__lte=t60).count()
    passports_t90 = qs.filter(passport_expiry_date__gt=t60, passport_expiry_date__lte=t90).count()

    penalties = PenaltyLedger.objects.filter(expert__company=company, resolved=False)
    penalty_total = sum(p.total_amount_usd for p in penalties)
    penalty_count = penalties.count()

    # ── Travel Stats ──────────────────────────────────────────
    upcoming_flights_count = CharterFlight.objects.filter(departure_datetime__date__gte=today).count()

    # ── Risk score ────────────────────────────────────────────
    risk = compute_risk_score(
        passports_expired=passports_expired,
        cartes_expired=cartes_expired,
        yellow_fever_expired=yellow_fever_expired,
        passports_t30=passports_t30,
        passports_t60=passports_t60,
        passports_t90=passports_t90,
        cartes_t30=0,
        cartes_t90=0,
        visas_t30=0,
        visas_t90=0,
        unresolved_penalties=penalty_count,
        quota_breached=quota_breached,
        workforce_data_complete=workforce_data_complete,
    )

    risk_label, risk_color = get_risk_label(risk['score'])

    if workforce_data_complete:
        display_score = risk['score']
        display_label = risk_label
        display_color = risk_color
    else:
        display_score = "—"
        display_label = "PENDING DATA"
        display_color = "#F59E0B"

    recent_penalties = list(penalties.order_by("-accrual_start_date")[:5])
    expiring_list = list(
        qs.filter(passport_expiry_date__gte=today, passport_expiry_date__lte=t90)
        .order_by("passport_expiry_date")[:5]
    )
    for e in expiring_list:
        e.days_left = (e.passport_expiry_date - today).days

    context = {
        "today": today,
        "company": company,
        "scope_label": company.name,
        "total_experts": total_experts,
        "expat_count": expat_count_from_snapshot,
        "congolese_count": congolese_count,
        "total_workforce": total_workforce,
        "quota_pct": quota_pct,
        "quota_cap": quota_cap,
        "quota_compliant": quota_compliant,
        "quota_breached": quota_breached,
        "quota_headroom": quota_headroom,
        "workforce_data_complete": workforce_data_complete,
        "workforce_snapshot": snapshot,
        "workforce_warning": (
            "Workforce data incomplete. The quota hard cap was NOT applied. "
            "Please record a workforce snapshot."
        ) if not workforce_data_complete else None,
        "passports_expiring": passports_expiring,
        "cartes_expiring": cartes_expiring,
        "critical_count": passports_t30,
        "penalty_total": float(penalty_total),
        "penalty_count": penalty_count,
        "upcoming_flights_count": upcoming_flights_count,
        "compliance_score": display_score,
        "risk_label": display_label,
        "risk_color": display_color,
        "risk_ceiling": risk['ceiling'],
        "risk_hard_caps": risk['hard_caps'],
        "risk_soft_deductions": risk['soft_deductions'],
        "recent_penalties": recent_penalties,
        "expiring_list": expiring_list,
    }
    return render(request, "frontend/executive_dashboard.html", context)


# ═══════════════════════════════════════════════════════════════
# EXPERT SELF-SERVICE PORTAL
# ═══════════════════════════════════════════════════════════════

@login_required
def expert_portal(request):
    """Expert self-service portal — mobile-first, own data only."""
    today = timezone.now().date()

    expert = getattr(request.user, "expert_profile", None)

    if not expert:
        membership = (
            UserCompanyMembership.objects
            .filter(user=request.user, is_active=True)
            .select_related("expert_profile")
            .first()
        )
        expert = membership.expert_profile if membership else None

    if not expert:
        return render(request, "frontend/expert_portal_no_profile.html")

    carte = (
        CarteDeTravail.objects
        .filter(expert=expert, is_active=True)
        .order_by("-expiry_date")
        .first()
    )

    dependants = list(expert.expert_family_members.all())

    upcoming_flights = (
        CharterPassenger.objects
        .filter(expert=expert, flight__departure_datetime__date__gte=today)
        .select_related("flight", "flight__route", "flight__operator")
        .order_by("flight__departure_datetime")[:5]
    )

    passport_days = (expert.passport_expiry_date - today).days if expert.passport_expiry_date else None
    yf_days = (expert.yellow_fever_expiry_date - today).days if expert.yellow_fever_expiry_date else None
    carte_days = (carte.expiry_date - today).days if carte else None

    days = [d for d in [passport_days, yf_days, carte_days] if d is not None]
    min_days = min(days) if days else None

    if min_days is None:
        status_label = "INCOMPLETE"
        status_color = "#64748B"
    elif min_days < 0:
        status_label = "EXPIRED"
        status_color = "#DC2626"
    elif min_days < 30:
        status_label = "CRITICAL"
        status_color = "#EA580C"
    elif min_days < 90:
        status_label = "ATTENTION"
        status_color = "#F59E0B"
    else:
        status_label = "COMPLIANT"
        status_color = "#16A34A"

    context = {
        "today": today,
        "expert": expert,
        "carte": carte,
        "dependants": dependants,
        "upcoming_flights": upcoming_flights,
        "passport_days": passport_days,
        "yf_days": yf_days,
        "carte_days": carte_days,
        "status_label": status_label,
        "status_color": status_color,
    }
    return render(request, "frontend/expert_portal.html", context)


def login_view(request):
    """Handle login and route staff to the hidden backend, others to frontend."""
    if request.user.is_authenticated:
        # If already logged in, route staff to admin, others to dashboard
        if request.user.is_staff or request.user.is_superuser:
            return redirect("/control-tower-x9/")
        return redirect("/dashboard/")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)

            # Route staff to the hidden admin URL
            if user.is_staff or user.is_superuser:
                return redirect("/control-tower-x9/")

            next_url = request.GET.get("next") or "/dashboard/"
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "frontend/login.html")


def logout_view(request):
    auth_logout(request)
    return redirect("/")


# ═══════════════════════════════════════════════════════════════
# PROLONGATION WORKFLOW
# ═══════════════════════════════════════════════════════════════

class ProlongationRequestView(LoginRequiredMixin, CreateView):
    model = VisaProlongation
    form_class = VisaProlongationForm
    template_name = 'frontend/prolongation_form.html'
    success_url = reverse_lazy('frontend:prolongation_success')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notice_days'] = getattr(settings, 'VISA_PROLONGATION_NOTICE_DAYS', 30)
        context['notice_verified'] = getattr(settings, 'VISA_PROLONGATION_NOTICE_VERIFIED', False)

        membership = getattr(self.request.user, 'membership', None)
        if membership:
            company = membership.company
        else:
            company = Company.objects.filter(is_active=True).first()

        context['company'] = company
        context['scope_label'] = company.name if company else "All Companies"

        prolongation_types = VisaTypeCatalog.objects.filter(category=VisaTypeCatalog.Category.PROLONGATION,
                                                            is_active=True)
        rules = {str(p.id): p.extension_length_days for p in prolongation_types if p.extension_length_days}
        context['catalog_rules_json'] = json.dumps(rules)

        return context

    def form_valid(self, form):
        form.instance.status = VisaProlongation.Status.REQUESTED
        form.instance.submitted_by = self.request.user
        if form.instance.parent_visa:
            form.instance.expert = form.instance.parent_visa.expert

        response = super().form_valid(form)

        try:
            ImmutableAuditLog.objects.create(
                user_repr=self.request.user.username,
                action="PROLONGATION_REQUESTED",
                model_name="VisaProlongation",
                object_repr=f"Prolongation {form.instance.prolongation_number} for {form.instance.expert.full_name}",
                changes={
                    "info": f"Requested prolongation of type {form.instance.prolongation_type.code}. New expiry: {form.instance.new_expiry_date}."}
            )
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

        return response


class ProlongationSuccessView(TemplateView):
    template_name = 'frontend/prolongation_success.html'


# ═══════════════════════════════════════════════════════════════
# EXPERT PROFILE & DEPENDANTS
# ═══════════════════════════════════════════════════════════════

@login_required
def expert_profile_view(request, expert_id):
    expert = get_object_or_404(ExpertProfile, id=expert_id)
    visas = expert.visa_records.all().order_by('-issue_date')
    cartes = expert.cartes_de_travail.all().order_by('-issue_date')
    dependants = expert.expert_family_members.all()

    context = {
        "expert": expert,
        "visas": visas,
        "cartes": cartes,
        "dependants": dependants,
        "scope_label": expert.company.name if expert.company else "All Companies",
    }
    return render(request, "frontend/expert_profile.html", context)


@login_required
def expert_dependants(request, expert_id):
    expert = get_object_or_404(ExpertProfile, id=expert_id)
    dependants = expert.expert_family_members.all()

    context = {
        "expert": expert,
        "dependants": dependants,
        "scope_label": expert.company.name if expert.company else "All Companies",
    }
    return render(request, "frontend/dependants.html", context)


class DependantCreateView(LoginRequiredMixin, CreateView):
    model = Dependant
    form_class = DependantForm
    template_name = 'frontend/dependant_form.html'

    def form_valid(self, form):
        expert_id = self.kwargs.get('expert_id')
        expert = get_object_or_404(ExpertProfile, id=expert_id)
        form.instance.expert = expert
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('frontend:expert_dependants', kwargs={'expert_id': self.kwargs.get('expert_id')})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expert'] = get_object_or_404(ExpertProfile, id=self.kwargs.get('expert_id'))
        return context


# ═══════════════════════════════════════════════════════════════
# REPORTS & SETTINGS
# ═══════════════════════════════════════════════════════════════

@login_required
def reports_dashboard(request):
    membership = getattr(request.user, 'membership', None)
    company = membership.company if membership else None

    context = {
        "company": company,
        "scope_label": company.name if company else "All Companies",
    }
    return render(request, "frontend/reports.html", context)


@login_required
def settings_dashboard(request):
    membership = getattr(request.user, 'membership', None)

    if membership:
        company = membership.company
    else:
        company = Company.objects.filter(is_active=True).first()

    team_members = []
    if company:
        team_members = UserCompanyMembership.objects.filter(
            company=company,
            is_active=True
        ).select_related('user').order_by('user__first_name')

    context = {
        "company": company,
        "scope_label": company.name if company else "All Companies",
        "team_members": team_members,
    }
    return render(request, "frontend/settings.html", context)


@login_required
def invite_user(request):
    """Frontend view to invite a new team member."""
    membership = getattr(request.user, 'membership', None)
    if not membership or membership.role not in ['OWNER', 'ADMIN', 'HR_MANAGER']:
        messages.error(request, "You do not have permission to invite users.")
        return redirect('frontend:settings')

    company = membership.company

    if request.method == 'POST':
        form = InviteUserForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            if User.objects.filter(email=email).exists():
                messages.error(request, "A user with this email already exists.")
            elif UserCompanyMembership.objects.filter(user__email=email, company=company).exists():
                messages.error(request, "This user is already a member of your company.")
            else:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    password=None
                )
                user.set_unusable_password()
                user.save()

                UserCompanyMembership.objects.create(
                    user=user,
                    company=company,
                    role=form.cleaned_data['role'],
                    is_active=True
                )

                ImmutableAuditLog.objects.create(
                    user_repr=request.user.username,
                    action="USER_INVITED",
                    model_name="UserCompanyMembership",
                    object_repr=f"User {email}",
                    changes={"info": f"Invited {email} with role {form.cleaned_data['role']}."}
                )

                messages.success(request, f"Invitation created for {email}. They will receive an email shortly.")
                return redirect('frontend:settings')
    else:
        form = InviteUserForm()

    return render(request, 'frontend/invite_user.html', {'form': form, 'company': company})


@login_required
def profile_view(request):
    """Handle user profile updates and password changes."""
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect('frontend:profile')
        elif 'change_password' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect('frontend:profile')
    else:
        profile_form = UserProfileForm(instance=request.user)
        password_form = CustomPasswordChangeForm(request.user)

    context = {
        'profile_form': profile_form,
        "password_form": password_form,
        "company": getattr(request.user, 'membership', None).company if getattr(request.user, 'membership',
                                                                                None) else None,
    }
    return render(request, 'frontend/profile.html', context)


# ═══════════════════════════════════════════════════════════════
# TRUST & LEGAL PAGES
# ═══════════════════════════════════════════════════════════════

def security(request):
    return render(request, "frontend/security.html")


def privacy(request):
    return render(request, "frontend/privacy.html")


def terms(request):
    return render(request, "frontend/terms.html")


# ═══════════════════════════════════════════════════════════════
# MARKETING PAGES
# ═══════════════════════════════════════════════════════════════

def features(request):
    return render(request, "frontend/features.html")


def modules(request):
    return render(request, "frontend/modules.html")


def pricing(request):
    return render(request, "frontend/pricing.html")


def contact(request):
    from .models import ContactMessage

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        company = request.POST.get("company", "").strip()
        phone = request.POST.get("phone", "").strip()
        role = request.POST.get("role", "").strip()
        message = request.POST.get("message", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not email or "@" not in email:
            errors.append("Valid email is required.")
        if not message or len(message) < 10:
            errors.append("Message must be at least 10 characters.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            ContactMessage.objects.create(
                name=name,
                email=email,
                company=company,
                phone=phone,
                role=role,
                message=message,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )
            messages.success(
                request,
                "Thank you. Your message has been received. "
                "Our team will respond within 24 hours."
            )
            return redirect("/contact/")

    return render(request, "frontend/contact.html")


# ═══════════════════════════════════════════════════════════════
# BULK IMPORTS & WORKFORCE SNAPSHOTS
# ═══════════════════════════════════════════════════════════════

@login_required
def import_experts_csv(request):
    """Handles the CSV upload and processes the experts."""
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']

            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a valid CSV file.')
                return redirect('frontend:settings')

            try:
                data_set = csv_file.read().decode('UTF-8')
            except UnicodeDecodeError:
                messages.error(request, 'File encoding error. Please save as UTF-8 CSV.')
                return redirect('frontend:settings')

            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)

            company = getattr(request.user, 'membership', None).company if getattr(request.user, 'membership',
                                                                                   None) else Company.objects.filter(
                is_active=True).first()

            created_count = 0
            skipped_count = 0

            with transaction.atomic():
                for row in reader:
                    if ExpertProfile.objects.filter(passport_number=row.get('passport_number')).exists():
                        skipped_count += 1
                        continue

                    try:
                        from django.utils.dateparse import parse_date

                        ExpertProfile.objects.create(
                            company=company,
                            first_name=row.get('first_name', 'Unknown'),
                            last_name=row.get('last_name', 'Unknown'),
                            date_of_birth=parse_date(row.get('date_of_birth')) or timezone.now().date(),
                            gender=row.get('gender', 'M'),
                            nationality=row.get('nationality', 'Unknown'),
                            passport_number=row.get('passport_number', 'MISSING'),
                            passport_issue_date=parse_date(row.get('passport_issue_date')) or timezone.now().date(),
                            passport_expiry_date=parse_date(row.get('passport_expiry_date')) or timezone.now().date(),
                            employer_company=row.get('employer_company', company.name if company else 'Unknown'),
                            job_title=row.get('job_title', 'Engineer'),
                            email=row.get('email', 'no-email@example.com'),
                            is_expatriate=True,
                            is_active=True
                        )
                        created_count += 1
                    except Exception as e:
                        skipped_count += 1
                        logger.error(f"CSV Import error on {row.get('first_name')}: {e}")

            ImmutableAuditLog.objects.create(
                user_repr=request.user.username,
                action="CSV_IMPORT",
                model_name="ExpertProfile",
                object_repr="Bulk Expert Import",
                changes={"info": f"Imported {created_count} experts. Skipped {skipped_count}."}
            )

            messages.success(request,
                             f'Successfully imported {created_count} experts. ({skipped_count} skipped/duplicates).')
            return redirect('frontend:settings')
    else:
        return redirect('frontend:settings')


@login_required
def add_workforce_snapshot(request):
    """Frontend view for HR to record a workforce snapshot."""
    membership = getattr(request.user, 'membership', None)
    company = membership.company if membership else Company.objects.filter(is_active=True).first()

    if request.method == 'POST':
        form = WorkforceSnapshotForm(request.POST, request.FILES)
        if form.is_valid():
            snapshot = form.save(commit=False)
            snapshot.company = company
            snapshot.created_by = request.user
            snapshot.save()

            ImmutableAuditLog.objects.create(
                user_repr=request.user.username,
                action="WORKFORCE_SNAPSHOT_CREATED",
                model_name="WorkforceSnapshot",
                object_repr=f"Snapshot for {company.name} on {snapshot.snapshot_date}",
                changes={
                    "info": f"Recorded workforce data: {snapshot.total_expat_staff} expats, {snapshot.total_congolese_staff} Congolese."}
            )

            messages.success(request, "Workforce snapshot saved successfully. Dashboard updated.")
            return redirect('frontend:executive_dashboard')
    else:
        form = WorkforceSnapshotForm()

    return render(request, 'frontend/add_snapshot.html', {'form': form, 'company': company})


# ═══════════════════════════════════════════════════════════════
# LISTS (VISAS, EXPERTS, PENALTIES, DOCUMENTS)
# ═══════════════════════════════════════════════════════════════

@login_required
def visa_records_list(request):
    """Frontend list view for Visa Records."""
    membership = getattr(request.user, 'membership', None)
    company = membership.company if membership else Company.objects.filter(is_active=True).first()

    visas = VisaRecord.objects.filter(expert__company=company).select_related('expert', 'visa_type').order_by(
        '-expiry_date')

    query = request.GET.get('q')
    if query:
        visas = visas.filter(Q(expert__first_name__icontains=query) | Q(expert__last_name__icontains=query) | Q(
            visa_number__icontains=query))

    status_filter = request.GET.get('status')
    if status_filter:
        visas = visas.filter(status=status_filter)

    context = {
        "visas": visas,
        "scope_label": company.name if company else "All Companies",
        "today": timezone.now().date(),
        "status_choices": VisaRecord.Status.choices,
    }
    return render(request, "frontend/visa_list.html", context)


@login_required
def expert_list(request):
    """Frontend list view for Experts."""
    membership = getattr(request.user, 'membership', None)
    company = membership.company if membership else Company.objects.filter(is_active=True).first()

    if request.user.is_superuser:
        experts = ExpertProfile.objects.unscoped().all()
    else:
        experts = ExpertProfile.objects.unscoped().filter(company=company)

    experts = experts.order_by('last_name', 'first_name')

    query = request.GET.get('q')
    if query:
        experts = experts.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(passport_number__icontains=query) |
            Q(email__icontains=query)
        )

    status_filter = request.GET.get('status')
    if status_filter == 'active':
        experts = experts.filter(is_active=True)
    elif status_filter == 'inactive':
        experts = experts.filter(is_active=False)

    context = {
        "experts": experts,
        "scope_label": company.name if company else "All Companies",
        "today": timezone.now().date(),
    }
    return render(request, "frontend/expert_list.html", context)


@login_required
def penalty_list(request):
    """Frontend list view for Penalties."""
    membership = getattr(request.user, 'membership', None)
    company = membership.company if membership else Company.objects.filter(is_active=True).first()

    if request.user.is_superuser:
        penalties = PenaltyLedger.objects.all().select_related('expert')
    else:
        penalties = PenaltyLedger.objects.filter(expert__company=company).select_related('expert')

    penalties = penalties.order_by('-accrual_start_date')

    query = request.GET.get('q')
    if query:
        penalties = penalties.filter(
            Q(expert__first_name__icontains=query) |
            Q(expert__last_name__icontains=query)
        )

    status_filter = request.GET.get('status')
    if status_filter == 'resolved':
        penalties = penalties.filter(resolved=True)
    elif status_filter == 'unresolved':
        penalties = penalties.filter(resolved=False)

    context = {
        "penalties": penalties,
        "scope_label": company.name if company else "All Companies",
        "today": timezone.now().date(),
    }
    return render(request, "frontend/penalty_list.html", context)


@login_required
def resolve_penalty(request, penalty_id):
    """Action to mark a penalty as resolved."""
    if request.method == 'POST':
        penalty = get_object_or_404(PenaltyLedger, id=penalty_id)
        if not request.user.is_superuser and penalty.expert.company != getattr(request.user, 'membership',
                                                                               None).company:
            messages.error(request, "Permission denied.")
            return redirect('frontend:penalty_list')

        penalty.resolved = True
        penalty.resolution_date = timezone.now().date()
        penalty.resolution_notes = f"Resolved by {request.user.username} via frontend."
        penalty.save()

        ImmutableAuditLog.objects.create(
            user_repr=request.user.username,
            action="PENALTY_RESOLVED",
            model_name="PenaltyLedger",
            object_repr=f"Penalty for {penalty.expert.full_name}",
            changes={"info": f"Marked penalty of ${penalty.total_amount_usd} as resolved."}
        )

        messages.success(request, f"Penalty for {penalty.expert.full_name} marked as resolved.")
    return redirect('frontend:penalty_list')


@login_required
def document_list(request):
    """Frontend list view for all uploaded documents."""
    membership = getattr(request.user, 'membership', None)
    company = membership.company if membership else Company.objects.filter(is_active=True).first()

    documents = DocumentVersion.objects.all().order_by('-uploaded_at')

    query = request.GET.get('q')
    if query:
        documents = documents.filter(
            Q(original_filename__icontains=query) |
            Q(uploaded_by_repr__icontains=query)
        )

    context = {
        "documents": documents,
        "scope_label": company.name if company else "All Companies",
    }
    return render(request, "frontend/document_list.html", context)


class ExpertCreateView(LoginRequiredMixin, CreateView):
    model = ExpertProfile
    form_class = ExpertProfileForm
    template_name = 'frontend/expert_form.html'
    success_url = reverse_lazy('frontend:expert_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        membership = getattr(self.request.user, 'membership', None)
        company = membership.company if membership else Company.objects.filter(is_active=True).first()
        kwargs['company'] = company
        return kwargs

    def form_valid(self, form):
        membership = getattr(self.request.user, 'membership', None)
        company = membership.company if membership else Company.objects.filter(is_active=True).first()

        form.instance.company = company
        form.instance.is_active = True
        form.instance.is_expatriate = True

        response = super().form_valid(form)

        ImmutableAuditLog.objects.create(
            user_repr=self.request.user.username,
            action="EXPERT_CREATED",
            model_name="ExpertProfile",
            object_repr=f"Expert {form.instance.full_name}",
            changes={"info": f"Created new expert profile for {form.instance.full_name} ({form.instance.nationality})."}
        )

        messages.success(self.request, f"Expert {form.instance.full_name} created successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership = getattr(self.request.user, 'membership', None)
        context['company'] = membership.company if membership else Company.objects.filter(is_active=True).first()
        return context


class ExpertUpdateView(LoginRequiredMixin, UpdateView):
    model = ExpertProfile
    form_class = ExpertProfileForm
    template_name = 'frontend/expert_form.html'
    success_url = reverse_lazy('frontend:expert_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        membership = getattr(self.request.user, 'membership', None)
        company = membership.company if membership else Company.objects.filter(is_active=True).first()
        kwargs['company'] = company
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Expert {form.instance.full_name} updated successfully.")
        return response


# ═══════════════════════════════════════════════════════════════
# TRAVEL & CHARTER
# ═══════════════════════════════════════════════════════════════

@login_required
def travel_dashboard(request):
    """Premium frontend dashboard for Travel & Charter."""
    today = timezone.now().date()

    upcoming_flights = CharterFlight.objects.filter(
        departure_datetime__date__gte=today
    ).select_related('route', 'aircraft', 'operator').order_by('departure_datetime')[:10]

    total_upcoming = CharterFlight.objects.filter(departure_datetime__date__gte=today).count()
    total_passengers = CharterPassenger.objects.filter(flight__departure_datetime__date__gte=today).count()

    context = {
        "upcoming_flights": upcoming_flights,
        "total_upcoming": total_upcoming,
        "total_passengers": total_passengers,
        "scope_label": getattr(request.user, 'membership', None).company.name if getattr(request.user, 'membership',
                                                                                         None) else "All Companies",
    }
    return render(request, "frontend/travel_dashboard.html", context)


@login_required
def flight_manifest(request, flight_id):
    """Printable DGM Manifest for a specific flight."""
    flight = get_object_or_404(CharterFlight, id=flight_id)
    passengers = CharterPassenger.objects.filter(flight=flight).select_related('expert', 'dependant')

    # 1. Run the validation engine for the red/amber warning banners
    validator = ManifestValidator(flight)
    errors, warnings = validator.validate()

    # 2. Generate the QR Code if the manifest is locked/submitted
    qr_code_url = None
    if flight.manifest_hash:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        # This URL should point to a public verification page you build later
        verify_url = request.build_absolute_uri(f"/verify/{flight.manifest_hash}/")
        qr.add_data(verify_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0f172a", back_color="white")

        # Convert image to base64 string for the HTML template
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_url = base64.b64encode(buffer.getvalue()).decode()

    context = {
        "flight": flight,
        "passengers": passengers,
        "today": timezone.now().date(),
        "validation_errors": errors,
        "validation_warnings": warnings,
        "qr_code_url": qr_code_url,
    }
    return render(request, "frontend/flight_manifest.html", context)


# ═══════════════════════════════════════════════════════════════
# DGM INSPECTION MODE (Tablet-optimized, PIN protected)
# ═══════════════════════════════════════════════════════════════

@login_required
def inspection_mode(request):
    """DGM Inspection Mode — DB-backed sessions and PII masking."""
    today = timezone.now().date()
    now = timezone.now()

    # 1. Check for existing active session
    session_id = request.session.get("inspection_session_id")
    insp_session = None

    if session_id:
        insp_session = InspectionSession.objects.filter(id=session_id).first()
        if not insp_session or not insp_session.is_active:
            del request.session["inspection_session_id"]
            insp_session = None
            messages.warning(request, "Inspection session expired.")

    # 2. Handle PIN submission
    if not insp_session:
        if request.method == "POST":
            pin = request.POST.get("pin")
            inspector_name = request.POST.get("inspector_name", "").strip()
            inspector_id = request.POST.get("inspector_id", "").strip()

            if pin == "1234" and inspector_name and inspector_id:
                # Create a 1-hour session
                insp_session = InspectionSession.objects.create(
                    inspector_name=inspector_name,
                    inspector_id=inspector_id,
                    company=request.user.company_memberships.first().company,  # Or fallback
                    expires_at=now + timedelta(hours=1),
                    ip_address=request.META.get("REMOTE_ADDR")
                )
                request.session["inspection_session_id"] = insp_session.id
                return redirect("/inspection/")
            else:
                messages.error(request, "Invalid PIN or missing Inspector details.")

        return render(request, "frontend/inspection_pin.html")

    # 3. Authorized — Fetch Data
    company = insp_session.company
    experts = ExpertProfile.objects.unscoped().filter(
        company=company, is_active=True
    ).select_related("department").order_by("last_name")

    for e in experts:
        e.passport_valid = e.passport_expiry_date and e.passport_expiry_date >= today
        carte = CarteDeTravail.objects.filter(expert=e, is_active=True).order_by("-expiry_date").first()
        e.carte_valid = carte and carte.expiry_date >= today
        from apps.visas.models import VisaRecord
        visa = VisaRecord.objects.filter(expert=e).order_by("-expiry_date").first()
        e.visa_valid = visa and visa.expiry_date >= today

    # Calculate time remaining
    minutes_left = int((insp_session.expires_at - now).total_seconds() / 60)

    return render(request, "frontend/inspection_mode.html", {
        "experts": experts,
        "insp_session": insp_session,
        "company": company,
        "today": today,
        "minutes_left": minutes_left,
    })


@login_required
def reveal_passport(request, expert_id):
    """AJAX endpoint to reveal masked passport and log the action."""
    session_id = request.session.get("inspection_session_id")
    if not session_id:
        return JsonResponse({"error": "No active session"}, status=403)

    insp_session = InspectionSession.objects.filter(id=session_id).first()
    if not insp_session or not insp_session.is_active:
        return JsonResponse({"error": "Session expired"}, status=403)

    try:
        expert = ExpertProfile.objects.unscoped().get(id=expert_id, company=insp_session.company)

        # Log the reveal
        InspectionAuditLog.objects.create(
            session=insp_session,
            expert=expert,
            action="REVEAL_PASSPORT"
        )

        return JsonResponse({"status": "ok", "passport": expert.passport_number})
    except ExpertProfile.DoesNotExist:
        return JsonResponse({"error": "Expert not found"}, status=404)


@login_required
def inspection_logout(request):
    """Clear the session."""
    if "inspection_session_id" in request.session:
        del request.session["inspection_session_id"]
    return redirect("/dashboard/")


@login_required
def inspection_logout(request):
    """Clear the DGM PIN session."""
    if "inspection_authorized" in request.session:
        del request.session["inspection_authorized"]
    return redirect("/dashboard/")


# ═══════════════════════════════════════════════════════════════
# QUOTA SIMULATOR
# ═══════════════════════════════════════════════════════════════

@login_required
def quota_simulator(request):
    """A sandbox calculator for HR to simulate workforce changes."""
    company = getattr(request, "active_company", None)
    if not company:
        company = Company.objects.filter(is_active=True).first()

    if not company:
        return redirect("/admin/")

    # Get current baselines
    qs = ExpertProfile.objects.unscoped().filter(company=company, is_active=True)
    current_expat_count = qs.filter(is_expatriate=True).count()
    current_congolese_count = company.congolese_staff_count or 0

    context = {
        "company": company,
        "current_expat_count": current_expat_count,
        "current_congolese_count": current_congolese_count,
        "quota_cap": 6.5,
    }
    return render(request, "frontend/quota_simulator.html", context)


# ═══════════════════════════════════════════════════════════════
# MANIFEST WORKFLOW & VERIFICATION
# ═══════════════════════════════════════════════════════════════

@login_required
def submit_manifest(request, flight_id):
    """Locks the manifest, generates the hash, and sets status to SUBMITTED."""
    flight = get_object_or_404(CharterFlight, id=flight_id)

    # 1. Check permissions (Only HR or Admins can submit)
    membership = getattr(request.user, 'membership', None)
    if not membership or membership.role not in ['OWNER', 'ADMIN', 'HR_MANAGER']:
        messages.error(request, "You do not have permission to submit manifests.")
        return redirect('frontend:flight_manifest', flight_id=flight.id)

    if request.method == 'POST':
        # 2. Run validation one last time before locking
        from apps.travel.services import ManifestValidator
        validator = ManifestValidator(flight)
        errors, warnings = validator.validate()

        # Check if they are overriding
        override_reason = request.POST.get('override_reason', '').strip()

        if errors and not override_reason:
            messages.error(request, "Cannot submit: Please fix the validation errors or provide an override reason.")
            return redirect('frontend:flight_manifest', flight_id=flight.id)

        # 3. Lock the manifest
        flight.manifest_status = CharterFlight.ManifestStatus.SUBMITTED
        flight.locked_at = timezone.now()
        flight.save()  # The save() method automatically generates the SHA-256 hash!

        # 4. Log the action in the immutable audit trail
        ImmutableAuditLog.objects.create(
            user_repr=request.user.username,
            action="MANIFEST_SUBMITTED",
            model_name="CharterFlight",
            object_repr=f"Manifest {flight.flight_number}",
            changes={
                "info": f"Submitted to DGM. Hash: {flight.manifest_hash}. Override Reason: {override_reason or 'None'}"}
        )

        messages.success(request, "Manifest successfully submitted to DGM and locked.")
        return redirect('frontend:flight_manifest', flight_id=flight.id)

    return redirect('frontend:flight_manifest', flight_id=flight.id)


def verify_manifest(request, manifest_hash):
    """Public page accessed via QR code to verify document authenticity."""
    flight = CharterFlight.objects.filter(manifest_hash=manifest_hash).first()

    is_valid = flight is not None

    context = {
        "is_valid": is_valid,
        "flight": flight,
        "scanned_hash": manifest_hash,
    }
    return render(request, "frontend/verify_manifest.html", context)