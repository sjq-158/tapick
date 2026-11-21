from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Admin, HeadPharmacist, Pharmacist

PROFILE_MODELS = {
    "admin": Admin,
    "head_pharmacist": HeadPharmacist,
    "pharmacist": Pharmacist,
}

ROLE_CAPABILITIES = {
    "admin": {
        "title": "Organization Administrator",
        "description": "Full administrative control over company branches, user onboarding, role access, and organizational inventory.",
        "permissions": [
            "Company & Branch Configuration",
            "Staff & Role Management",
            "System-wide Inventory Auditing",
            "Cross-Branch Activity Oversight",
        ],
    },
    "head_pharmacist": {
        "title": "Head Pharmacist",
        "description": "Supervises medicine catalogue specifications, reorder levels, stock allocations, and cross-branch transfer requests.",
        "permissions": [
            "Catalogue Medicine Creation & Pricing",
            "Stock Reorder Threshold Configuration",
            "Cross-Branch Transfer Authorization",
            "Company-wide Stock Locator Access",
        ],
    },
    "pharmacist": {
        "title": "Branch Pharmacist",
        "description": "Responsible for daily branch stock tracking, dispensing records, cross-branch availability inquiries, and stock receiving.",
        "permissions": [
            "Branch Stock Level Management",
            "Cross-Branch Availability Locator",
            "Inter-Branch Stock Transfer Requests",
            "Real-time Inventory Notifications",
        ],
    },
}


def get_profile(user):
    model = PROFILE_MODELS.get(user.role, Pharmacist)
    profile, _ = model.objects.get_or_create(user=user)
    return profile


@method_decorator(login_required, name="dispatch")
class ProfileScreen(View):
    def get(self, request):
        user = request.user
        profile = get_profile(user)

        full_name = f"{profile.first_name} {profile.last_name}".strip()
        display_name = full_name if full_name else user.email.split("@")[0].replace(".", " ").title()

        initials = (
            (profile.first_name[:1] + profile.last_name[:1]).upper()
            if (profile.first_name and profile.last_name)
            else user.email[:2].upper()
        )

        phone_val = getattr(profile, getattr(profile, "phone_field", ""), "")
        license_val = getattr(profile, "license_number", "") if hasattr(profile, "license_number") else ""

        role_info = ROLE_CAPABILITIES.get(user.role, ROLE_CAPABILITIES["pharmacist"])

        return render(request, "profiles/profile.html", {
            "profile": profile,
            "display_name": display_name,
            "initials": initials,
            "phone": phone_val or "Not provided",
            "license_number": license_val or ("N/A - Administrative Role" if user.role == "admin" else "Not on file"),
            "has_license": hasattr(profile, "license_number"),
            "role_info": role_info,
            "user_branch": user.branch,
            "user_company": user.company,
        })
