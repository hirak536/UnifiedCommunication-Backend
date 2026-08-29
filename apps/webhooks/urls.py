from django.urls import path
from apps.webhooks.views import FreeSwitchWebhookView

urlpatterns = [
    path("freeswitch/", FreeSwitchWebhookView.as_view(), name="webhook-freeswitch"),
]
