from canvasapi import Canvas
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib import error as url_error
from urllib import request as url_request

sys.stdout.reconfigure(line_buffering=True)

DEFAULT_API_BASE = "https://canvas.tue.nl"
DEFAULT_TOKEN_FILE = "token"
DEFAULT_GROUPS_FILE = "student_groups.json"
DEFAULT_STATE_FILE = "state/course_comment_dedupe.json"


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def get_canvas_token() -> str:
    env_token = os.getenv("CANVAS_TOKEN", "").strip()
    if env_token:
        return env_token

    token_file = os.getenv("CANVAS_TOKEN_FILE", DEFAULT_TOKEN_FILE)
    with open(token_file, "r", encoding="utf-8") as file:
        token = file.read().strip()
    if not token:
        raise ValueError("Canvas token is empty")
    return token


def load_groups(groups_file: str) -> dict[str, str]:
    with open(groups_file, "r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("student_groups.json must contain a JSON object")
    return {str(key): str(value) for key, value in data.items()}


def load_state(state_file: str) -> tuple[dict, bool]:
    path = Path(state_file)
    if not path.exists():
        return {"version": 1, "seen": {}}, False

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    seen = payload.get("seen", {}) if isinstance(payload, dict) else {}
    if not isinstance(seen, dict):
        seen = {}
    return {"version": 1, "seen": seen}, True


def save_state(state_file: str, state: dict) -> None:
    path = Path(state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)
        file.write("\n")
    tmp_path.replace(path)


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split())


def is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def make_comment_key(
    course_id: int,
    assignment_id: int | None,
    submission_user_id: int | None,
    comment: dict,
) -> str:
    comment_id = comment.get("id")
    if comment_id is not None:
        canonical = {
            "course_id": course_id,
            "assignment_id": assignment_id,
            "submission_user_id": submission_user_id,
            "comment_id": comment_id,
        }
    else:
        canonical = {
            "course_id": course_id,
            "assignment_id": assignment_id,
            "submission_user_id": submission_user_id,
            "author_id": comment.get("author_id"),
            "created_at": comment.get("created_at"),
            "comment": normalize_text(comment.get("comment")),
        }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_teams_text(event: dict) -> str:
    lines = [
        "New Canvas student comment",
        f"Course: {event['course_name']} (ID: {event['course_id']})",
        f"Assignment: {event['assignment_name']} (ID: {event['assignment_id']})",
        f"Author: {event['author_name']} (ID: {event['author_id']})",
        f"Group: {event['group_name']}",
        f"Created: {event['created_at'] or 'unknown'}",
        "Comment:",
        event['comment_text'] or "(empty)",
    ]
    if event.get("assignment_url"):
        lines.append(f"Assignment link: {event['assignment_url']}")
    return "\n".join(lines)


def post_to_teams(webhook_url: str, text: str, timeout_seconds: int = 20, max_retries: int = 3) -> bool:
    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": "Canvas student comment",
        "text": text,
    }
    request = url_request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for attempt in range(1, max_retries + 1):
        try:
            with url_request.urlopen(request, timeout=timeout_seconds) as response:
                if 200 <= response.getcode() < 300:
                    return True
                print(f"Teams webhook returned HTTP {response.getcode()}")
        except url_error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            body = exc.read().decode("utf-8", errors="replace")
            print(f"Teams webhook failed with HTTP {exc.code}: {body}")
            return False
        except url_error.URLError as exc:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            print(f"Teams webhook request failed: {exc}")
            return False
    return False


def collect_candidate_events(course, group_map: dict[str, str]) -> list[dict]:
    events = []
    for assignment in course.get_assignments():
        assignment_id = getattr(assignment, "id", None)
        assignment_name = getattr(assignment, "name", f"Assignment {assignment_id}")
        assignment_url = getattr(assignment, "html_url", None)

        try:
            submissions = assignment.get_submissions(include=["submission_comments", "user"])
        except Exception as exc:
            print(f"Failed to fetch submissions for assignment {assignment_id}: {exc}")
            continue

        for submission in submissions:
            submission_user_id = getattr(submission, "user_id", None)
            comments = getattr(submission, "submission_comments", None) or []

            for comment in comments:
                author_id = comment.get("author_id")
                if author_id is None:
                    continue

                author_key = str(author_id)
                if author_key not in group_map:
                    continue

                events.append(
                    {
                        "course_id": getattr(course, "id", None),
                        "course_name": getattr(course, "name", "Unknown course"),
                        "assignment_id": assignment_id,
                        "assignment_name": assignment_name,
                        "assignment_url": assignment_url,
                        "submission_user_id": submission_user_id,
                        "author_id": author_id,
                        "author_name": comment.get("author_name") or f"User {author_id}",
                        "group_name": group_map.get(author_key, "No Group"),
                        "created_at": comment.get("created_at"),
                        "comment_text": comment.get("comment") or "",
                        "comment": comment,
                    }
                )

    events.sort(key=lambda item: item.get("created_at") or "")
    return events


def main() -> None:
    api_base = os.getenv("CANVAS_API_BASE", DEFAULT_API_BASE).strip() or DEFAULT_API_BASE
    course_id = int(require_env("CANVAS_COURSE_ID"))
    webhook_url = require_env("TEAMS_WEBHOOK_URL")
    groups_file = os.getenv("STUDENT_GROUPS_FILE", DEFAULT_GROUPS_FILE)
    state_file = os.getenv("STATE_FILE", DEFAULT_STATE_FILE)
    first_run_behavior = os.getenv("FIRST_RUN_BEHAVIOR", "baseline").strip().lower()
    dry_run = is_truthy(os.getenv("DRY_RUN"))

    token = get_canvas_token()
    group_map = load_groups(groups_file)
    state, state_exists = load_state(state_file)
    seen = state.get("seen", {})

    canvas = Canvas(api_base, token)
    current_user = canvas.get_current_user()
    course = canvas.get_course(course_id)
    print(f"Canvas user: {current_user.name} ({current_user.id})")
    print(f"Course: {course.name} ({course.id})")

    candidates = collect_candidate_events(course, group_map)
    unseen = []
    for event in candidates:
        key = make_comment_key(
            course_id=course.id,
            assignment_id=event.get("assignment_id"),
            submission_user_id=event.get("submission_user_id"),
            comment=event["comment"],
        )
        event["key"] = key
        if key not in seen:
            unseen.append(event)

    if dry_run:
        print(f"DRY_RUN enabled. {len(unseen)} comments would be sent to Teams.")
        for event in unseen:
            print(
                f"- {event.get('created_at') or 'unknown'} | "
                f"{event.get('assignment_name')} | "
                f"{event.get('author_name')}"
            )
        return

    if not state_exists and first_run_behavior == "baseline":
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for event in unseen:
            seen[event["key"]] = {
                "created_at": event.get("created_at"),
                "assignment_id": event.get("assignment_id"),
                "author_id": event.get("author_id"),
                "saved_at": now,
            }
        save_state(state_file, state)
        print(f"First run baseline complete. Added {len(unseen)} existing comments to state.")
        return

    sent = 0
    for event in unseen:
        text = build_teams_text(event)
        success = post_to_teams(webhook_url, text)
        if not success:
            continue

        seen[event["key"]] = {
            "created_at": event.get("created_at"),
            "assignment_id": event.get("assignment_id"),
            "author_id": event.get("author_id"),
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        sent += 1

    if sent > 0 or (not state_exists and not unseen):
        save_state(state_file, state)

    print(f"Detected {len(unseen)} new student comments. Sent {sent} to Teams.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc)
        sys.exit(1)