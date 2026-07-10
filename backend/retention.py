from datetime import datetime, timezone, timedelta

from wikimedia_api import get_user_metadata_batch, get_user_contributions


def normalize_usernames(usernames: list[str]) -> list[str]:
    """
    Clean and deduplicate usernames.

    - Removes empty lines
    - Trims spaces
    - Deduplicates usernames case-insensitively
    """

    cleaned_usernames = []
    seen = set()

    for username in usernames:
        cleaned = username.strip()

        if not cleaned:
            continue

        username_key = cleaned.lower()

        if username_key in seen:
            continue

        cleaned_usernames.append(cleaned)
        seen.add(username_key)

    return cleaned_usernames


def parse_wikimedia_timestamp(timestamp: str | None) -> datetime | None:
    """
    Convert a Wikimedia timestamp string into a Python datetime.

    Example input:
    "2020-01-15T12:34:56Z"

    If the timestamp is missing or invalid, return None.
    """

    if not timestamp:
        return None

    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def reference_date_to_datetime(reference_date) -> datetime:
    """
    Convert FastAPI's date object into a UTC datetime at midnight.
    """

    return datetime(
        year=reference_date.year,
        month=reference_date.month,
        day=reference_date.day,
        tzinfo=timezone.utc
    )


def datetime_to_wikimedia_timestamp(dt: datetime) -> str:
    """
    Convert a Python datetime into the timestamp format expected by Wikimedia APIs.
    """

    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_experience_type(
    registration_date: str | None,
    reference_date,
    newbie_threshold_days: int
) -> str:
    """
    Classify a valid user as newbie, existing user, or unknown.

    Newbie:
    - Registered between reference_date - newbie_threshold_days and reference_date.

    Existing user:
    - Registered before that threshold.

    Unknown:
    - Registration date is unavailable or invalid.
    """

    registration_dt = parse_wikimedia_timestamp(registration_date)

    if registration_dt is None:
        return "unknown"

    reference_dt = reference_date_to_datetime(reference_date)

    days_between = (reference_dt - registration_dt).days

    days_between = (reference_dt - registration_dt).days

    if days_between < 0:
        return "created_after_reference_date"

    if 0 <= days_between <= newbie_threshold_days:
        return "newbie"

    return "existing_user"


def calculate_retention_metrics(
    contributions: list[dict],
    reference_date,
    retention_windows: list[int],
) -> dict:
    """
    Calculate cumulative retention metrics from post-event contributions.

    A retention window is only available if enough time has passed since
    the reference date. For example, 180-day retention should not be shown
    as final if the reference date was only 90 days ago.
    """

    reference_dt = reference_date_to_datetime(reference_date)

    # "Today" in UTC, at midnight.
    today_dt = datetime.now(timezone.utc).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    contribution_datetimes = []

    for contribution in contributions:
        timestamp = contribution.get("timestamp")
        contribution_dt = parse_wikimedia_timestamp(timestamp)

        if contribution_dt is not None:
            contribution_datetimes.append(contribution_dt)

    contribution_datetimes.sort()

    metrics = {}

    for window in retention_windows:
        window_end = reference_dt + timedelta(days=window)
        window_is_available = window_end <= today_dt

        metrics[f"available_{window}d"] = window_is_available

        if not window_is_available:
            metrics[f"edits_{window}d"] = None
            metrics[f"retained_{window}d"] = None
            continue

        count = sum(
            1
            for contribution_dt in contribution_datetimes
            if reference_dt <= contribution_dt <= window_end
        )

        metrics[f"edits_{window}d"] = count
        metrics[f"retained_{window}d"] = count > 0

    active_months = {
        contribution_dt.strftime("%Y-%m")
        for contribution_dt in contribution_datetimes
    }

    first_edit = contribution_datetimes[0] if contribution_datetimes else None
    last_edit = contribution_datetimes[-1] if contribution_datetimes else None

    total_edits = len(contribution_datetimes)

    return {
        **metrics,
        "total_edits": total_edits,
        "active_months": len(active_months),
        "first_post_activity_edit": first_edit.date().isoformat() if first_edit else None,
        "last_post_activity_edit": last_edit.date().isoformat() if last_edit else None,
    }


def classify_retention_category(
    total_edits: int,
    active_months: int,
    active_edit_threshold: int,
    very_active_edit_threshold: int,
) -> str:
    """
    Classify post-event retention level.

    Priority order:
    1. Not retained
    2. Very active retained user
    3. Sustained retained user
    4. Active retained user
    5. One-time returner
    """

    if total_edits == 0:
        return "not_retained"

    if total_edits >= very_active_edit_threshold:
        return "very_active_retained_user"

    if total_edits >= active_edit_threshold and active_months >= 2:
        return "very_active_retained_user"

    if active_months >= 2:
        return "sustained_retained_user"

    if total_edits >= active_edit_threshold:
        return "active_retained_user"

    return "one_time_returner"


