"""Сжать и разжать кулак (FlexChallenge): защита от фото, даже если телефон двигают."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import MaxsgMuss  # noqa: E402
from hand import gesture_points, make_points  # noqa: E402

FPS = 30
HALF_BENT = (True, False, True, False)  # Пальцы в движении: жест не распознаётся.


def feed(challenge, plan):
    """plan — список (что в кадре, секунды[, cx]).

    "palm"/"fist" — жест; "bend" — рука в кадре, но жест не распознан;
    "none" — руки в кадре нет.
    """
    now, done = 100.0, False
    for item in plan:
        state, seconds = item[0], item[1]
        cx = item[2] if len(item) > 2 else 0.5
        for _ in range(max(1, round(seconds * FPS))):
            now += 1 / FPS
            if state == "none":
                points, gesture = None, None
            elif state == "bend":
                points, gesture = make_points(HALF_BENT, cx=cx), None
            else:
                points, gesture = gesture_points(state, cx=cx), state
            done = challenge.add(points, gesture, now) or done
    return done


def flexes(times, pause=0.5, between=0.15):
    """Ладонь, затем times раз: кулак, ладонь… с полусогнутыми кадрами между ними."""
    plan, state = [("palm", pause)], "palm"
    for _ in range(times):
        state = "fist" if state == "palm" else "palm"
        plan += [("bend", between), (state, pause)]
    return plan


class FlexChallengeTest(unittest.TestCase):
    def test_two_full_flexes_pass(self):
        self.assertTrue(feed(MaxsgMuss.FlexChallenge(), flexes(4)))

    def test_three_changes_are_not_enough(self):
        challenge = MaxsgMuss.FlexChallenge()
        self.assertFalse(feed(challenge, flexes(3)))
        self.assertAlmostEqual(challenge.progress(), 0.75)

    def test_still_photo_never_passes(self):
        self.assertFalse(feed(MaxsgMuss.FlexChallenge(), [("palm", 5.0)]))

    def test_hand_lost_resets_progress(self):
        # Так выглядит листание фото: рука на мгновение пропадает.
        challenge = MaxsgMuss.FlexChallenge()
        plan = flexes(2) + [("none", 0.5)] + [("fist", 0.5), ("bend", 0.15), ("palm", 0.5)]
        self.assertFalse(feed(challenge, plan))
        self.assertIn("пропала", challenge.reset_reason)

    def test_short_dropout_is_tolerated(self):
        plan = flexes(2) + [("none", 0.1)] + [("bend", 0.1), ("fist", 0.5), ("bend", 0.15), ("palm", 0.5)]
        self.assertTrue(feed(MaxsgMuss.FlexChallenge(), plan))

    def test_too_slow_resets(self):
        self.assertFalse(feed(MaxsgMuss.FlexChallenge(), flexes(4, pause=2.0)))

    def test_teleport_resets(self):
        # Центр руки резко прыгнул — другая картинка, а не та же рука.
        challenge = MaxsgMuss.FlexChallenge()
        plan = flexes(2) + [("fist", 0.5, 0.15), ("bend", 0.15, 0.15), ("palm", 0.5, 0.15)]
        self.assertFalse(feed(challenge, plan))
        self.assertIn("скачк", challenge.reset_reason)

    def test_can_succeed_after_reset(self):
        plan = flexes(2) + [("none", 0.6)] + flexes(4)
        self.assertTrue(feed(MaxsgMuss.FlexChallenge(), plan))

    def test_thumb_sticking_out_still_counts_as_fist(self):
        plan = [("palm", 0.5)]
        for state in ("thumbs_up", "palm", "fist", "palm"):
            plan += [("bend", 0.15), (state, 0.5)]
        self.assertTrue(feed(MaxsgMuss.FlexChallenge(), plan))

    def test_other_gestures_do_not_count(self):
        plan = [("palm", 0.5), ("peace", 0.5), ("palm", 0.5), ("peace", 0.5), ("palm", 0.5)]
        self.assertFalse(feed(MaxsgMuss.FlexChallenge(), plan))


if __name__ == "__main__":
    unittest.main()
