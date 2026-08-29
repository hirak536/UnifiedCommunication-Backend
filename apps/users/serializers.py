"""
apps/users/serializers.py
─────────────────────────
Serializers for authentication and user management.
"""

from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.extensions.models import Extension
from apps.tenants.models import Tenant
from apps.users.models import User


class ExtensionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Extension
        fields = [
            "id",
            "extension_number",
            "sip_username",
            "sip_server",
            "transport_type",
        ]


class TenantSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "id",
            "freeswitch_tenant_uuid",
            "tenant_code",
            "tenant_name",
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    tenant = TenantSummarySerializer(read_only=True)
    extension = ExtensionSummarySerializer(read_only=True)
    features = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "is_active",
            "tenant",
            "features",
            "extension",
            "fax_boxes",
            "voicemail_boxes",
            "created_at",
        ]

    def get_features(self, obj) -> dict:
        if obj.tenant and hasattr(obj.tenant, "features"):
            return obj.tenant.features
        return {
            "calling": False,
            "messaging": False,
            "fax": False,
            "voicemail": False,
        }


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                {"detail": "No active account found with the given credentials."},
                code="authorization",
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "This user account is disabled."},
                code="authorization",
            )

        attrs["user"] = user
        return attrs
