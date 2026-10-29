from django.urls import path
from apps.customers.views import (
    CustomerPreferencesView,
    CustomerProfileView,
    CustomerRegistrationView,
    FavouriteDetailView,
    FavouriteListCreateView,
    ReportCreateView,
    ReviewListCreateView,
)

urlpatterns = [
    path("register/", CustomerRegistrationView.as_view(), name="customer-register"),
    path("me/", CustomerProfileView.as_view(), name="customer-profile"),
    path("me/preferences/", CustomerPreferencesView.as_view(), name="customer-preferences"),
    path("me/favourites/", FavouriteListCreateView.as_view(), name="customer-favourites"),
    path("me/favourites/<int:property_id>/", FavouriteDetailView.as_view(), name="customer-favourite-detail"),
    path("reviews/", ReviewListCreateView.as_view(), name="reviews"),
    path("reports/", ReportCreateView.as_view(), name="property-reports"),
]
