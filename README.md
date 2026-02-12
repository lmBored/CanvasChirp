# CanvasChirp

Canvas LMS submission and comment monitoring

## Installation

### Prerequisites

- A Canvas LMS access token (from your Canvas account settings)

### Setup

Setup uv:
```bash
uv sync
```

Create a `token` file in the project root and paste your Canvas access token, or:
```bash
echo "your-canvas-api-token" > token
```

## Run

Before running the main script, you need to set constant for groups and fetch students group mapping:
```python
# For example "https://canvas.tue.nl/courses/32560/groups#tab-25446"
GROUP = 25446
```
```bash
uv run fetch_groups.py
```

Then, edit the constants in `main.py`:
```python
API = "https://canvas.tue.nl"
COURSE_ID = 32560
ASSIGNMENT_ID = 146386
```

Then, run the script:
```bash
uv run main.py
```

## Course comment notifier (Teams + GitHub Actions)

`notify_course_comments.py` monitors a single course and send only student-authored submission comments to a Teams channel via Teams Workflow Webhook alerts.

It uses `student_groups.json` to identify student authors, and keeps de-duplication state in a JSON file.

### Local run

Set required environment variables:

```bash
export CANVAS_COURSE_ID="32560"
export TEAMS_WEBHOOK_URL="https://..."
export CANVAS_TOKEN="your-canvas-token"
```

Optional variables:

```bash
export CANVAS_API_BASE="https://canvas.tue.nl"                 # default: https://canvas.tue.nl
export STUDENT_GROUPS_FILE="student_groups.json"               # default: student_groups.json
export STATE_FILE="state/course_comment_dedupe.json"           # default: state/course_comment_dedupe.json
export FIRST_RUN_BEHAVIOR="baseline"                           # baseline | notify
export DRY_RUN="false"                                         # true|false (no Teams post, no state writes)
```

Run:

```bash
uv run notify_course_comments.py
```

`FIRST_RUN_BEHAVIOR=baseline` (default) stores existing comments in state without posting them, then posts only future comments.

Safe local verification:

```bash
DRY_RUN=true uv run notify_course_comments.py
```

### GitHub Actions (daily run)

Workflow file: `.github/workflows/course-comments-to-teams.yml`

1. Add repository secrets:
	- `CANVAS_TOKEN`
	- `TEAMS_WEBHOOK_URL`
2. Add repository variable:
	- `CANVAS_COURSE_ID`
3. Optional repository variable:
	- `CANVAS_API_BASE` (defaults to `https://canvas.tue.nl` if unset)
4. Create and push the state branch once:

```bash
git switch -c canvas-notifier-state
git push -u origin canvas-notifier-state
git switch -
```

The workflow runs daily and on manual dispatch, then commits only the de-dup state file to `canvas-notifier-state` with `[skip ci]`.
