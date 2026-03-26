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


def _igdb_search_term(query):
    """Strip characters that break IGDB `search "..."` syntax."""
    if not query:
        return ""
    s = query.replace("\\", " ").replace('"', " ").strip()
    return s[:200] if s else ""


def search_games(query):
    global access_token

    term = _igdb_search_term(query)
    if not term:
        return []

    if not access_token:
        get_access_token()

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }

    body = f'''
        fields name,genres.name,summary,cover.url;
        search "{term}";
        where cover != null;
        limit 20;
    '''

    response = requests.post(IGDB_URL, headers=headers, data=body)

    data = response.json()
    if not isinstance(data, list):
        return []
    return data


def featured_games(limit=12):
    """Highly-rated / often-rated games from IGDB (no search query)."""
    global access_token

    try:
        if not access_token:
            get_access_token()

        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {access_token}"
        }

        body = f"""
            fields name,genres.name,summary,cover.url,total_rating,rating_count,id;
            where cover != null & rating_count > 15;
            sort rating_count desc;
            limit {int(limit)};
        """

        response = requests.post(
            IGDB_URL, headers=headers, data=body, timeout=20
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return []
        return data
    except Exception as e:
        print("featured_games error:", e)
        return []
