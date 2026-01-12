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
