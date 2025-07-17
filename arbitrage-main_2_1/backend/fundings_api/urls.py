from django.urls import path
from .views import getFundingsView

urlpatterns = [
    path('get/', getFundingsView)
]
