import httpx

def normalize_wiki_name(wiki: str) -> str: #because wikidatawiki is not commonly used, same as comonswiki

    normalized_wiki = wiki.strip().lower()
    aliases = {
        "wikidata": "wikidatawiki",
        "commons": "commonswiki",
        "meta": "metawiki",
    }

    return aliases.get(normalized_wiki, normalized_wiki)

def get_api_url(wiki: str) -> str:  #Wiki database name to MediaWiki API URL converter.

    wiki = normalize_wiki_name(wiki)

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
        f"Unsupported wiki format: {wiki}. Try something like eswiki, enwiki, wikidata, or commons."
    )

def get_content_namespaces(wiki: str) -> list[int]: #0 for WP, 6 for Commons, 0 & more for Wikidata. Returns a list of namespace IDs that are considered "content" for the given wiki.
    normalized_wiki = normalize_wiki_name(wiki)

    if normalized_wiki == "commonswiki":
        return [6]

    if normalized_wiki == "wikidatawiki":
        return [0, 120, 146, 640]

    return [0]

def get_headers() -> dict:

    return {
        "User-Agent": "RetentionChecker/0.1 (https://toolforge.org/; Wikimedia retention analysis prototype)"
    }


def get_user_metadata_batch(
    usernames: list[str],
    wiki: str,
    batch_size: int = 50,
) -> list[dict]:

    api_url = get_api_url(wiki)
    results = []

    for start_index in range(0, len(usernames), batch_size):
        username_batch = usernames[
            start_index:start_index + batch_size
        ]

        usernames_string = "|".join(username_batch)

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
    namespaces: list[int] | None = None,
) -> list[dict]:

    api_url = get_api_url(wiki)

    if namespaces is None:
        namespaces = get_content_namespaces(wiki)

    namespace_string = "|".join(
        str(namespace) for namespace in namespaces
    )

    params = {
        "action": "query",
        "format": "json",
        "list": "usercontribs",
        "ucuser": username,
        "ucstart": start_timestamp,
        "ucend": end_timestamp,
        "ucdir": "newer",
        "uclimit": "500",
        "ucnamespace": namespace_string,
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