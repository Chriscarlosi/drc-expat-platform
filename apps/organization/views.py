"""Organization views — MFA setup."""

import qrcode
from io import BytesIO
from base64 import b64encode

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from django_otp.plugins.otp_totp.models import TOTPDevice


@login_required
def mfa_setup(request):
    """TOTP MFA setup page — QR code + verification."""

    device, created = TOTPDevice.objects.get_or_create(
        user=request.user,
        name="default",
        confirmed=False,
    )

    if request.method == "POST":
        token = request.POST.get("token", "").strip()

        if device.verify_token(token):
            device.confirmed = True
            device.save()
            messages.success(request, "MFA enabled successfully. Welcome!")
            return redirect("/admin/")
        else:
            messages.error(request, "Invalid code. Please try again.")

    # Generate QR code
    qr = qrcode.make(device.config_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = b64encode(buffer.getvalue()).decode()

    return render(
        request,
        "organization/mfa_setup.html",
        {"qr_code": qr_base64, "secret": device.key},
    )