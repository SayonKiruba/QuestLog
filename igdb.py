import requests

CLIENT_ID = "o50ito0pmytmcep4cuaflfuod30wwc"
CLIENT_SECRET = "pnxkpq4s22pkwy939le7xyf6fz9gre"

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_URL = "https://api.igdb.com/v4/games"

access_token = None


def get_access_token():
    global access_token

    response = requests.post(TOKEN_URL, params={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    })

    access_token = response.json()["access_token"]
    return access_token


def search_games(query):
    global access_token

    if not access_token:
        get_access_token()

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }

    body = f'''
        fields name,genres.name,summary,cover.url;
        search "{query}";
        where cover != null;
        limit 20;
    '''

    response = requests.post(IGDB_URL, headers=headers, data=body)

    return response.json()