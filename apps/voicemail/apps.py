from django.apps import AppConfig


class VoicemailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.voicemail"
    label = "voicemail"
    verbose_name = "Voicemail"
