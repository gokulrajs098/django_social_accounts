from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from googleapiclient.errors import HttpError

def refresh_google_access_token(refresh_token):
    token_url = 'https://oauth2.googleapis.com/token'
    payload = {
        'client_id': '204875283942-g3n3bdc2no6lj3koir4vpkei0q02sged.apps.googleusercontent.com',
        'client_secret': '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',
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }

    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        tokens = response.json()
        return tokens['access_token'], tokens.get('expires_in', 3600)
    return None, None  # Return None for both if refresh fails

def create_google_calendar_event(access_token, refresh_token, token_expiry_time):

    expires_in = None  # Initialize expires_in at the start of the function     
    # Check if the access token is expired
    if datetime.now() >= token_expiry_time:
        print("Access token has expired. Refreshing the token...")
        # Refresh the access token using the refresh token
        access_token, expires_in = refresh_google_access_token(refresh_token)
        if not access_token:
            return {'error': 'Failed to refresh the access token.'}, None  # Explicitly return error
    
    creds = Credentials(token=access_token)

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': 'Reminder: Team Meeting',
        'location': 'Google Meet',
        'description': 'Discuss the project updates',
        'start': {
            'dateTime': '2024-09-30T10:00:00-07:00',  # Example start time
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': '2024-09-30T11:00:00-07:00',  # Example end time
            'timeZone': 'America/Los_Angeles',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # Email reminder 1 day before
                {'method': 'popup', 'minutes': 10},       # Popup reminder 10 minutes before
            ],
        },
    }

    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event, expires_in
    except Exception as e:
        return {'error': str(e)}, None  # Handle Google API errors

class GoogleCalendarEventView(APIView):
    def post(self, request):
        try:
            access_token = request.data.get('access_token')
            refresh_token = request.data.get('refresh_token')
            token_expiry_time = request.data.get('token_expiry_time')

            if not token_expiry_time:
                return Response({'error': 'Token expiry time not provided'}, status=status.HTTP_400_BAD_REQUEST)

            token_expiry_time = datetime.now() + timedelta(seconds=token_expiry_time)

            if not all([access_token, refresh_token]):
                return Response({'error': 'Missing required parameters'}, status=status.HTTP_400_BAD_REQUEST)

            # Create the Google Calendar event
            event, expires_in = create_google_calendar_event(access_token, refresh_token, token_expiry_time)

            # Check for errors during event creation
            if 'error' in event:
                return Response({'error': event['error']}, status=status.HTTP_400_BAD_REQUEST)

            # If token was refreshed, include new expiry time in the response
            if expires_in:
                new_expiry_time = datetime.now() + timedelta(seconds=expires_in)
                return Response({
                    'event': event,
                    'new_token_expiry_time': new_expiry_time.isoformat()
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({'event': event}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'Unexpected error: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GoogleLoginCallback(APIView):
    def get(self, request):
        try:
            # Extract code from the query parameters
            code = request.query_params.get('code')
            if not code:
                return Response({'error': 'Authorization code not provided'}, status=status.HTTP_400_BAD_REQUEST)

            # Exchange the authorization code for tokens
            token_url = 'https://oauth2.googleapis.com/token'
            payload = {
                'code': code,
                'client_id': '204875283942-g3n3bdc2no6lj3koir4vpkei0q02sged.apps.googleusercontent.com',
                'client_secret': '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',
                'redirect_uri': 'http://127.0.0.1:8000/auth/social/custom/login/',
                'grant_type': 'authorization_code',
                'scope': 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
                'access_type': 'offline',  # Request offline access
            }

            # Make a POST request to exchange code for tokens
            response = requests.post(token_url, data=payload)
            tokens = response.json()

            # Check for token exchange success
            if response.status_code != 200:
                return Response({'error': 'Failed to obtain tokens', 'details': tokens}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure required scopes are present
            if 'scope' not in tokens or 'calendar' not in tokens['scope']:
                return Response({'error': 'Insufficient permissions, required calendar access'}, status=status.HTTP_403_FORBIDDEN)

            # Extract tokens and other information
            access_token = tokens.get('access_token')
            id_token = tokens.get('id_token')
            refresh_token = tokens.get('refresh_token')
            expires_in = tokens.get('expires_in')

            if not all([access_token, id_token]):
                return Response({'error': 'Access token or ID token missing from response'}, status=status.HTTP_400_BAD_REQUEST)

            # Use the access token to fetch profile information from Google's UserInfo endpoint
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            userinfo_response = requests.get(userinfo_url, headers=headers)
            userinfo = userinfo_response.json()

            if userinfo_response.status_code == 200:
                # Return tokens, user profile information, and token expiry time
                return Response({
                    'access_token': access_token,
                    'id_token': id_token,
                    'refresh_token': refresh_token,  # Return refresh token if available
                    'token_expiry_time': expires_in,  # Return token expiry time in seconds
                    'user_info': userinfo
                }, status=status.HTTP_200_OK)
            else:
                # Handle error in fetching user info
                return Response({'error': 'Failed to fetch user info', 'details': userinfo}, status=status.HTTP_400_BAD_REQUEST)

        except requests.RequestException as e:
            return Response({'error': f'HTTP Request failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'Unexpected error: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)