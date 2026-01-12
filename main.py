from canvasapi import Canvas
import os
import sys
import json
sys.stdout.reconfigure(line_buffering=True)

API = "https://canvas.tue.nl"
TOKEN = "token"
COURSE_ID = 32560
ASSIGNMENT_ID = 146385
GFILE = "student_groups.json"

def token():
    with open(TOKEN, "r") as f:
        return f.read().strip()

def get_group():
    with open(GFILE, "r") as f:
        return json.load(f)

def main():
    api = token()
    try:
        canvas = Canvas(API, api)

        print(f"{canvas.get_current_user().name} - {canvas.get_current_user().id}")

        course = canvas.get_course(COURSE_ID)
        print(f"Course: {course.name}")

        group = get_group()
        ass = course.get_assignment(ASSIGNMENT_ID)
        print(f"Assignment: {ass.name}")

        sub = ass.get_submissions(include=["submission_comments", "user"])
        count = 0
        for s in sub:
            if (hasattr(s, "submission_comments") and s.submission_comments):
                if hasattr(s, "user"):
                    student_name = getattr(s.user, "name", f"Student {s.user_id}")
                group_name = group.get(str(s.user_id), "No Group")

                print(f"\nStudent: {student_name}, ID: {s.user_id}, Group: {group_name}")

                for c in s.submission_comments:
                    author_name = c.get("author_name")
                    comment = c.get("comment")
                    created_at = c.get("created_at")
                    print(f"{created_at} - {author_name}:")
                    print(f"{comment}")

                count += 1

        if count == 0:
            print("\nNo submission comments.")
        else:
            print(f"\n{count} comments")

    except Exception as e:
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
