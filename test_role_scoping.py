"""Final verification of the 4-role scoping system."""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.organization.context import (
    set_current_tenant, reset_tenant,
    set_current_department, reset_department,
    set_current_role, reset_role,
    set_bypass, reset_bypass,
)
from apps.organization.models import Company, Department, UserCompanyMembership
from apps.experts.models import ExpertProfile


def main():
    kibali = Company.objects.get(slug="kibali")
    mining = Department.objects.get(company=kibali, code="MINING")

    print("\n" + "═" * 60)
    print("  4-ROLE SCOPING TEST (final)")
    print("═" * 60)

    # Test 1
    print("\n[Test 1] No tenant (fail-safe):")
    n = ExpertProfile.objects.count()
    print(f"  Result: {n}  (expected: 0)")
    ok1 = (n == 0)

    # Test 2
    print("\n[Test 2] HR Manager — full company:")
    t1 = set_current_tenant(kibali)
    t2 = set_current_role(UserCompanyMembership.Role.HR_MANAGER)
    n = ExpertProfile.objects.count()
    print(f"  Result: {n}  (expected: ≥1)")
    ok2 = (n >= 1)
    reset_role(t2); reset_tenant(t1)

    # Test 3
    print("\n[Test 3] Department Manager — scoped to Mining:")
    t1 = set_current_tenant(kibali)
    t2 = set_current_role(UserCompanyMembership.Role.DEPARTMENT_MANAGER)
    t3 = set_current_department(mining)
    n = ExpertProfile.objects.count()
    print(f"  Result: {n}  (expected: 1 — Jean is now in Mining)")
    ok3 = (n == 1)
    reset_department(t3); reset_role(t2); reset_tenant(t1)

    # Test 4
    print("\n[Test 4] Superuser bypass:")
    t1 = set_bypass(True)
    n = ExpertProfile.objects.count()
    print(f"  Result: {n}  (expected: ≥1)")
    ok4 = (n >= 1)
    reset_bypass(t1)

    print("\n" + "═" * 60)
    print("  SUMMARY")
    print("═" * 60)
    print(f"  Test 1 (fail-safe)       : {'✅ PASS' if ok1 else '❌ FAIL'}")
    print(f"  Test 2 (HR full access)  : {'✅ PASS' if ok2 else '❌ FAIL'}")
    print(f"  Test 3 (Dept scoping)    : {'✅ PASS' if ok3 else '❌ FAIL'}")
    print(f"  Test 4 (superuser bypass): {'✅ PASS' if ok4 else '❌ FAIL'}")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()