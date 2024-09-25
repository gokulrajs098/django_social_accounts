from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

class GoogleLoginCallback(APIView):
    def get(self, request):
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
        }

        # Make a POST request to exchange code for tokens
        response = requests.post(token_url, data=payload)
        tokens = response.json()

        # Check if we received tokens successfully
        if 'access_token' in tokens and 'id_token' in tokens:
            access_token = tokens['access_token']
            id_token = tokens['id_token']

            # Use the access token to fetch profile information from Google's UserInfo endpoint
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            userinfo_response = requests.get(userinfo_url, headers=headers)
            userinfo = userinfo_response.json()

            if userinfo_response.status_code == 200:
                # Return tokens and user profile information
                return Response({
                    'access_token': access_token,
                    'id_token': id_token,
                    'user_info': userinfo
                }, status=status.HTTP_200_OK)
            else:
                # Handle error in fetching user info
                return Response({'error': 'Failed to fetch user info', 'details': userinfo}, status=status.HTTP_400_BAD_REQUEST)

        # Handle errors and return response
        return Response({'error': 'Failed to obtain tokens', 'details': tokens}, status=status.HTTP_400_BAD_REQUEST)
