"""Жест в движении (MotionChallenge): защита от фотографии руки."""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import MaxsgMuss  # noqa: E402
from hand import gesture_points  # noqa: E402

FPS = 30


class MotionChallengeTest(unittest.TestCase):
    def feed(self, challenge, centers, duration):
        """centers — функция t → (cx, wrist_y); duration — секунды движения."""
        done = False
        frames = int(duration * FPS)
        for i in range(frames + 1):
            t = i / FPS
            cx, wy = centers(t / duration if duration else 1)
            done = challenge.add(gesture_points("palm", cx=cx, wrist_y=wy), 100 + t) or done
        return done

    def test_every_motion_has_a_description(self):
        for kind in ("left", "right", "up", "wave"):
            self.assertIn(kind, MaxsgMuss.MOTIONS)

    def test_move_left(self):
        challenge = MaxsgMuss.MotionChallenge("left")
        self.assertTrue(self.feed(challenge, lambda k: (0.65 - 0.3 * k, 0.8), 1.0))

    def test_move_right(self):
        challenge = MaxsgMuss.MotionChallenge("right")
        self.assertTrue(self.feed(challenge, lambda k: (0.35 + 0.3 * k, 0.8), 1.0))

    def test_wrong_direction_does_not_count(self):
        challenge = MaxsgMuss.MotionChallenge("left")
        self.assertFalse(self.feed(challenge, lambda k: (0.35 + 0.3 * k, 0.8), 1.0))

    def test_move_up(self):
        challenge = MaxsgMuss.MotionChallenge("up")
        self.assertTrue(self.feed(challenge, lambda k: (0.5, 0.9 - 0.3 * k), 1.0))

    def test_too_slow_does_not_count(self):
        # 0,25 кадра за 6 секунд: в окно 3 с попадает только половина пути.
        challenge = MaxsgMuss.MotionChallenge("left")
        self.assertFalse(self.feed(challenge, lambda k: (0.65 - 0.25 * k, 0.8), 6.0))

    def test_wave(self):
        def wave(k):
            # Два с половиной взмаха: вправо-влево-вправо-влево.
            phase = (k * 5) % 2
            x = 0.42 + 0.16 * (phase if phase <= 1 else 2 - phase)
            return x, 0.8
        challenge = MaxsgMuss.MotionChallenge("wave")
        self.assertTrue(self.feed(challenge, wave, 2.0))

    def test_wave_around_the_starting_point(self):
        # Рука сначала стоит в центре, потом машет вокруг него на ±0,075.
        # Каждый взмах длиной 0,15 — это настоящие взмахи, хотя от стартовой
        # точки рука отходит меньше чем на WAVE_AMPLITUDE (0,08).
        challenge = MaxsgMuss.MotionChallenge("wave")
        self.feed(challenge, lambda k: (0.5, 0.8), 1.0)

        def wave(k):
            phase = (k * 5 + 0.5) % 2
            return 0.425 + 0.15 * (phase if phase <= 1 else 2 - phase), 0.8
        self.assertTrue(self.feed(challenge, wave, 2.0))

    def test_small_jitter_is_not_a_wave(self):
        rng = random.Random(4)
        challenge = MaxsgMuss.MotionChallenge("wave")
        self.assertFalse(self.feed(challenge, lambda k: (0.5 + rng.uniform(-0.02, 0.02), 0.8), 2.0))

    def test_progress_grows_with_movement(self):
        challenge = MaxsgMuss.MotionChallenge("left")
        self.assertEqual(challenge.progress(), 0)
        self.feed(challenge, lambda k: (0.6 - 0.1 * k, 0.8), 0.5)
        self.assertGreater(challenge.progress(), 0.3)
        self.assertLess(challenge.progress(), 1)


if __name__ == "__main__":
    unittest.main()
