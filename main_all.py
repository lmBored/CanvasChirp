from canvasapi import Canvas
import sys
import json
sys.stdout.reconfigure(line_buffering=True)

API = "https://canvas.tue.nl"
TOKEN = "token"
GFILE = "student_groups.json"

def token():
    with open(TOKEN, "r") as f:
        return f.read().strip()

def get_group():
    with open(GFILE, "r") as f:
        return json.load(f)


def fetch_courses(canvas, include_concluded=True, state="available"):
    if include_concluded:
        # https://canvas.instructure.com/doc/api/courses.html#method.courses.index
        try:
            return list(canvas.get_courses(state=[state]))
        except TypeError:
            pass
    return list(canvas.get_courses())


def select_course(courses, input_fn=input, print_fn=print):
    if not courses:
        return None

    print_fn("\nAvailable courses:")
    for idx, course in enumerate(courses, start=1):
        course_name = getattr(course, "name", f"Course {idx}")
        course_id = getattr(course, "id", "?")
        print_fn(f"{idx}. {course_name} (ID: {course_id})")

    while True:
        choice = input_fn("Select a course by number: ").strip()
        selected_index = int(choice)
        if 1 <= selected_index <= len(courses):
            return courses[selected_index - 1]
        print_fn("Wrong input")

def main():
    api = token()
    try:
        canvas = Canvas(API, api)

        print(f"{canvas.get_current_user().name} - {canvas.get_current_user().id}")

        # choice = input("Completed (1) or available course (2): ").strip()
        # if choice == "1":
        #     courses = fetch_courses(canvas, include_concluded=True, state="completed")
        # elif choice == "2":
        #     courses = fetch_courses(canvas, include_concluded=True, state="available")
        # else:
        #     print("Wrong input")
        #     return
        courses = fetch_courses(canvas, include_concluded=True, state="available")

        if not courses:
            print("No courses found.")
            return

        course = select_course(courses)
        if course is None:
            print("No course selected.")
            return

        print(f"Course: {course.name}")

        group = get_group()
        ass = course.get_assignments()
        for a in ass:
            print("======================================================================")
            print(f"Assignment: {a.name}")
            sub = a.get_submissions(include=["submission_comments", "user"])
            count = 0
            for s in sub:
                if (hasattr(s, "submission_comments") and s.submission_comments):
                    if hasattr(s, "user"):
                        student_name = getattr(s.user, "name", f"Student {s.user_id}")
                    group_name = group.get(str(s.user_id), "No Group")

                    # https://canvas.instructure.com/doc/api/submissions.html#SubmissionComment
                    for c in s.submission_comments:
                        aid = c.get("author_id")
                        if str(aid) not in group: # O(1)
                            continue

                        print("----------------------------------")
                        print(f"Student: {student_name}, ID: {s.user_id}, Group: {group_name}")
                        author_name = c.get("author_name")
                        comment = c.get("comment")
                        created_at = c.get("created_at")
                        print(f"{created_at} - {author_name}:")
                        print(f"{comment}")
                    count += 1
            if count == 0:
                print("\nNo submission comments.")
            else:
                print(f"\n{count} comments\n")

    except Exception as e:
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
