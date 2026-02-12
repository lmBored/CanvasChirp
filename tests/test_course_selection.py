import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main_all as main


class TestCourseSelection(unittest.TestCase):
    def test_list_courses_includes_concluded_when_requested(self):
        canvas = Mock()
        expected_courses = [
            SimpleNamespace(id=10, name="Course A"),
            SimpleNamespace(id=11, name="Course B"),
        ]
        canvas.get_courses.return_value = iter(expected_courses)

        courses = main.fetch_courses(canvas, include_concluded=True, state="completed")

        self.assertEqual(courses, expected_courses)
        canvas.get_courses.assert_called_once_with(state=["completed"])

    def test_select_course_by_valid_index(self):
        courses = [
            SimpleNamespace(id=20, name="Course X"),
            SimpleNamespace(id=21, name="Course Y"),
        ]
        inputs = iter(["2"])

        selected = main.select_course(
            courses,
            input_fn=lambda _: next(inputs),
            print_fn=lambda *args, **kwargs: None,
        )

        self.assertIs(selected, courses[1])

    def test_select_course_reprompts_on_invalid_input(self):
        courses = [
            SimpleNamespace(id=30, name="Course 1"),
            SimpleNamespace(id=31, name="Course 2"),
        ]
        inputs = iter(["abc", "0", "3", "1"])
        output = []

        selected = main.select_course(
            courses,
            input_fn=lambda _: next(inputs),
            print_fn=lambda message="", *args, **kwargs: output.append(str(message)),
        )

        self.assertIs(selected, courses[0])
        self.assertGreaterEqual(
            sum("Invalid selection" in line for line in output),
            1,
        )

    def test_fetch_courses_falls_back_when_enrollment_state_unsupported(self):
        canvas = Mock()
        expected_courses = [
            SimpleNamespace(id=40, name="Course C"),
            SimpleNamespace(id=41, name="Course D"),
        ]

        def get_courses(*args, **kwargs):
            # simulate that passing any keyword (state/enrollment_state) is unsupported
            if "state" in kwargs or "enrollment_state" in kwargs:
                raise TypeError("Unexpected keyword")
            return iter(expected_courses)

        canvas.get_courses.side_effect = get_courses

        courses = main.fetch_courses(canvas, include_concluded=True, state="completed")

        self.assertEqual(courses, expected_courses)
        # first attempt: state=[...], second: enrollment_state=..., final fallback: bare get_courses()
        self.assertEqual(canvas.get_courses.call_count, 3)
        canvas.get_courses.assert_any_call(state=["completed"])
        canvas.get_courses.assert_any_call(enrollment_state="completed")
        canvas.get_courses.assert_any_call()

    def test_select_course_returns_none_for_empty_course_list(self):
        selected = main.select_course(
            [],
            input_fn=lambda _: self.fail("input() should not be called for empty course list"),
            print_fn=lambda *args, **kwargs: None,
        )

        self.assertIsNone(selected)

    @patch("main_all.get_group", return_value={})
    @patch("main_all.select_course")
    @patch("main_all.fetch_courses")
    @patch("main_all.token", return_value="fake-token")
    @patch("main_all.Canvas")
    def test_main_handles_missing_assignment_for_selected_course(
        self,
        mock_canvas_class,
        mock_token,
        mock_fetch_courses,
        mock_select_course,
        mock_get_group,
    ):
        course = SimpleNamespace(id=50, name="Course Z")

        def raise_missing_assignment(_assignment_id):
            raise main.ResourceDoesNotExist("Missing assignment")

        course.get_assignment = raise_missing_assignment

        canvas = Mock()
        canvas.get_current_user.return_value = SimpleNamespace(name="Tester", id=123)
        mock_canvas_class.return_value = canvas
        mock_fetch_courses.return_value = [course]
        mock_select_course.return_value = course

        output = []
        with patch("builtins.input", return_value="2"):
            with patch("builtins.print", side_effect=lambda *args, **kwargs: output.append(" ".join(str(a) for a in args))):
                main.main()

        self.assertTrue(any("Course: Course Z" in line for line in output))
        self.assertTrue(
            any(
                "Assignment ID" in line and "not found" in line
                for line in output
            )
        )


@patch("main.fetch_courses")
@patch("main.select_course", return_value=None)
@patch("main.token", return_value="fake-token")
@patch("main.Canvas")
def test_main_menu_choice_completed_calls_fetch(self, mock_canvas_class, mock_token, mock_select_course, mock_fetch_courses):
    canvas = Mock()
    canvas.get_current_user.return_value = SimpleNamespace(name="Tester", id=123)
    mock_canvas_class.return_value = canvas
    mock_fetch_courses.return_value = []
    with patch("builtins.input", return_value="1"):
        main.main()
    mock_fetch_courses.assert_called_once_with(canvas, include_concluded=True, state="completed")


@patch("main.fetch_courses")
@patch("main.select_course", return_value=None)
@patch("main.token", return_value="fake-token")
@patch("main.Canvas")
def test_main_menu_choice_active_calls_fetch(self, mock_canvas_class, mock_token, mock_select_course, mock_fetch_courses):
    canvas = Mock()
    canvas.get_current_user.return_value = SimpleNamespace(name="Tester", id=123)
    mock_canvas_class.return_value = canvas
    mock_fetch_courses.return_value = []
    with patch("builtins.input", return_value="2"):
        main.main()
    mock_fetch_courses.assert_called_once_with(canvas, include_concluded=True, state="available")


@patch("main.fetch_courses")
@patch("main.token", return_value="fake-token")
@patch("main.Canvas")
def test_main_menu_invalid_choice(self, mock_canvas_class, mock_token, mock_fetch_courses):
    canvas = Mock()
    canvas.get_current_user.return_value = SimpleNamespace(name="Tester", id=123)
    mock_canvas_class.return_value = canvas
    with patch("builtins.input", return_value="x"):
        output = []
        with patch("builtins.print", side_effect=lambda *args, **kwargs: output.append(" ".join(str(a) for a in args))):
            main.main()
    self.assertTrue(any("Invalid selection. Enter 1 or 2." in line for line in output))
    mock_fetch_courses.assert_not_called()

if __name__ == "__main__":
    unittest.main()