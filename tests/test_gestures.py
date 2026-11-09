"""Проверки распознавания жестов recognize_gesture() без камеры."""

import math
import os
import sys
import unittest
from types import SimpleNamespace

# Тесты лежат в tests/, а программа — на уровень выше.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import MaxsgMuss  # noqa: E402  Импорт не включает камеру: библиотеки грузятся только в __main__.
from hand import PATTERNS, gesture_points, make_points  # noqa: E402

recognize = MaxsgMuss.recognize_gesture


def mirrored(points):
    """Отражает кисть по горизонтали — как левая рука вместо правой."""
    return [SimpleNamespace(x=1 - p.x, y=p.y) for p in points]


class RecognizeGestureTest(unittest.TestCase):
    def test_all_seven_gestures(self):
        for name in MaxsgMuss.GESTURES:
            with self.subTest(gesture=name):
                self.assertEqual(recognize(gesture_points(name)), name)

    def test_helper_covers_every_gesture(self):
        self.assertEqual(set(PATTERNS), set(MaxsgMuss.GESTURES))

    def test_mirrored_hand(self):
        for name in MaxsgMuss.GESTURES:
            with self.subTest(gesture=name):
                self.assertEqual(recognize(mirrored(gesture_points(name))), name)

    def test_unsupported_combination(self):
        # Поднят только средний палец — такого жеста в программе нет.
        self.assertIsNone(recognize(make_points((False, True, False, False))))

    def test_incomplete_points(self):
        self.assertIsNone(recognize(gesture_points("palm")[:20]))
        self.assertIsNone(recognize([]))

    def test_hand_cut_by_frame_edge(self):
        points = gesture_points("palm")
        points[8] = SimpleNamespace(x=points[8].x, y=0.01)
        self.assertIsNone(recognize(points))

    def test_hand_too_small(self):
        self.assertIsNone(recognize(gesture_points("palm", palm=0.05)))

    def test_hand_tilted(self):
        points = gesture_points("palm")
        points[9] = SimpleNamespace(x=points[0].x + 0.2, y=points[9].y)
        self.assertIsNone(recognize(points))

    def test_upside_down_hand(self):
        points = [SimpleNamespace(x=p.x, y=1 - p.y) for p in gesture_points("palm")]
        self.assertIsNone(recognize(points))

    def test_half_bent_finger_is_not_counted(self):
        points = gesture_points("palm")
        points[12] = SimpleNamespace(x=points[12].x, y=points[10].y - 0.001)
        self.assertIsNone(recognize(points))

    def test_not_a_number_coordinates(self):
        points = gesture_points("palm")
        points[5] = SimpleNamespace(x=math.nan, y=math.nan)
        self.assertIsNone(recognize(points))


if __name__ == "__main__":
    unittest.main()
