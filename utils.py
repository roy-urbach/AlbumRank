import base64, requests

from consts import CLIENT_ID, CLIENT_SECRET

AUTH_URL = 'https://accounts.spotify.com/api/token'
GRANT_TYPE = 'client_credentials'
ACCESS_TOKEN = None
ARTIST_IDS = {"Elvis Presley": "43ZHCT0cAZBISjO8DG9PnE?si=QT2HgySWTFmSo9M5Z3K9MA"}


def get_access_token():
    global ACCESS_TOKEN
    if ACCESS_TOKEN is None:
        auth_data = {'grant_type': GRANT_TYPE}
        auth_header = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
        auth_headers = {'Authorization': f'Basic {auth_header}'}
        response = requests.post(AUTH_URL, data=auth_data, headers=auth_headers)
        if response.status_code == 200:
            token_info = response.json()
            ACCESS_TOKEN = token_info['access_token']
        else:
            raise Exception("Failed to authenticate with Spotify API.")
    return ACCESS_TOKEN


def get_headers():
    token = get_access_token()
    return {'Authorization': f'Bearer {token}'}


def choose_artist_headless(artist_name):
    artist_id = None
    if artist_name in ARTIST_IDS:
        artist_id = ARTIST_IDS[artist_name]
    else:
        try:
            artist_id = search_artist(artist_name)
        except Exception as err:
            # In a GUI, this would be handled by displaying a list of close matches
            print(f"Error finding artist {artist_name}: {err}")
            print("No close matches handled in this headless version.")
            return None # Indicate failure to find artist

    return artist_id


def search_artist(artist_name):
    search_url = 'https://api.spotify.com/v1/search'
    headers = get_headers()
    params = {'q': artist_name, 'type': 'artist', 'limit': 1}
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        search_results = response.json()
        if search_results['artists']['items']:
            return search_results['artists']['items'][0]['id']
        else:
            return None
    else:
        print(f"Error searching for artist {artist_name}: {response.status_code}")
        return None