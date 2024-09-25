from django.urls import path
from .views import GoogleLoginCallback

urlpatterns = [
    path('login/', GoogleLoginCallback.as_view(), name='google-login'),
]