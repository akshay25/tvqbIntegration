from django.conf import settings
import requests

def get_access_token():
    params = {
            'client_id' : "TrackViaAPI",
            'grant_type' : "password",
            'username' : settings.TRACKVIA_USERNAME,
            'password' : settings.TRACKVIA_PASSWORD
    }
    url = settings.TRACKVIA_BASE_URL + '/oauth/token'
    r = requests.get(url = url, params = params)
    if r.status_code == 200:
        return r.json()['access_token']
    else:
        return None

