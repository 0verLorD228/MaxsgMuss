"""Защита от перебора: растущая пауза (Lockout) и подсчёт неверных жестов."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import MaxsgMuss  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 1_700_000_000.0

    def __call__(self):
        return self.now


class LockoutTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "MaxsgMuss", "lockout.json")
        self.clock = FakeClock()

    def tearDown(self):
        self.folder.cleanup()

    def make(self):
        return MaxsgMuss.Lockout(self.path, clock=self.clock)

    def errors(self, lockout, count):
        pauses = [lockout.add_error() for _ in range(count)]
        return [p for p in pauses if p]

    def test_fresh_start_is_not_locked(self):
        lockout = self.make()
        self.assertEqual(lockout.remaining(), 0)
        self.assertEqual(lockout.errors_left(), 5)

    def test_four_errors_do_not_lock(self):
        lockout = self.make()
        self.assertEqual(self.errors(lockout, 4), [])
        self.assertEqual(lockout.errors_left(), 1)

    def test_pauses_grow(self):
        lockout = self.make()
        expected = [10, 30, 60, 60]
        for pause in expected:
            self.assertEqual(self.errors(lockout, 5), [pause])
            self.assertAlmostEqual(lockout.remaining(), pause)
            self.clock.now += pause  # Ждём окончания паузы.
            self.assertEqual(lockout.remaining(), 0)

    def test_success_resets_everything(self):
        lockout = self.make()
        self.errors(lockout, 5)
        self.clock.now += 10
        lockout.success()
        self.assertEqual(lockout.errors_left(), 5)
        self.assertEqual(self.errors(lockout, 5), [10])  # Снова с первой ступени.

    def test_restart_keeps_the_pause(self):
        self.errors(self.make(), 5)
        self.clock.now += 4
        restarted = self.make()  # Как будто программу закрыли и открыли снова.
        self.assertAlmostEqual(restarted.remaining(), 6)

    def test_restart_keeps_the_error_count(self):
        self.errors(self.make(), 3)
        self.assertEqual(self.make().errors_left(), 2)

    def test_corrupted_file_starts_from_zero(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as file:
            file.write("{не json")
        lockout = self.make()
        self.assertEqual(lockout.remaining(), 0)
        self.assertEqual(lockout.errors_left(), 5)

    def test_wrong_types_in_file_start_from_zero(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"errors": "много", "level": None, "locked_until": [1]}, file)
        self.assertEqual(self.make().errors_left(), 5)

    def test_pause_is_never_longer_than_maximum(self):
        # Если часы перевели назад или файл подправили, бесконечной блокировки нет.
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"errors": 5, "level": 1, "locked_until": self.clock.now + 999999}, file)
        self.assertLessEqual(self.make().remaining(), 60)

    def test_unwritable_place_does_not_crash(self):
        blocker = os.path.join(self.folder.name, "file")
        open(blocker, "w").close()  # Папку с таким именем создать нельзя.
        lockout = MaxsgMuss.Lockout(os.path.join(blocker, "lockout.json"), clock=self.clock)
        self.assertEqual(self.errors(lockout, 5), [10])

    def test_file_has_only_numbers(self):
        self.errors(self.make(), 2)
        with open(self.path, encoding="utf-8") as file:
            data = json.load(file)
        self.assertEqual(set(data), {"errors", "level", "locked_until"})


class WrongGestureFilterTest(unittest.TestCase):
    def run_frames(self, frames, target="palm"):
        """frames — список (жест, секунды); возвращает число засчитанных ошибок."""
        wrong = MaxsgMuss.WrongGestureFilter()
        now, count = 0.0, 0
        for gesture, seconds in frames:
            for _ in range(int(seconds * 30)):
                now += 1 / 30
                count += wrong.update(gesture, target, now)
        return count

    def test_stable_wrong_gesture_counts_once(self):
        self.assertEqual(self.run_frames([("fist", 3.0)]), 1)

    def test_short_flash_does_not_count(self):
        self.assertEqual(self.run_frames([("fist", 0.3)]), 0)

    def test_flicker_does_not_count(self):
        self.assertEqual(self.run_frames([("fist", 0.3), (None, 0.1), ("fist", 0.3)]), 0)

    def test_each_new_wrong_gesture_counts(self):
        self.assertEqual(self.run_frames([("fist", 0.7), ("peace", 0.7), ("rock", 0.7)]), 3)

    def test_target_gesture_is_not_an_error(self):
        self.assertEqual(self.run_frames([("palm", 3.0)]), 0)

    def test_same_wrong_gesture_after_pause_counts_again(self):
        self.assertEqual(self.run_frames([("fist", 0.7), (None, 0.3), ("fist", 0.7)]), 2)


if __name__ == "__main__":
    unittest.main()
