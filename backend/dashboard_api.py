from collections import defaultdict
from datetime import datetime
from urllib.parse import quote

import requests


DASHBOARD_BASE_URL = "https://outreachdashboard.wmflabs.org"
REQUEST_TIMEOUT_SECONDS = 30

HEADERS = {
    "User-Agent": (
        "RetentionChecker/0.1 "
        "(Wikimedia retention analysis tool)"
    )
}


class DashboardApiError(Exception):
    """Raised when Dashboard data cannot be retrieved or interpreted."""


def validate_course_slug(course_slug: str) -> str:
    """
    Validate and normalize a Dashboard course slug.

    Expected format:
    Organization/Course_Name
    """
    normalized_slug = course_slug.strip().strip("/")
    parts = normalized_slug.split("/")

    if len(parts) != 2 or not all(parts):
        raise ValueError(
            "The Dashboard course slug must use the format "
            "Organization/Course_Name."
        )

    if any(part in {".", ".."} for part in parts):
        raise ValueError("The Dashboard course slug is not valid.")

    return normalized_slug


def build_dashboard_url(course_slug: str, resource: str) -> str:
    normalized_slug = validate_course_slug(course_slug)
    organization, course_name = normalized_slug.split("/", maxsplit=1)

    encoded_slug = (
        f"{quote(organization, safe='')}/"
        f"{quote(course_name, safe='')}"
    )

    return (
        f"{DASHBOARD_BASE_URL}/courses/"
        f"{encoded_slug}/{resource}.json"
    )


def fetch_dashboard_resource(
    course_slug: str,
    resource: str
) -> dict:
    url = build_dashboard_url(course_slug, resource)

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        raise DashboardApiError(
            "Could not connect to the Programs & Events Dashboard."
        ) from exc

    if response.status_code == 404:
        raise DashboardApiError(
            "The Dashboard course could not be found."
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise DashboardApiError(
            "The Programs & Events Dashboard returned an error."
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise DashboardApiError(
            "The Dashboard returned an invalid response."
        ) from exc

    course_data = data.get("course")

    if not isinstance(course_data, dict):
        raise DashboardApiError(
            "The Dashboard response does not contain course data."
        )

    return course_data


def format_date_only(value: str | None) -> str | None:
    if not value:
        return None

    try:
        parsed_date = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return parsed_date.date().isoformat()
    except ValueError:
        return None


def suggest_wiki(home_wiki: dict | None) -> str | None:
    """
    Convert common Dashboard home-wiki values into the wiki identifiers
    currently understood by Retention Checker.
    """
    if not home_wiki:
        return None

    language = home_wiki.get("language")
    project = home_wiki.get("project")

    if project == "wikipedia" and language:
        return f"{language}wiki"

    if project == "wikidata":
        return "wikidatawiki"

    if project == "wikimedia" and language == "commons":
        return "commonswiki"

    if project == "wikimedia" and language == "meta":
        return "metawiki"

    return None


def summarize_dashboard_users(user_records: list[dict]) -> dict:
    """
    Deduplicate Dashboard user records and separate participants from staff.

    A username that has both participant and staff roles is treated as a
    role conflict and excluded from the default participant list.
    """
    roles_by_username: dict[str, set[int]] = defaultdict(set)

    for user in user_records:
        username = str(user.get("username", "")).strip()
        role = user.get("role")

        if not username:
            continue

        if isinstance(role, int):
            roles_by_username[username].add(role)

    participant_usernames = []
    staff_usernames = []
    role_conflict_usernames = []

    for username, roles in roles_by_username.items():
        has_participant_role = 0 in roles
        has_staff_role = any(role != 0 for role in roles)

        if has_participant_role and has_staff_role:
            role_conflict_usernames.append(username)
        elif has_participant_role:
            participant_usernames.append(username)
        else:
            staff_usernames.append(username)

    return {
        "raw_user_records": len(user_records),
        "unique_users": len(roles_by_username),
        "participant_count": len(participant_usernames),
        "staff_count": len(staff_usernames),
        "role_conflict_count": len(role_conflict_usernames),
        "participant_usernames": sorted(
            participant_usernames,
            key=str.casefold
        ),
        "staff_usernames": sorted(
            staff_usernames,
            key=str.casefold
        ),
        "role_conflict_usernames": sorted(
            role_conflict_usernames,
            key=str.casefold
        )
    }


def get_dashboard_course_preview(course_slug: str) -> dict:
    normalized_slug = validate_course_slug(course_slug)

    course = fetch_dashboard_resource(
        normalized_slug,
        "course"
    )

    users_resource = fetch_dashboard_resource(
        normalized_slug,
        "users"
    )

    user_records = users_resource.get("users", [])

    if not isinstance(user_records, list):
        raise DashboardApiError(
            "The Dashboard response does not contain a valid user list."
        )

    user_summary = summarize_dashboard_users(user_records)

    timeline_end = course.get("timeline_end")
    course_end = course.get("end")

    return {
        "course_slug": normalized_slug,
        "course_url": (
            f"{DASHBOARD_BASE_URL}/courses/{normalized_slug}"
        ),
        "title": course.get("title"),
        "organization": course.get("school"),
        "activity_type": course.get("type"),
        "timeline_start": course.get("timeline_start"),
        "timeline_end": timeline_end,
        "course_start": course.get("start"),
        "course_end": course_end,
        "suggested_reference_date": (
            format_date_only(timeline_end)
            or format_date_only(course_end)
        ),
        "home_wiki": course.get("home_wiki"),
        "suggested_wiki": suggest_wiki(
            course.get("home_wiki")
        ),
        **user_summary
    }