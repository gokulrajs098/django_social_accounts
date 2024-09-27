from django.urls import path
from .views import GoogleLoginCallback, GoogleCalendarEventView

urlpatterns = [
    path('login/', GoogleLoginCallback.as_view(), name='google-login'),
    path('events/', GoogleCalendarEventView.as_view(), name='event-creation')
]