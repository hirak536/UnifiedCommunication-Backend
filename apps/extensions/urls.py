from django.urls import path
from apps.extensions.views import ExtensionDetailView, ExtensionListView

urlpatterns = [
    path("", ExtensionListView.as_view(), name="extension-list"),
    path("<uuid:id>/", ExtensionDetailView.as_view(), name="extension-detail"),
]
