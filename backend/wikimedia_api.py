import httpx


def get_api_url(wiki: str) -> str:
    """
    Convert a wiki database name into a MediaWiki API URL.

    Examples:
    - eswiki -> https://es.wikipedia.org/w/api.php
    - enwiki -> https://en.wikipedia.org/w/api.php
    - wikidatawiki -> https://www.wikidata.org/w/api.php
    - commonswiki -> https://commons.wikimedia.org/w/api.php
    """

    wiki = wiki.strip().lower()

    special_wikis = {
        "wikidatawiki": "https://www.wikidata.org/w/api.php",
        "commonswiki": "https://commons.wikimedia.org/w/api.php",
        "metawiki": "https://meta.wikimedia.org/w/api.php",
    }

    if wiki in special_wikis:
        return special_wikis[wiki]

    if wiki.endswith("wiki"):
        language_code = wiki.replace("wiki", "")
        return f"https://{language_code}.wikipedia.org/w/api.php"

    raise ValueError(
        f"Unsupported wiki format: {wiki}. Try something like eswiki, enwiki, wikidatawiki, or commonswiki."
    )


def get_headers() -> dict:
    """
    Wikimedia asks API clients to use a clear User-Agent.
    Later we can replace this with the final Toolforge URL.
    """

    return {
        "User-Agent": "RetentionChecker/0.1 (https://toolforge.org/; Wikimedia retention analysis prototype)"
    }


def get_user_metadata_batch(usernames: list[str], wiki: str) -> list[dict]:
    """
    Fetch basic user metadata from the Wikimedia API.

    For each username, this returns:
    - username
    - user_id
    - registration_date
    - is_missing
    - is_bot

    This function does not calculate retention yet.
    """

    api_url = get_api_url(wiki)

    usernames_string = "|".join(usernames)

    params = {
        "action": "query",
        "format": "json",
        "list": "users",
        "ususers": usernames_string,
        "usprop": "registration|groups",
    }

    response = httpx.get(
        api_url,
        params=params,
        headers=get_headers(),
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    users = data.get("query", {}).get("users", [])

    results = []

    for user in users:
        groups = user.get("groups", [])

        is_missing = "missing" in user

        is_bot = (
            "bot" in groups
            or user.get("name", "").lower().endswith("bot")
        )

        results.append({
            "username": user.get("name"),
            "user_id": user.get("userid"),
            "registration_date": user.get("registration"),
            "is_missing": is_missing,
            "is_bot": is_bot,
            "groups": groups,
        })

    return results


def get_user_contributions(
    username: str,
    wiki: str,
    start_timestamp: str,
    end_timestamp: str,
    namespace: int = 0,
) -> list[dict]:
    """
    Fetch visible user contributions from a Wikimedia project.

    For v0.1, we use namespace 0 only:
    - Wikipedia articles
    - Wikidata items
    - Commons files
    - Main content pages in other projects

    Timestamps should look like:
    2026-03-31T00:00:00Z
    """

    api_url = get_api_url(wiki)

    params = {
        "action": "query",
        "format": "json",
        "list": "usercontribs",
        "ucuser": username,
        "ucstart": start_timestamp,
        "ucend": end_timestamp,
        "ucdir": "newer",
        "uclimit": "500",
        "ucnamespace": namespace,
        "ucprop": "ids|title|timestamp|sizediff|flags",
    }

    contributions = []

    while True:
        response = httpx.get(
            api_url,
            params=params,
            headers=get_headers(),
            timeout=30
        )
        response.raise_for_status()

        data = response.json()

        batch = data.get("query", {}).get("usercontribs", [])
        contributions.extend(batch)

        if "continue" not in data:
            break

        params.update(data["continue"])

    return contributions