from apps.home.models import Medicine
from apps.register.models import Branch


def visible_branches(user):
    branches = Branch.objects.filter(is_active=True)
    if user.company_id:
        branches = branches.filter(company_id=user.company_id)
    if user.role == "pharmacist" and user.branch_id:
        branches = branches.filter(branch_id=user.branch_id)
    return branches


def visible_medicines(user):
    medicines = Medicine.objects.filter(is_active=True)
    if user.company_id:
        medicines = medicines.filter(company_id=user.company_id)
    return medicines


def can_manage_catalogue(user):
    return user.role in ("head_pharmacist", "admin") and bool(user.company_id)