def calculate_percentage(count: int, total: int) -> float:
    """
    Calculate percentage safely.
    """

    if total == 0:
        return 0

    return round((count / total) * 100, 1)

def build_retention_summary(window: int, retained_counts: dict, valid_users: int, reference_date) -> dict:
    """
    Build summary data for a retention window.

    If the window is not available yet, return null values so the frontend
    does not show misleading 0% retention.
    """

    reference_dt = reference_date_to_datetime(reference_date)

    today_dt = datetime.now(timezone.utc).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    window_end = reference_dt + timedelta(days=window)
    window_is_available = window_end <= today_dt

    if not window_is_available:
        return {
            "available": False,
            "count": None,
            "percentage": None
        }

    count = retained_counts.get(window, 0)

    return {
        "available": True,
        "count": count,
        "percentage": calculate_percentage(count, valid_users)
    }


def count_pre_event_edits(
    username: str,
    wiki: str,
    reference_date,
    reactivation_threshold_days: int,
) -> int:
    """
    Count main-namespace edits before the reference date.

    For v0.1, this is used to identify reactivated editors.

    Reactivated editor logic:
    - Existing user
    - 0 main-namespace edits in the previous N days
    - 1+ main-namespace edits after the reference date
    """

    reference_dt = reference_date_to_datetime(reference_date)
    pre_event_start_dt = reference_dt - timedelta(days=reactivation_threshold_days)

    start_timestamp = datetime_to_wikimedia_timestamp(pre_event_start_dt)
    end_timestamp = datetime_to_wikimedia_timestamp(reference_dt)

    contributions = get_user_contributions(
        username=username,
        wiki=wiki,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        namespace=0,
    )

    return len(contributions)


