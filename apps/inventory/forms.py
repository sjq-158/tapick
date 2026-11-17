from django import forms

from apps.home.models import Medicine
from apps.register.models import Branch

from .access import visible_branches, visible_medicines


class AddStockForm(forms.Form):
    medicine = forms.ModelChoiceField(queryset=Medicine.objects.none())
    branch = forms.ModelChoiceField(queryset=Branch.objects.none())
    quantity_on_hand = forms.IntegerField(label="Quantity on hand", min_value=0)
    reorder_threshold = forms.IntegerField(label="Reorder level", min_value=0)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = visible_branches(user)
        self.fields["medicine"].queryset = visible_medicines(user)


class AdjustStockForm(forms.Form):
    action = forms.ChoiceField(choices=[("set", "Set quantity"), ("add", "Add stock"), ("remove", "Remove stock")])
    amount = forms.IntegerField(min_value=0)
    reorder_threshold = forms.IntegerField(label="Reorder level", min_value=0, required=False)


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            "medicine_name", "generic_name", "brand_name", "category",
            "unit_of_measure", "unit_price", "requires_prescription",
        ]
        labels = {"medicine_name": "Medicine name", "unit_of_measure": "Unit", "unit_price": "Unit price"}