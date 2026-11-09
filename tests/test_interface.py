"""Логика интерфейса без окна: уровни сложности, подсказки, картинки жестов."""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import MaxsgMuss  # noqa: E402
from hand import gesture_points, make_points  # noqa: E402


def first(options):
    """Вместо случайного выбора — всегда первый вариант, чтобы тест был предсказуемым."""
    return list(options)[0]


class DifficultyTest(unittest.TestCase):
    def test_three_levels(self):
        self.assertEqual(list(MaxsgMuss.DIFFICULTY), ["Лёгкий", "Средний", "Сложный"])
        self.assertIn(MaxsgMuss.DEFAULT_DIFFICULTY, MaxsgMuss.DIFFICULTY)

    def test_easy_is_one_gesture(self):
        steps = MaxsgMuss.build_steps("Лёгкий", first)
        self.assertEqual([kind for kind, _ in steps], ["gesture"])

    def test_medium_adds_flex(self):
        steps = MaxsgMuss.build_steps("Средний", first)
        self.assertEqual([kind for kind, _ in steps], ["gesture", "flex"])

    def test_hard_adds_motion(self):
        steps = MaxsgMuss.build_steps("Сложный", first)
        self.assertEqual([kind for kind, _ in steps], ["gesture", "flex", "motion"])
        self.assertIn(steps[2][1], MaxsgMuss.MOTIONS)

    def test_new_gesture_differs_from_previous(self):
        previous = first(MaxsgMuss.GESTURES)
        steps = MaxsgMuss.build_steps("Средний", first, previous=previous)
        self.assertNotEqual(steps[0][1], previous)

    def test_hard_is_stricter(self):
        easy, hard = MaxsgMuss.DIFFICULTY["Лёгкий"], MaxsgMuss.DIFFICULTY["Сложный"]
        self.assertGreater(easy["time"], hard["time"])
        self.assertGreater(hard["hold"], easy["hold"])


class GestureProblemTest(unittest.TestCase):
    """gesture_problem() объясняет, почему recognize_gesture() вернула None."""

    def assertProblem(self, points, word):
        self.assertIsNone(MaxsgMuss.recognize_gesture(points))
        problem = MaxsgMuss.gesture_problem(points)
        self.assertIsNotNone(problem)
        self.assertIn(word, problem.lower())

    def test_no_problem_for_known_gestures(self):
        for name in MaxsgMuss.GESTURES:
            with self.subTest(gesture=name):
                self.assertIsNone(MaxsgMuss.gesture_problem(gesture_points(name)))

    def test_incomplete(self):
        self.assertProblem(gesture_points("palm")[:20], "не полностью")

    def test_edge(self):
        points = gesture_points("palm")
        points[8] = SimpleNamespace(x=points[8].x, y=0.01)
        self.assertProblem(points, "края")

    def test_far(self):
        self.assertProblem(gesture_points("palm", palm=0.04), "далеко")

    def test_upside_down(self):
        self.assertProblem([SimpleNamespace(x=p.x, y=1 - p.y) for p in gesture_points("palm")], "вверх")

    def test_tilted(self):
        points = gesture_points("palm")
        points[9] = SimpleNamespace(x=points[0].x + 0.2, y=points[9].y)
        self.assertProblem(points, "ровно")

    def test_half_bent_finger(self):
        points = gesture_points("palm")
        points[12] = SimpleNamespace(x=points[12].x, y=points[10].y - 0.001)
        self.assertProblem(points, "чётче")

    def test_unknown_combination(self):
        self.assertProblem(make_points((False, True, False, False)), "нет")


class GesturePictureTest(unittest.TestCase):
    def picture(self, kind, name):
        return MaxsgMuss.draw_gesture_picture(kind, name, MaxsgMuss.THEMES["dark"])

    def test_every_task_has_a_picture(self):
        tasks = [("gesture", g) for g in MaxsgMuss.GESTURES]
        tasks += [("motion", m) for m in MaxsgMuss.MOTIONS] + [("flex", "flex")]
        for kind, name in tasks:
            with self.subTest(task=name):
                image = self.picture(kind, name)
                self.assertEqual(image.size, (200, 200))
                visible = sum(1 for alpha in image.getchannel("A").getdata() if alpha)
                self.assertGreater(visible, 1500, "на картинке почти ничего не нарисовано")

    def test_different_gestures_look_different(self):
        pictures = {g: self.picture("gesture", g).tobytes() for g in MaxsgMuss.GESTURES}
        self.assertEqual(len(set(pictures.values())), len(pictures))

    def test_both_themes(self):
        dark = MaxsgMuss.draw_gesture_picture("gesture", "palm", MaxsgMuss.THEMES["dark"])
        light = MaxsgMuss.draw_gesture_picture("gesture", "palm", MaxsgMuss.THEMES["light"])
        self.assertNotEqual(dark.tobytes(), light.tobytes())


class ColorTest(unittest.TestCase):
    def test_hex_to_rgb(self):
        self.assertEqual(MaxsgMuss.hex_to_rgb("#22d3ee"), (0x22, 0xD3, 0xEE))

    def test_themes_have_same_keys(self):
        self.assertEqual(set(MaxsgMuss.THEMES["dark"]), set(MaxsgMuss.THEMES["light"]))


if __name__ == "__main__":
    unittest.main()