def analyze_manual_placeholder(request) -> dict:
    """
    Manual analysis with real user metadata and real post-event edit counts.

    This version:
    - Cleans usernames
    - Fetches real registration dates from Wikimedia
    - Detects missing users
    - Detects likely bots
    - Classifies valid users as newbie or existing_user
    - Detects reactivated editors
    - Fetches main-namespace edits after the reference date
    - Calculates cumulative retention windows
    """

    cleaned_usernames = normalize_usernames(request.usernames)
    duplicate_or_removed_usernames = len(request.usernames) - len(cleaned_usernames)

    user_metadata = get_user_metadata_batch(
        usernames=cleaned_usernames,
        wiki=request.wiki
    )

    users = []
    invalid_users = 0
    bot_users = 0
    newbies = 0
    existing_users = 0
    reactivated_editors = 0
    unknown_experience = 0

    retained_counts = {
        30: 0,
        90: 0,
        180: 0,
        360: 0,
    }

    active_retained_users = 0
    sustained_retained_users = 0
    very_active_retained_users = 0

    max_window = max(request.retention_windows)
    reference_dt = reference_date_to_datetime(request.reference_date)
    end_dt = reference_dt + timedelta(days=max_window)

    post_event_start_timestamp = datetime_to_wikimedia_timestamp(reference_dt)
    post_event_end_timestamp = datetime_to_wikimedia_timestamp(end_dt)

    for metadata in user_metadata:
        is_missing = metadata["is_missing"]
        is_bot = metadata["is_bot"]

        if is_missing:
            status = "user_not_found"
            experience_type = None
            pre_event_edits = None
            reactivation_status = None
            invalid_users += 1

            retention_metrics = {
                "available_30d": False,
                "available_90d": False,
                "available_180d": False,
                "available_360d": False,
                "edits_30d": None,
                "edits_90d": None,
                "edits_180d": None,
                "edits_360d": None,
                "retained_30d": None,
                "retained_90d": None,
                "retained_180d": None,
                "retained_360d": None,
                "total_edits": None,
                "active_months": None,
                "first_post_activity_edit": None,
                "last_post_activity_edit": None,
            }

            retention_category = None

        elif is_bot:
            status = "bot_excluded"
            experience_type = None
            pre_event_edits = None
            reactivation_status = None
            bot_users += 1

            retention_metrics = {
                "available_30d": False,
                "available_90d": False,
                "available_180d": False,
                "available_360d": False,
                "edits_30d": None,
                "edits_90d": None,
                "edits_180d": None,
                "edits_360d": None,
                "retained_30d": None,
                "retained_90d": None,
                "retained_180d": None,
                "retained_360d": None,
                "total_edits": None,
                "active_months": None,
                "first_post_activity_edit": None,
                "last_post_activity_edit": None,
            }

            retention_category = None

        else:
            status = "ok"
            reactivation_status = None

            experience_type = classify_experience_type(
                registration_date=metadata["registration_date"],
                reference_date=request.reference_date,
                newbie_threshold_days=request.newbie_threshold_days
            )

            contributions = get_user_contributions(
                username=metadata["username"],
                wiki=request.wiki,
                start_timestamp=post_event_start_timestamp,
                end_timestamp=post_event_end_timestamp,
                namespace=0,
            )

            retention_metrics = calculate_retention_metrics(
                contributions=contributions,
                reference_date=request.reference_date,
                retention_windows=request.retention_windows,
            )

            pre_event_edits = None

            reactivation_status = None

            if experience_type == "existing_user":
                existing_users += 1

                pre_event_edits = count_pre_event_edits(
                    username=metadata["username"],
                    wiki=request.wiki,
                    reference_date=request.reference_date,
                    reactivation_threshold_days=request.reactivation_threshold_days,
                )

                if pre_event_edits == 0 and retention_metrics["total_edits"] > 0:
                    reactivation_status = "reactivated"
                    reactivated_editors += 1
                else:
                    reactivation_status = "not_reactivated"

            elif experience_type == "newbie":
                newbies += 1

            else:
                unknown_experience += 1

            retention_category = classify_retention_category(
                total_edits=retention_metrics["total_edits"],
                active_months=retention_metrics["active_months"],
                active_edit_threshold=request.active_edit_threshold,
                very_active_edit_threshold=request.very_active_edit_threshold,
            )

            for window in request.retention_windows:
                if retention_metrics.get(f"retained_{window}d"):
                    retained_counts[window] = retained_counts.get(window, 0) + 1

            if retention_metrics["total_edits"] >= request.active_edit_threshold:
                active_retained_users += 1

            if retention_metrics["active_months"] >= 2:
                sustained_retained_users += 1

            if retention_category == "very_active_retained_user":
                very_active_retained_users += 1

        users.append({
            "username": metadata["username"],
            "status": status,
            "registration_date": metadata["registration_date"],
            "experience_type": experience_type,
            "account_type": experience_type,
            "reactivation_status": reactivation_status,
            "pre_event_edits_reactivation_window": pre_event_edits,
            "available_30d": retention_metrics["available_30d"],
            "available_90d": retention_metrics["available_90d"],
            "available_180d": retention_metrics["available_180d"],
            "available_360d": retention_metrics["available_360d"],
            "edits_30d": retention_metrics["edits_30d"],
            "edits_90d": retention_metrics["edits_90d"],
            "edits_180d": retention_metrics["edits_180d"],
            "edits_360d": retention_metrics["edits_360d"],
            "retained_30d": retention_metrics["retained_30d"],
            "retained_90d": retention_metrics["retained_90d"],
            "retained_180d": retention_metrics["retained_180d"],
            "retained_360d": retention_metrics["retained_360d"],
            "total_edits": retention_metrics["total_edits"],
            "active_months": retention_metrics["active_months"],
            "first_post_activity_edit": retention_metrics["first_post_activity_edit"],
            "last_post_activity_edit": retention_metrics["last_post_activity_edit"],
            "retention_category": retention_category,
        })

    valid_users = len(cleaned_usernames) - invalid_users - bot_users

    return {
        "metadata": {
            "wiki": request.wiki,
            "reference_date": str(request.reference_date),
            "retention_windows": request.retention_windows,
            "namespace": 0,
            "reactivation_threshold_days": request.reactivation_threshold_days,
        },
        "summary": {
            "total_users_submitted": len(request.usernames),
            "cleaned_users": len(cleaned_usernames),
            "duplicate_or_removed_usernames": duplicate_or_removed_usernames,
            "valid_users": valid_users,
            "invalid_users": invalid_users,
            "bot_users": bot_users,
            "newbies": newbies,
            "existing_users": existing_users,
            "reactivated_editors": reactivated_editors,
            "unknown_experience": unknown_experience,
            "retained_30d": build_retention_summary(
                window=30,
                retained_counts=retained_counts,
                valid_users=valid_users,
                reference_date=request.reference_date
            ),
            "retained_90d": build_retention_summary(
                window=90,
                retained_counts=retained_counts,
                valid_users=valid_users,
                reference_date=request.reference_date
            ),
            "retained_180d": build_retention_summary(
                window=180,
                retained_counts=retained_counts,
                valid_users=valid_users,
                reference_date=request.reference_date
            ),
            "retained_360d": build_retention_summary(
                window=360,
                retained_counts=retained_counts,
                valid_users=valid_users,
                reference_date=request.reference_date
            ),
            "active_retained_users": active_retained_users,
            "sustained_retained_users": sustained_retained_users,
            "very_active_retained_users": very_active_retained_users
        },
        "users": users
    }