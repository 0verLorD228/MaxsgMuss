"""Проверка настоящего окна MaxsgMuss без веб-камеры.

Запуск: python tests/ui_smoke.py
Настоящие: CustomTkinter, OpenCV, отрисовка скелета MediaPipe.
Подменены: камера (рисованный кадр), нейросеть Hands (отдаёт заданные точки) и часы.
Скриншоты сохраняются в _shots/ (папка не попадает в git).
"""

import os
import random
import sys
import tempfile
import time as real_time
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2  # noqa: E402
import customtkinter as ctk  # noqa: E402
import mediapipe as mp  # noqa: E402
import numpy as np  # noqa: E402
from mediapipe.framework.formats import landmark_pb2  # noqa: E402
from PIL import Image, ImageGrab  # noqa: E402

import MaxsgMuss as app_module  # noqa: E402
from hand import gesture_points, make_points  # noqa: E402

SHOTS = os.path.join(ROOT, "_shots")
errors = []  # Исключения из обработчиков Tk.


class FakeClock:
    """Подменяет модуль time внутри программы: время идёт, только когда мы скажем."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def time(self):  # Обычные часы — для паузы при переборе.
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeCamera:
    def __init__(self):
        self.released = False

    def read(self):
        # Тёмный кадр с мягким градиентом, как комната при слабом свете (порядок цветов BGR).
        rows = np.linspace(38, 18, 480, dtype=np.float32)[:, None, None]
        frame = np.broadcast_to(rows * np.array([1.0, 0.9, 0.8]), (480, 640, 3)).astype(np.uint8).copy()
        return True, frame

    def release(self):
        self.released = True


class Scenario:
    """Что сейчас «видит» поддельная нейросеть.

    none — пусто; target — живая рука с нужным жестом (дрожит);
    photo — нужный жест, но точки неподвижны, как на фото;
    wrong — чужой жест wrong_name; move — живая рука выполняет движение.
    """

    show = "none"
    wrong_name = None
    move_start = None
    app = None
    clock = None
    rng = random.Random(7)


def moved_position(kind, k):
    """Где центр руки в доле k (0…1) движения."""
    if kind == "left":
        return 0.65 - 0.3 * k, 0.8
    if kind == "right":
        return 0.35 + 0.3 * k, 0.8
    if kind == "up":
        return 0.5, 0.9 - 0.3 * k
    phase = (k * 5) % 2  # wave: взмахи вправо-влево.
    return 0.42 + 0.16 * (phase if phase <= 1 else 2 - phase), 0.8


def hand_proto(points, jitter=0.0):
    proto = landmark_pb2.NormalizedLandmarkList()
    for p in points:
        proto.landmark.add(x=p.x + Scenario.rng.gauss(0, jitter) if jitter else p.x,
                           y=p.y + Scenario.rng.gauss(0, jitter) if jitter else p.y, z=0.0)
    return proto


class FakeHands:
    def __init__(self, **kwargs):
        self.closed = False

    def process(self, rgb):
        app, hands = Scenario.app, []
        if Scenario.show == "target":
            hands = [hand_proto(gesture_points(app.target), jitter=0.004)]
        elif Scenario.show == "photo":
            hands = [hand_proto(gesture_points(app.target))]
        elif Scenario.show == "photo_moving":
            # Фото на телефоне, телефон плавно водят влево-вправо (как в проверке Макса).
            u = (Scenario.clock.now * 0.8) % 2
            cx = 0.35 + 0.3 * (u if u <= 1 else 2 - u)  # Туда-обратно между 0,35 и 0,65.
            hands = [hand_proto(gesture_points(app.target, cx=cx))]
        elif Scenario.show == "flex":
            # Живая рука: ладонь и кулак по 0,5 с с полусогнутыми кадрами между ними.
            phase = (Scenario.clock.now - Scenario.move_start) % 1.3 if Scenario.move_start else 0
            if Scenario.move_start is None:
                Scenario.move_start = Scenario.clock.now
            if phase < 0.5:
                points = gesture_points("palm")
            elif phase < 0.65 or phase >= 1.15:
                points = make_points((True, False, True, False))
            else:
                points = gesture_points("fist")
            hands = [hand_proto(points, jitter=0.004)]
        elif Scenario.show == "wrong":
            hands = [hand_proto(gesture_points(Scenario.wrong_name), jitter=0.004)]
        elif Scenario.show == "move" and app.motion is not None:
            if Scenario.move_start is None:
                Scenario.move_start = Scenario.clock.now
            k = min(1.0, (Scenario.clock.now - Scenario.move_start) / 2.0)
            cx, wy = moved_position(app.motion.kind, k)
            hands = [hand_proto(gesture_points("palm", cx=cx, wrist_y=wy), jitter=0.004)]
        return SimpleNamespace(multi_hand_landmarks=hands or None)

    def close(self):
        self.closed = True


cameras = []
camera_fails = {"on": False}


def fake_open_camera(index):
    if camera_fails["on"]:
        raise RuntimeError(f"Камера {index} не передаёт изображение.")
    camera = FakeCamera()
    cameras.append(camera)
    return camera, camera.read()[1]


def install_fakes():
    clock = FakeClock()
    app_module.time = clock
    app_module.cv2 = cv2
    app_module.ctk = ctk
    app_module.Image = Image
    app_module.open_camera = fake_open_camera
    mp.solutions.hands.Hands = FakeHands
    app_module.mp = mp
    # Настоящий счётчик ошибок в %APPDATA% не трогаем: временная папка.
    app_module.LOCKOUT_PATH = os.path.join(tempfile.mkdtemp(prefix="maxsgmuss_"), "lockout.json")
    Scenario.clock = clock
    return clock


def pump(root, clock, seconds, step=0.05):
    """Прокручивает окно: поддельное время идёт вперёд, Tk обрабатывает события."""
    for _ in range(int(seconds / step)):
        clock.now += step
        root.update()
        real_time.sleep(0.032)  # Чуть дольше интервала обновления кадров (30 мс).


def shot(root, name):
    os.makedirs(SHOTS, exist_ok=True)
    root.update()
    real_time.sleep(0.15)
    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(os.path.join(SHOTS, name + ".png"))


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("  ok —", message)


def main():
    clock = install_fakes()
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.report_callback_exception = lambda *exc: errors.append(exc)
    app = app_module.CaptchaApp(root)
    Scenario.app = app
    root.attributes("-topmost", True)
    if os.environ.get("SMOKE_THEME") == "light":  # Светлые скриншоты для презентации.
        app._on_shortcut_theme()

    print("1. Запуск и первый кадр")
    pump(root, clock, 0.5)
    check(app.active and app.preview_state == "camera", "камера включена, показывается кадр")
    check(app.target in app_module.GESTURES, "выбрано задание")
    check("ШАГ 1 ИЗ 2" in app.task_section_label.cget("text"), "задание из двух шагов")
    shot(root, "01_camera")

    print("2. Чужой жест не открывает доступ и считается ошибкой")
    Scenario.show, Scenario.wrong_name = "wrong", next(g for g in app_module.GESTURES if g != app.target)
    pump(root, clock, 1.0)
    check(not app.access_granted, "доступ закрыт")
    check("Распознано" in app.detected.cget("text"), "подсказка показывает распознанный жест")
    check(app.lockout.errors == 1, "одна ошибка за один удерживаемый чужой жест")

    print("3. Фото руки проходит жест, но застревает на сжатиях")
    Scenario.show = "photo"
    pump(root, clock, app.hold_seconds + 0.6)
    check(app.step_index == 1 and app.flex is not None, "жест на фото засчитан, ждём сжатия кулака")
    check("ШАГ 2 ИЗ 2" in app.task_section_label.cget("text"), "в панели второй шаг")
    pump(root, clock, 4.0)
    check(not app.access_granted and app.flex.progress() == 0, "неподвижное фото не сжимает кулак")
    Scenario.show = "photo_moving"
    pump(root, clock, 5.0)
    check(not app.access_granted and app.flex.progress() == 0, "фото на движущемся телефоне тоже не проходит")
    shot(root, "02_photo_stuck")

    print("4. Живая рука сжимает и разжимает кулак")
    Scenario.show, Scenario.move_start = "flex", None
    pump(root, clock, 4.0)
    check(app.access_granted, "доступ открыт после двух сжатий")
    check(app.progress.get() == 1.0, "полоса сжатий заполнена до конца")
    check(app.preview_state == "success", "экран успеха")
    check(cameras[-1].released and app.detector is None, "камера и детектор освобождены")
    check(app.lockout.errors == 0, "успех обнулил счётчик ошибок")
    shot(root, "04_success")

    print("5. Новая попытка отзывает прошлый успех")
    Scenario.show = "none"
    app.new_challenge()
    pump(root, clock, 0.3)
    check(not app.access_granted and app.active, "успех сброшен, камера снова работает")

    print("6. Тема меняется без перезапуска камеры")
    camera_before, theme_before = app.camera, app.theme_mode
    app._on_shortcut_theme()
    pump(root, clock, 0.3)
    check(app.theme_mode != theme_before and app.camera is camera_before, "тема сменилась, та же камера")
    shot(root, "light_theme")
    app._on_shortcut_theme()

    print("7. Время вышло")
    pump(root, clock, app.time_limit + 0.5, step=0.5)
    check(app.preview_state == "timeout" and not app.access_granted, "экран «Время вышло»")
    check(app.new_button.cget("text") == "Повторить попытку", "кнопка повтора")
    check(app.lockout.errors == 1, "истёкшее время — ошибка")
    shot(root, "05_timeout")

    print("8. Перебор жестов включает паузу")
    app.lockout.success()
    app.new_challenge()
    pump(root, clock, 0.3)
    others = [g for g in app_module.GESTURES if g != app.target]
    for name in others[:app_module.LOCK_AFTER]:
        Scenario.show, Scenario.wrong_name = "wrong", name
        pump(root, clock, 0.7)
    Scenario.show = "none"
    check(app.lockout.remaining() > 0, "началась пауза")
    check(not app.active and app.camera is None, "камера выключена во время паузы")
    check(app.new_button.cget("state") == "disabled", "кнопка недоступна")
    check(app.placeholder_title.cget("text") == "Слишком много ошибок", "экран паузы")
    pump(root, clock, 1.0, step=0.25)
    shot(root, "06_lockout")
    opened = len(cameras)
    app.lockout = app_module.Lockout(app_module.LOCKOUT_PATH)  # Как после перезапуска: читаем файл.
    app.new_challenge()
    pump(root, clock, 0.3)
    check(app.lockout.remaining() > 0 and len(cameras) == opened, "после «перезапуска» пауза осталась, камера не открывалась")
    pump(root, clock, app_module.LOCK_STEPS[0] + 1, step=0.25)
    real_time.sleep(0.3)
    root.update()
    check(app.new_button.cget("state") == "normal", "пауза закончилась, попытка снова доступна")
    check(app.placeholder_title.cget("text") == "Пауза закончилась", "сообщение об окончании паузы")

    print("9. Камера не открывается")
    camera_fails["on"] = True
    app.new_challenge()
    pump(root, clock, 0.3)
    check(not app.active and not app.access_granted, "доступ закрыт, камера выключена")
    check(app.new_button.cget("state") == "normal", "повтор доступен")
    shot(root, "07_camera_error")
    camera_fails["on"] = False

    print("10. Уровень «Лёгкий»: один жест, фото проходит (для демонстрации атаки)")
    app.lockout.success()
    app.change_difficulty("Лёгкий")
    pump(root, clock, 0.3)
    check(app.active, "камера работает")
    check([kind for kind, _ in app.steps] == ["gesture"] and app.time_limit == 40, "один шаг, 40 с")
    Scenario.show = "photo"
    pump(root, clock, app.hold_seconds + 0.5)
    check(app.access_granted, "фото проходит лёгкий уровень")

    print("11. Уровень «Сложный»: жест, сжатия и движение")
    Scenario.show = "none"
    app.change_difficulty("Сложный")
    pump(root, clock, 0.3)
    check(app.active, "камера работает")
    check([kind for kind, _ in app.steps] == ["gesture", "flex", "motion"], "три шага")
    check(app.hold_seconds == 2.0, "удержание 2 с")
    check(app.difficulty_choice.get() == "Сложный", "список показывает выбранный уровень")
    Scenario.show = "target"
    pump(root, clock, app.hold_seconds + 0.5)
    Scenario.show, Scenario.move_start = "flex", None
    pump(root, clock, 4.0)
    check(app.step_index == 2 and app.motion is not None, "после сжатий — шаг с движением")
    shot(root, "08_hard_motion")
    Scenario.show, Scenario.move_start = "move", None
    pump(root, clock, 2.5)
    check(app.access_granted, f"сложный уровень пройден (движение «{app.motion.kind}»)")

    print("12. Минимальный размер окна: результат и кнопки видны")
    Scenario.show = "target"
    app.change_difficulty("Средний")
    pump(root, clock, 0.5)
    shot(root, "08b_medium_normal_size")
    root.geometry("900x600")
    pump(root, clock, 0.5)
    check(app.active and app.preview_state == "camera", "камера работает в маленьком окне")
    panel_bottom = app.panel.winfo_rooty() + app.panel.winfo_height()
    for widget, name in ((app.result_box, "блок результата"), (app.new_button, "кнопка"),
                         (app.difficulty_choice, "выбор сложности")):
        bottom = widget.winfo_rooty() + widget.winfo_height()
        check(widget.winfo_ismapped() and bottom <= panel_bottom, f"{name} внутри панели")
    shot(root, "09_min_size")
    app._on_shortcut_theme()
    pump(root, clock, 0.3)
    shot(root, "10_min_size_light")
    app._on_shortcut_theme()

    print("13. Закрытие окна")
    app.new_challenge()
    pump(root, clock, 0.2)
    last = cameras[-1]
    app.close()
    check(last.released, "камера освобождена при закрытии")
    check(not errors, f"нет исключений в обработчиках Tk ({len(errors)})")
    print("Готово. Скриншоты:", SHOTS)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("ОШИБКА:", error)
        for exc in errors:
            print("  исключение Tk:", exc[1])
        sys.exit(1)
