from canvasapi import Canvas
import os
import sys
import json
sys.stdout.reconfigure(line_buffering=True)

API = "https://canvas.tue.nl"
TOKEN = "token"
GROUP = 25446
FILE = "student_groups.json"

def token():
    with open(TOKEN, "r") as f:
        return f.read().strip()

def main():
    api = token()
    try:
        canvas = Canvas(API, api)
        cat = canvas.get_group_category(GROUP)
        groups = cat.get_groups()

        map = {}
        for g in groups:
            print(f"  Processing group: {g.name}...", end="\r")
            for u in g.get_users():
                map[str(u.id)] = g.name

        with open(FILE, "w") as f:
            json.dump(map, f, indent=2)

    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
