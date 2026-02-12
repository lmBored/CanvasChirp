import tempfile
import unittest
from pathlib import Path

import notify_course_comments as notifier


class TestNotifyCourseComments(unittest.TestCase):
    def test_is_truthy(self):
        self.assertTrue(notifier.is_truthy("1"))
        self.assertTrue(notifier.is_truthy("true"))
        self.assertTrue(notifier.is_truthy("YES"))
        self.assertFalse(notifier.is_truthy("0"))
        self.assertFalse(notifier.is_truthy("false"))
        self.assertFalse(notifier.is_truthy(None))

    def test_normalize_text_collapses_whitespace(self):
        self.assertEqual(notifier.normalize_text("  hello\n\tworld  "), "hello world")
        self.assertEqual(notifier.normalize_text(None), "")

    def test_make_comment_key_is_deterministic(self):
        comment = {
            "id": 99,
            "author_id": 120,
            "created_at": "2026-02-01T10:00:00Z",
            "comment": "Looks good",
        }
        key_one = notifier.make_comment_key(1, 2, 3, comment)
        key_two = notifier.make_comment_key(1, 2, 3, comment)
        self.assertEqual(key_one, key_two)

    def test_make_comment_key_prefers_comment_id_when_present(self):
        comment_one = {
            "id": 88,
            "author_id": 120,
            "created_at": "2026-02-01T10:00:00Z",
            "comment": "Initial text",
        }
        comment_two = {
            "id": 88,
            "author_id": 120,
            "created_at": "2026-02-01T11:00:00Z",
            "comment": "Edited text",
        }
        key_one = notifier.make_comment_key(1, 2, 3, comment_one)
        key_two = notifier.make_comment_key(1, 2, 3, comment_two)
        self.assertEqual(key_one, key_two)

    def test_make_comment_key_normalizes_fallback_text(self):
        comment_one = {
            "author_id": 120,
            "created_at": "2026-02-01T10:00:00Z",
            "comment": "Great   work",
        }
        comment_two = {
            "author_id": 120,
            "created_at": "2026-02-01T10:00:00Z",
            "comment": "Great work",
        }
        key_one = notifier.make_comment_key(1, 2, 3, comment_one)
        key_two = notifier.make_comment_key(1, 2, 3, comment_two)
        self.assertEqual(key_one, key_two)

    def test_build_teams_text_contains_core_fields(self):
        event = {
            "course_name": "Algorithms",
            "course_id": 42,
            "assignment_name": "Report",
            "assignment_id": 7,
            "author_name": "Student A",
            "author_id": 1001,
            "group_name": "Group 2",
            "created_at": "2026-02-02T11:30:00Z",
            "comment_text": "Please check section 3.",
            "assignment_url": "https://canvas.example/assignments/7",
        }
        text = notifier.build_teams_text(event)
        self.assertIn("Algorithms", text)
        self.assertIn("Report", text)
        self.assertIn("Student A", text)
        self.assertIn("Please check section 3.", text)

    def test_state_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            initial_state, exists = notifier.load_state(str(state_path))
            self.assertFalse(exists)
            self.assertEqual(initial_state.get("seen"), {})

            payload = {
                "version": 1,
                "seen": {
                    "k1": {
                        "created_at": "2026-02-02T11:30:00Z",
                        "assignment_id": 1,
                        "author_id": 2,
                        "saved_at": "2026-02-02T12:00:00Z",
                    }
                },
            }
            notifier.save_state(str(state_path), payload)

            loaded_state, exists_after = notifier.load_state(str(state_path))
            self.assertTrue(exists_after)
            self.assertIn("k1", loaded_state.get("seen", {}))


if __name__ == "__main__":
    unittest.main()