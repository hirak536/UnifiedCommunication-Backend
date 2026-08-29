from django.urls import path
from apps.dids.views import DIDDetailView, DIDListView

urlpatterns = [
    path("", DIDListView.as_view(), name="did-list"),
    path("<uuid:id>/", DIDDetailView.as_view(), name="did-detail"),
]
