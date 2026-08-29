"""
apps/users/backends.py
───────────────────────
Optimized email-based authentication backend with eager relationship loading.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailAuthBackend(ModelBackend):
    """
    Authenticates against normalized email with select_related('tenant', 'extension')
    to prevent subsequent N+1 database queries during token generation and user serialization.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email or not password:
            return None

        email = email.strip().lower()
        try:
            user = (
                UserModel.objects
                .select_related("tenant", "extension")
                .get(email=email)
            )
        except UserModel.DoesNotExist:
            # Run dummy password hasher check to mitigate timing attacks
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
