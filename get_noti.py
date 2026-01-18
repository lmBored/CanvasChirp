"""
Ever got a notification like "A new annotation has been made to your submission document", and it doesn't load when you open it?
This will fetch all notification like that.
"""

from canvasapi import Canvas
import requests
import sys
from datetime import datetime
sys.stdout.reconfigure(line_buffering=True)

API = "https://canvas.tue.nl"
TOKEN = "token"

def token():
    with open(TOKEN, "r") as f:
        return f.read().strip()

def main():
    api = token()
    canvas = Canvas(API, api)
    user = canvas.get_current_user()
    print(f"Checking notifications for: {user.name}\n")

    # Direct API call to get notifications
    headers = {'Authorization': f'Bearer {api}'}

    # Try the notification preferences endpoint
    notif_url = f"{API}/api/v1/users/self/communication_channels"
    response = requests.get(notif_url, headers=headers)
    print(f"Communication channels status: {response.status_code}\n")

    stream_url = f"{API}/api/v1/users/self/activity_stream"
    response = requests.get(stream_url, headers=headers)

    if response.status_code == 200:
        activities = response.json()
        print(f"Found {len(activities)} recent activities:\n")

        for activity in activities:
            if 'annotation' in str(activity).lower():
                print(f"Type: {activity.get('type')}")
                print(f"Title: {activity.get('title')}")
                print(f"Created: {activity.get('created_at')}")
                print(f"Link: {activity.get('html_url')}")
                # print(activity)
                print("-" * 60)
    else:
        print(f"Could not fetch activity stream: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    main()
