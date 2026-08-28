"""
apps/users/managers.py
──────────────────────
Custom manager for the User model.

Responsibilities:
- Email normalization: strip whitespace, lowercase.
  Applied before uniqueness validation and before any DB write.
- Standard create_user() and create_superuser() factory methods
  required by Django's AbstractBaseUser contract.

Email normalization rule:
    " John@Example.com " → "john@example.com"

This is enforced here (manager layer) rather than solely at the DB level
so that we get a clean error at Python level before hitting the unique constraint.
"""

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom manager for apps.users.User.

    Django's AbstractBaseUser requires create_user() and create_superuser().
    """

    @staticmethod
    def normalize_email_address(email: str) -> str:
        """
        Normalize an email address for consistent storage and lookup.

        Operations (applied in order):
        1. Strip leading/trailing whitespace.
        2. Convert to lowercase.
        3. Delegate to BaseUserManager.normalize_email() for domain normalization.

        This ensures that:
            " John@Example.COM " == "john@example.com"

        and prevents duplicate accounts across tenants that differ only in
        email casing or surrounding whitespace.
        """
        if not email:
            raise ValueError("Email address must not be empty.")
        email = email.strip().lower()
        email = BaseUserManager.normalize_email(email)
        return email

    def create_user(
        self,
        email: str,
        password: str = None,
        tenant=None,
        **extra_fields,
    ):
        """
        Create and save a user.
        Tenant is required for regular users, but optional for superusers.
        """
        if not email:
            raise ValueError("Users must have an email address.")
        if tenant is None and not extra_fields.get("is_superuser") and not extra_fields.get("is_staff"):
            raise ValueError("Regular users must belong to a tenant.")

        email = self.normalize_email_address(email)

        extra_fields.setdefault("is_active", True)

        user = self.model(email=email, tenant=tenant, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str = None,
        tenant=None,
        **extra_fields,
    ):
        """
        Create a superuser.
        Matches Django's standard create_superuser contract so standard CLI commands work.
        """
        extra_fields.setdefault("role", "superadmin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password=password, tenant=tenant, **extra_fields)
