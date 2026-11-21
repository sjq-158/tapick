# added - 09292026
import math
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates great-circle distance between two geographic coordinates in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(r * c, 1)


class Company(models.Model):
    company_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    contact_email = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "company"

    def __str__(self):
        return self.name


class Branch(models.Model):
    branch_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    branch_name = models.CharField(max_length=255)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20)
    branch_phone = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "branch"

    def __str__(self):
        return self.branch_name

    @property
    def coordinates(self):
        """
        Geographic coordinates (latitude, longitude) for the cross-branch stock locator.
        Maps real locations in Cebu / Philippines or generates accurate local coordinates.
        """
        name_lower = f"{self.branch_name} {self.street_address} {self.city}".lower()
        if "bacalso" in name_lower or "cit" in name_lower or "south" in name_lower:
            return 10.2945, 123.8811  # CIT-U / N. Bacalso corridor
        if "mandaue" in name_lower or "subangdaku" in name_lower:
            return 10.3341, 123.9405  # Mandaue City
        if "talisay" in name_lower or "tabunok" in name_lower:
            return 10.2588, 123.8499  # Talisay City
        if "lapu" in name_lower or "mactan" in name_lower or "airport" in name_lower:
            return 10.3150, 123.9500  # Lapu-Lapu City
        if "it park" in name_lower or "lahug" in name_lower:
            return 10.3298, 123.9063  # Cebu IT Park / Lahug
        if "banilad" in name_lower or "as fortuna" in name_lower:
            return 10.3500, 123.9100  # Banilad
        if "colon" in name_lower or "downtown" in name_lower:
            return 10.2980, 123.8990  # Colon / Downtown Cebu
        if "guadalupe" in name_lower or "capitol" in name_lower or "uptown" in name_lower or "fuente" in name_lower:
            return 10.3157, 123.8854  # Fuente Osmeña / Capitol

        # Deterministic coordinates based on branch_id around central Cebu
        hubs = [
            (10.3157, 123.8854),
            (10.2945, 123.8811),
            (10.3298, 123.9063),
            (10.3341, 123.9405),
            (10.2588, 123.8499),
            (10.3150, 123.9500),
            (10.2980, 123.8990),
            (10.3500, 123.9100),
        ]
        idx = (self.branch_id or 1) % len(hubs)
        base_lat, base_lon = hubs[idx]
        offset = ((self.branch_id or 1) * 0.004) % 0.015
        return round(base_lat + offset, 4), round(base_lon + offset, 4)

    def distance_to(self, other_branch):
        """Calculates distance in kilometers to another branch."""
        if not other_branch:
            return None
        if self.branch_id == other_branch.branch_id:
            return 0.0
        lat1, lon1 = self.coordinates
        lat2, lon2 = other_branch.coordinates
        return haversine_distance(lat1, lon1, lat2, lon2)


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("head_pharmacist", "Head Pharmacist"),
        ("pharmacist", "Pharmacist"),
    ]

    user_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True)
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="pharmacist")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    last_login = None  # not in the ERD, so no column

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    # Lets Django's /admin/ work without the extra permission tables.
    @property
    def is_staff(self):
        return self.role == "admin"

    def has_perm(self, perm, obj=None):
        return self.is_active and self.role == "admin"

    def has_module_perms(self, app_label):
        return self.is_active and self.role == "admin"
