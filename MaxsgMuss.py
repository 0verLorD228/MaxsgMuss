"""
MaxsgMuss 2.3 — учебная жестовая капча с камерой на Python.

Запуск: Python 3.11 или 3.12 (64-bit). Проще всего — run_MaxsgMuss.bat.
Или один раз установите библиотеки в терминале:
python -m pip install -r requirements.txt
Затем: python MaxsgMuss.py
Проверка: python -m unittest discover -s tests

Программа работает локально, не записывает и не отправляет видео.
Надпись «Доступ открыт» демонстрирует результат, а не открывает доступ к ОС.

Источники и изменения:
1. CVZone 1.6.1, HandTrackingModule.py, метод fingersUp (MIT):
   https://github.com/cvzone/cvzone/blob/master/cvzone/HandTrackingModule.py
   Исходник прочитан из официального пакета https://pypi.org/project/cvzone/1.6.1/
   Адаптировано сравнение координат четырёх пальцев: убран подсчёт большого
   пальца, добавлены допуск и проверка положения кисти.
2. Справочник по API MediaPipe Hands и пример камеры:
   https://chuoling.github.io/mediapipe/solutions/hands.html
   Репозиторий: https://github.com/google-ai-edge/mediapipe
Окно на customtkinter, выбор задания, таймер, логика доступа, защита от фото
(FlexChallenge) и от перебора (Lockout), уровни сложности и подсказки написаны
для этого проекта.

Ниже сохранена лицензия заимствованного фрагмента CVZone:

MIT License
Copyright (c) 2021 Vizdx LLC, Computer Vision Zone, https://www.computervision.zone/

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json  # Хранит счётчик ошибок между запусками.
import math  # Корень и проверка чисел для оценки дрожи.
import os  # Путь к папке пользователя для файла счётчика.
import secrets  # Выбирает случайное задание.
import sys  # Позволяет узнать операционную систему.
import time  # Измеряет длительность удержания жеста.
from collections import deque  # Очередь последних положений руки.


# Эти настройки можно менять, не переписывая остальную программу.
APP_NAME = "MaxsgMuss"  # Название в шапке приложения и заголовке окна.
CAMERA_INDEX = 0  # Номер камеры: обычно 0; для другой камеры попробуйте 1.
MAX_FRAME_GAP = 0.5  # При большой паузе между кадрами удержание сбрасывается.
CARD_RADIUS = 20  # Радиус скругления карточек customtkinter.
MONO_FONT = "Consolas"  # Моноширинный шрифт для таймера и статуса: цифры не «прыгают».
# Время на задание и длительность удержания жеста зависят от уровня — см. DIFFICULTY ниже.

# Две палитры «киберсек»: графит с неоновым циановым акцентом. Все цвета собраны
# здесь, поэтому переключение темы меняет оформление сразу и не трогает логику камеры.
THEMES = {
    "dark": {
        "background": "#060a12",
        "text": "#e8f1ff",
        "panel": "#0c1422",
        "panel_light": "#15213a",
        "camera": "#03060c",
        "muted": "#7d8ca6",
        "secondary_text": "#b6c3d9",
        "accent": "#22d3ee",  # Неоновый циан.
        "success": "#34d399",
        "danger": "#fb5a78",
        "warning": "#fbbf24",  # Янтарный цвет истекшего времени и паузы.
        "timeout_panel": "#2c2312",
        "timeout_preview": "#0a111d",
        "border": "#1d2c47",
        "result": "#101b2e",
        "success_panel": "#0d2e27",
        "success_preview": "#051c17",
        "success_icon": "#0f4537",
        "button_hover": "#67e8f9",
        "secondary_hover": "#1e2e4c",
        "button_text": "#031119",
    },
    "light": {
        "background": "#edf3f9",
        "text": "#0e1a2c",
        "panel": "#ffffff",
        "panel_light": "#e2ecf7",
        "camera": "#d3dfec",
        "muted": "#56677f",
        "secondary_text": "#31445d",
        "accent": "#0891b2",
        "success": "#05875f",
        "danger": "#d61f4a",
        "warning": "#975a00",
        "timeout_panel": "#fdf0cf",
        "timeout_preview": "#f3f7fc",
        "border": "#c5d5e8",
        "result": "#e7eff9",
        "success_panel": "#d8f4e8",
        "success_preview": "#e5f8ef",
        "success_icon": "#bdeedb",
        "button_hover": "#06b6d4",
        "secondary_hover": "#d0deee",
        "button_text": "#ffffff",
    },
}
# Запасные цвета для статуса — берутся из тёмной темы, чтобы не расходиться с ней.
MUTED_COLOR = THEMES["dark"]["muted"]
ACCENT_COLOR = THEMES["dark"]["accent"]
SUCCESS_COLOR = THEMES["dark"]["success"]
DANGER_COLOR = THEMES["dark"]["danger"]

# Ключ — название жеста в коде; значения — название и пояснение для человека.
GESTURES = {
    "palm": ("Раскрытая ладонь", "Выпрямите четыре пальца. Большой палец можно держать свободно."),
    "peace": ("Знак V", "Поднимите указательный и средний пальцы. Безымянный и мизинец согните."),
    "index": ("Указательный палец", "Поднимите указательный палец. Средний, безымянный и мизинец согните."),
    "three": ("Три пальца", "Поднимите указательный, средний и безымянный пальцы. Мизинец согните."),
    "rock": ("Знак рока", "Поднимите указательный палец и мизинец. Средний и безымянный согните."),
    "fist": ("Кулак", "Сожмите четыре пальца в кулак. Большой палец можно положить сверху."),
    "thumbs_up": ("Большой палец вверх", "Сожмите четыре пальца и поднимите большой палец вверх."),
}

# Жесты в движении: фотографию нельзя сдвинуть по команде в случайную сторону.
# Предпросмотр зеркальный, поэтому «влево» — влево и для человека, и на экране.
MOTIONS = {
    "left": ("Сдвиньте руку влево", "Плавно проведите раскрытую ладонь влево через кадр."),
    "right": ("Сдвиньте руку вправо", "Плавно проведите раскрытую ладонь вправо через кадр."),
    "up": ("Поднимите руку вверх", "Плавно поднимите ладонь вверх, не убирая её из кадра."),
    "wave": ("Помашите рукой", "Помашите ладонью из стороны в сторону 2–3 раза."),
}

# Защита от фото: жест в движении.
# Проверку дрожи пальцев пробовали и убрали: калибровка 2026-11-09 показала,
# что на фото точки скачут сильнее, чем дрожит живая рука (медианы 0,16–0,26 и 0,05).
MOTION_DISTANCE = 0.2  # На какую долю кадра нужно сдвинуть руку.
MOTION_WINDOW = 3.0  # За сколько секунд нужно успеть сдвинуть руку.
WAVE_TURNS = 3  # Сколько раз рука должна сменить направление при взмахах.
WAVE_AMPLITUDE = 0.08  # Минимальный размах взмаха; мелкая дрожь не считается.

# Главная защита от фото: сжать и разжать кулак. Телефон с фото можно двигать,
# но согнуть пальцы на фото нельзя (проверка Макса 2026-11-09: сдвиг телефона
# проходил задание с движением).
FLEX_TASK = ("Сожмите и разожмите кулак",
             "Два раза подряд: кулак — ладонь — кулак — ладонь. Не убирайте руку из кадра.")
FLEX_CHANGES = 4  # Сколько смен «ладонь ↔ кулак» нужно (два полных сжатия).
FLEX_MAX_GAP = 0.3  # Рука пропала дольше — счёт заново (так выглядит листание фото).
FLEX_STEP_TIME = 1.5  # Максимум секунд между сменами формы.
FLEX_MAX_JUMP = 0.25  # Скачок центра руки между кадрами больше этой доли кадра — другая картинка.

# Уровни сложности: шаги задания, время на всё задание и удержание жеста.
# «Лёгкий» без сжатий: фото его проходит — удобно показать атаку на защите проекта.
DIFFICULTY = {
    "Лёгкий": {"steps": ("gesture",), "time": 40, "hold": 1.5},
    "Средний": {"steps": ("gesture", "flex"), "time": 30, "hold": 1.5},
    "Сложный": {"steps": ("gesture", "flex", "motion"), "time": 30, "hold": 2.0},
}
DEFAULT_DIFFICULTY = "Средний"

# Защита от перебора.
LOCK_AFTER = 5  # После скольких ошибок подряд начинается пауза.
LOCK_STEPS = (10, 30, 60)  # Длительность пауз в секундах; дальше остаётся последняя.
WRONG_HOLD = 0.5  # Сколько секунд чужой жест должен держаться, чтобы стать ошибкой.
LOCKOUT_PATH = None  # None — файл в папке пользователя (%APPDATA%\MaxsgMuss).


def draw_timeout_picture(colors):
    """Рисует часы для экрана тайм-аута. PNG и новые библиотеки не нужны."""
    from PIL import Image, ImageDraw  # Pillow уже используется для видео.

    picture = Image.new("RGBA", (320, 320), (0, 0, 0, 0))  # Прозрачный фон.
    draw = ImageDraw.Draw(picture)
    ink = colors["warning"]
    # Круглый циферблат и внешняя дуга изображают закончившийся отсчёт.
    draw.ellipse((42, 42, 278, 278), fill=colors["timeout_panel"])
    draw.arc((22, 22, 298, 298), start=285, end=615, fill=ink, width=6)
    draw.ellipse((72, 72, 248, 248), outline=ink, width=8)
    # Четыре отметки часов и две стрелки: всё рисуется простыми линиями.
    for line in ((160, 88, 160, 101), (219, 160, 232, 160),
                 (160, 219, 160, 232), (88, 160, 101, 160)):
        draw.line(line, fill=ink, width=6)
    draw.line((160, 117, 160, 160, 191, 179), fill=ink, width=10)
    draw.ellipse((152, 152, 168, 168), fill=ink)
    # Небольшая отметка привлекает внимание к завершению времени.
    draw.ellipse((227, 227, 291, 291), fill=ink)
    draw.line((259, 239, 259, 261), fill=colors["timeout_preview"], width=7)
    draw.ellipse((255, 271, 263, 279), fill=colors["timeout_preview"])
    return picture


def recognize_gesture(points):
    """Определяет жест по 21 точке кисти, найденной MediaPipe."""
    if len(points) != 21:  # Без полного набора точек результат не засчитывается.
        return None

    # Если точки выходят к краю кадра, просим показать кисть целиком.
    if any(not (0.02 < p.x < 0.98 and 0.02 < p.y < 0.98) for p in points):
        return None

    # 0 — запястье, 9 — основание среднего пальца; координата y растёт вниз.
    palm_height = points[0].y - points[9].y
    if palm_height < 0.06:  # Кисть слишком мала, сильно наклонена или перевёрнута.
        return None
    if abs(points[9].x - points[0].x) > palm_height * 0.8:
        return None  # Упрощённый алгоритм рассчитан на кисть пальцами вверх.

    margin = palm_height * 0.10  # Допуск зависит от размера кисти в кадре.
    fingers = []  # Здесь будут True для прямых и False для согнутых пальцев.
    for tip in (8, 12, 16, 20):  # Кончики четырёх пальцев, без большого.
        difference = points[tip - 2].y - points[tip].y  # Сустав минус кончик.
        if abs(difference) < margin:  # Промежуточное положение не засчитываем.
            return None
        fingers.append(difference > 0)  # Кончик выше сустава — палец поднят.

    # Порядок: указательный, средний, безымянный, мизинец.
    pattern = tuple(fingers)
    # Для жеста «большой палец вверх» дополнительно проверяем большой палец.
    # Точка 4 — его кончик, точка 3 — ближайший сустав.
    if pattern == (False, False, False, False):
        thumb_is_up = points[4].y < points[3].y - margin
        if thumb_is_up:  # Большой палец заметно выше своего сустава.
            return "thumbs_up"

    patterns = {
        (True, True, True, True): "palm",
        (True, True, False, False): "peace",
        (True, False, False, False): "index",
        (True, True, True, False): "three",
        (True, False, False, True): "rock",
        (False, False, False, False): "fist",
    }
    return patterns.get(pattern)  # Для неизвестной комбинации вернётся None.


def gesture_problem(points):
    """Объясняет человеку, почему recognize_gesture() не узнала жест.

    Проверки повторяют recognize_gesture() в том же порядке, но вместо None
    возвращают подсказку. None — проблем нет, жест распознаётся.
    """
    if len(points) != 21:
        return "Рука видна не полностью"
    if any(not (0.02 < p.x < 0.98 and 0.02 < p.y < 0.98) for p in points):
        return "Рука у края кадра — сдвиньте её к центру"
    palm_height = points[0].y - points[9].y
    palm_size = math.hypot(points[9].x - points[0].x, palm_height)
    if palm_size < 0.06:
        return "Рука далеко — поднесите её ближе к камере"
    if palm_height < 0.06:
        return "Поверните кисть пальцами вверх"
    if abs(points[9].x - points[0].x) > palm_height * 0.8:
        return "Держите кисть ровно, пальцами вверх"
    margin = palm_height * 0.10
    if any(abs(points[tip - 2].y - points[tip].y) < margin for tip in (8, 12, 16, 20)):
        return "Выпрямите или согните пальцы чётче"
    if recognize_gesture(points) is None:
        return "Такого жеста нет в задании"
    return None


def hex_to_rgb(color):
    """'#22d3ee' → (34, 211, 238): так цвет понимают OpenCV и MediaPipe."""
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


# Какие пальцы подняты на картинке жеста (указательный, средний, безымянный, мизинец)
# и поднят ли большой палец.
GESTURE_SHAPES = {
    "palm": ((True, True, True, True), False),
    "peace": ((True, True, False, False), False),
    "index": ((True, False, False, False), False),
    "three": ((True, True, True, False), False),
    "rock": ((True, False, False, True), False),
    "fist": ((False, False, False, False), False),
    "thumbs_up": ((False, False, False, False), True),
}


# Связи между 21 точкой руки — те же, что MediaPipe рисует поверх видео.
HAND_CONNECTIONS = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
                    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
                    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17))
PICTURE_SCALE = 4  # Рисуем в 4 раза крупнее и уменьшаем: линии получаются гладкими.


def hand_landmarks(shape):
    """Схема 21 точки руки в порядке MediaPipe, координаты 0…200 (y вниз).

    Возвращает точки и номера точек, которые не рисуются: у согнутого пальца
    виден только первый сустав, иначе линии согнутых пальцев накладываются.
    """
    fingers, thumb_up = shape
    points = {0: (100, 180)}  # Запястье.
    bases = {5: (78, 112), 9: (100, 106), 13: (121, 110), 17: (140, 120)}  # Основания пальцев.
    lengths = {5: (30, 22, 18), 9: (34, 24, 20), 13: (31, 22, 18), 17: (24, 17, 15)}
    hidden = set()
    for (base, (bx, by)), up in zip(bases.items(), fingers):
        points[base] = (bx, by)
        a, b, c = lengths[base]
        lean = (bx - 100) * 0.12  # Пальцы слегка расходятся веером.
        if up:
            points[base + 1] = (bx + lean, by - a)
            points[base + 2] = (bx + lean * 1.6, by - a - b)
            points[base + 3] = (bx + lean * 2.1, by - a - b - c)
        else:
            points[base + 1] = (bx, by - 16)  # Согнутый палец: только сустав над ладонью.
            points[base + 2] = points[base + 3] = points[base + 1]
            hidden.update((base + 2, base + 3))
    if thumb_up:  # Большой палец торчит вертикально вверх.
        points.update({1: (80, 158), 2: (64, 136), 3: (58, 110), 4: (56, 84)})
    else:  # Большой палец отведён в сторону.
        points.update({1: (80, 160), 2: (60, 145), 3: (46, 130), 4: (36, 117)})
    return [points[i] for i in range(21)], hidden


def _draw_skeleton(draw, shape, colors, ox=0.0, oy=0.0, s=1.0):
    """Рисует руку точками и линиями, как MediaPipe поверх видео."""
    k = PICTURE_SCALE
    landmarks, hidden = hand_landmarks(shape)
    points = [((ox + x * s) * k, (oy + y * s) * k) for x, y in landmarks]
    for a, b in HAND_CONNECTIONS:
        if a not in hidden and b not in hidden:
            draw.line((points[a], points[b]), fill=colors["accent"], width=round(9 * s * k))
    radius = 6 * s * k
    for number, (x, y) in enumerate(points):
        if number not in hidden:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                         fill=colors["text"], outline=colors["accent"], width=round(2.5 * s * k))


def _draw_arrow(draw, start, end, color, width=12):
    """Толстая стрелка: линия и треугольник на конце. Координаты 0…200."""
    k = PICTURE_SCALE
    start, end, width = (start[0] * k, start[1] * k), (end[0] * k, end[1] * k), width * k
    draw.line((start, end), fill=color, width=width)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy) or 1
    ux, uy = dx / length, dy / length  # Направление стрелки.
    head = width * 2
    back = (end[0] - ux * head, end[1] - uy * head)
    draw.polygon([(end[0] + ux * 4 * k, end[1] + uy * 4 * k),
                  (back[0] - uy * head, back[1] + ux * head),
                  (back[0] + uy * head, back[1] - ux * head)], fill=color)


def draw_gesture_picture(kind, name, colors, size=200):
    """Картинка задания size×size: скелет жеста, стрелка движения или «кулак ⇄ ладонь».
    Рисуется на холсте 200×200 (в PICTURE_SCALE раз крупнее) и уменьшается до size."""
    from PIL import Image, ImageDraw  # Pillow уже используется для видео.

    k = PICTURE_SCALE
    picture = Image.new("RGBA", (200 * k, 200 * k), (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    ink = colors["accent"]
    if kind == "gesture":
        _draw_skeleton(draw, GESTURE_SHAPES[name], colors, ox=-6, oy=-14, s=1.1)
    elif kind == "flex":
        _draw_skeleton(draw, GESTURE_SHAPES["fist"], colors, ox=-8, oy=10, s=0.6)
        _draw_skeleton(draw, GESTURE_SHAPES["palm"], colors, ox=86, oy=10, s=0.6)
        _draw_arrow(draw, (40, 160), (160, 160), ink, width=8)
        _draw_arrow(draw, (160, 186), (40, 186), ink, width=8)
    elif name in ("left", "right"):
        _draw_skeleton(draw, GESTURE_SHAPES["palm"], colors, ox=40, oy=-8, s=0.65)
        start, end = ((165, 170), (35, 170)) if name == "left" else ((35, 170), (165, 170))
        _draw_arrow(draw, start, end, ink)
    elif name == "up":
        _draw_skeleton(draw, GESTURE_SHAPES["palm"], colors, ox=0, oy=40, s=0.75)
        _draw_arrow(draw, (168, 185), (168, 25), ink)
    else:  # wave: ладонь и дуги по бокам, как взмахи.
        _draw_skeleton(draw, GESTURE_SHAPES["palm"], colors, ox=36, oy=26, s=0.65)
        for box in ((8, 30, 70, 150), (18, 50, 60, 130)):
            draw.arc([v * k for v in box], start=120, end=240, fill=ink, width=8 * k)
        for box in ((130, 30, 192, 150), (140, 50, 182, 130)):
            draw.arc([v * k for v in box], start=-60, end=60, fill=ink, width=8 * k)
    return picture.resize((size, size), Image.LANCZOS)


def build_steps(level, choose, previous=None):
    """Шаги задания для уровня. choose — функция случайного выбора (secrets.choice)."""
    steps = []
    for kind in DIFFICULTY[level]["steps"]:
        if kind == "gesture":
            steps.append(("gesture", choose([g for g in GESTURES if g != previous])))
        elif kind == "flex":
            steps.append(("flex", "flex"))
        else:
            steps.append(("motion", choose(list(MOTIONS))))
    return steps


def open_camera(index):
    """Пробует способы подключения и возвращает камеру вместе с первым кадром."""
    # В Windows разные камеры работают с разными драйверами OpenCV.
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
    for backend in backends:
        camera = None
        keep_camera = False  # Неудачно открытый ресурс обязательно освобождаем.
        try:
            camera = cv2.VideoCapture(index, backend)
            if not camera.isOpened():
                continue
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            # Одного isOpened недостаточно: камера должна выдать изображение.
            # Несколько повторов нужны для её прогрева после включения.
            for _ in range(10):
                ok, frame = camera.read()
                if ok and frame is not None and frame.size > 0:
                    keep_camera = True
                    return camera, frame
                time.sleep(0.03)
        except Exception:
            # Ошибка одного способа подключения не мешает попробовать следующий.
            continue
        finally:
            if camera is not None and not keep_camera:
                camera.release()
    raise RuntimeError(
        f"Камера {index} не передаёт изображение. "
        "Выберите другой номер камеры сверху. Закройте приложения, которые "
        "используют камеру, и проверьте разрешение на доступ к ней в Windows."
    )


def palm_center(points):
    """Центр ладони: среднее запястья и оснований указательного, среднего пальцев и мизинца."""
    base = [points[i] for i in (0, 5, 9, 17)]
    return sum(p.x for p in base) / 4, sum(p.y for p in base) / 4


class MotionChallenge:
    """Проверяет жест в движении: сдвиг в сторону или взмахи рукой."""

    def __init__(self, kind, distance=MOTION_DISTANCE, window=MOTION_WINDOW,
                 turns=WAVE_TURNS, amplitude=WAVE_AMPLITUDE):
        self.kind = kind
        self.distance = distance
        self.window = window
        self.turns_needed = turns
        self.amplitude = amplitude
        self.history = deque()  # Последние положения центра ладони: (время, x, y).
        self.turn_times = deque()  # Когда рука меняла направление при взмахах.
        self.extreme = None  # Крайняя точка текущего взмаха.
        self.low = self.high = None  # Самая левая и правая точки, пока направление не ясно.
        self.direction = 0  # 1 — рука идёт вправо, -1 — влево, 0 — ещё не ясно.
        self.best = 0.0  # Лучший достигнутый прогресс от 0 до 1.
        self.done = False

    def progress(self):
        return min(1.0, self.best)

    def add(self, points, now):
        """Добавляет положение руки; возвращает True, когда движение выполнено."""
        if self.done:
            return True
        x, y = palm_center(points)
        self.history.append((now, x, y))
        while now - self.history[0][0] > self.window:
            self.history.popleft()
        if self.kind == "wave":
            self._track_wave(x, now)
            reached = len(self.turn_times) / self.turns_needed
        else:
            if self.kind == "left":
                shift = max(h[1] for h in self.history) - x
            elif self.kind == "right":
                shift = x - min(h[1] for h in self.history)
            else:  # "up": координата y в кадре растёт вниз.
                shift = max(h[2] for h in self.history) - y
            reached = shift / self.distance
        self.best = max(self.best, reached)
        self.done = reached >= 1
        return self.done

    def _track_wave(self, x, now):
        """Считает смены направления; движения меньше amplitude не учитываются."""
        while self.turn_times and now - self.turn_times[0] > self.window:
            self.turn_times.popleft()
        if self.extreme is None:
            self.low = self.high = self.extreme = x
        elif self.direction == 0:
            # Направление ещё не ясно: помним самую левую и самую правую точку.
            # Отсчёт от одной стартовой точки не сработал бы, если рука машет вокруг неё.
            self.low, self.high = min(self.low, x), max(self.high, x)
            if x - self.low >= self.amplitude:
                self.direction, self.extreme = 1, x
            elif self.high - x >= self.amplitude:
                self.direction, self.extreme = -1, x
        elif (x - self.extreme) * self.direction > 0:
            self.extreme = x  # Рука продолжает идти в ту же сторону.
        elif abs(x - self.extreme) >= self.amplitude:
            self.direction = -self.direction  # Рука пошла обратно — это взмах.
            self.extreme = x
            self.turn_times.append(now)


class FlexChallenge:
    """Проверяет, что человек сжимает и разжимает кулак без разрывов.

    Фото можно двигать, но пальцы на нём не согнуть. Подменять фото
    листанием тоже не выйдет: при листании рука на мгновение пропадает
    или центр руки резко прыгает — тогда счёт начинается заново.
    """

    def __init__(self, changes=FLEX_CHANGES, max_gap=FLEX_MAX_GAP,
                 step_time=FLEX_STEP_TIME, max_jump=FLEX_MAX_JUMP):
        self.changes_needed = changes
        self.max_gap = max_gap
        self.step_time = step_time
        self.max_jump = max_jump
        self.state = None  # Последняя распознанная форма руки: "open" или "closed".
        self.changes = 0
        self.last_change = None  # Когда форма менялась последний раз.
        self.last_seen = None  # Когда рука была в кадре последний раз.
        self.last_center = None
        self.reset_reason = ""  # Почему счёт сбросился — для подсказки в окне.
        self.just_reset = False  # Счёт сбросился именно на этом кадре.
        self.done = False

    def progress(self):
        return min(1.0, self.changes / self.changes_needed)

    def _restart(self, reason):
        if self.state is not None:  # Сообщаем, только если было что сбрасывать.
            self.reset_reason = reason
            self.just_reset = True
        self.state, self.changes, self.last_change = None, 0, None

    def add(self, points, gesture, now):
        """points — точки руки или None; gesture — распознанный жест или None.
        Возвращает True, когда нужное число смен формы выполнено."""
        self.just_reset = False
        if self.done:
            return True
        gap = self.last_seen is not None and now - self.last_seen > self.max_gap
        if points is None:
            if gap:
                self._restart("Рука пропала из кадра — начните сначала.")
            return False
        center = palm_center(points)
        if gap:
            self._restart("Рука пропала из кадра — начните сначала.")
        elif self.last_center is not None and math.dist(center, self.last_center) > self.max_jump:
            self._restart("Рука сместилась скачком — начните сначала.")
        elif self.last_change is not None and now - self.last_change > self.step_time:
            self._restart("Слишком медленно — сжимайте и разжимайте быстрее.")
        self.last_seen, self.last_center = now, center
        # Кулак с торчащим вверх большим пальцем — тоже сжатая рука.
        shape = {"palm": "open", "fist": "closed", "thumbs_up": "closed"}.get(gesture)
        if shape:  # Полусогнутые пальцы (жест None) не прерывают счёт.
            if self.state is None:
                self.state = shape
            elif shape != self.state:
                self.state = shape
                self.changes += 1
                self.last_change = now
                self.done = self.changes >= self.changes_needed
        return self.done


def default_lockout_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME, "lockout.json")


class Lockout:
    """Растущая пауза после неверных жестов. Счётчик хранится в файле,
    поэтому перезапуск программы паузу не снимает.

    В файле только три числа: ошибки, ступень паузы и время её окончания.
    Удаление файла сбрасывает счётчик — это известное ограничение учебной версии.
    """

    def __init__(self, path=None, clock=None):
        self.path = path or default_lockout_path()
        self.clock = clock or (lambda: time.time())  # Обычные часы: переживают перезапуск.
        self.errors = 0
        self.level = 0
        self.locked_until = 0.0
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as file:
                data = json.load(file)
            values = (data["errors"], data["level"], data["locked_until"])
            for value in values:  # bool — тоже int в Python, его не принимаем.
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("в файле счётчика не числа")
            self.errors = max(0, int(values[0]))
            self.level = max(0, int(values[1]))
            self.locked_until = float(values[2])
        except (OSError, ValueError, KeyError, TypeError):
            # Файла нет или он испорчен — начинаем с нуля, программа не падает.
            self.errors, self.level, self.locked_until = 0, 0, 0.0

    def save(self):
        data = {"errors": self.errors, "level": self.level, "locked_until": self.locked_until}
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            temporary = self.path + ".tmp"
            with open(temporary, "w", encoding="utf-8") as file:
                json.dump(data, file)
            os.replace(temporary, self.path)  # Файл заменяется целиком, без половинчатой записи.
        except OSError:
            pass  # Нет доступа к папке — защита работает до закрытия программы.

    def remaining(self):
        """Сколько секунд паузы осталось. Не больше самой длинной паузы,
        даже если часы перевели назад или файл подправили."""
        left = self.locked_until - self.clock()
        return max(0.0, min(left, LOCK_STEPS[-1]))

    def errors_left(self):
        return LOCK_AFTER - self.errors % LOCK_AFTER

    def add_error(self):
        """Засчитывает ошибку. Возвращает длительность новой паузы или 0."""
        self.errors += 1
        pause = 0
        if self.errors % LOCK_AFTER == 0:
            pause = LOCK_STEPS[min(self.level, len(LOCK_STEPS) - 1)]
            self.level += 1
            self.locked_until = self.clock() + pause
        self.save()
        return pause

    def success(self):
        self.errors, self.level, self.locked_until = 0, 0, 0.0
        self.save()


class WrongGestureFilter:
    """Решает, когда чужой жест считать ошибкой.

    Рука, переходя от жеста к жесту, на мгновение показывает «чужие» жесты.
    Поэтому ошибка — только чужой жест, который держится WRONG_HOLD секунд,
    и засчитывается он один раз, пока жест не сменится.
    """

    def __init__(self, hold=WRONG_HOLD):
        self.hold = hold
        self.reset()

    def reset(self):
        self.gesture = None
        self.since = None
        self.counted = False

    def update(self, gesture, target, now):
        """Возвращает True ровно в тот момент, когда появилась новая ошибка."""
        if gesture is None or gesture == target:
            self.reset()
            return False
        if gesture != self.gesture:
            self.gesture, self.since, self.counted = gesture, now, False
            return False
        if not self.counted and now - self.since >= self.hold:
            self.counted = True
            return True
        return False


class CaptchaApp:
    """Элементы окна и состояние проверки; self означает этот объект."""

    def __init__(self, root):
        self.root = root
        self.camera = None
        self.detector = None
        self.after_id = None  # Единственное запланированное обновление кадров.
        self.active = False
        self.access_granted = False
        self.target = None
        self.match_since = None
        self.last_frame_at = None
        self.started_at = None
        self.first_frame = None
        self.last_picture = None
        self.preview_image = None
        self.theme_mode = "dark"  # Текущая тема: dark или light.
        self.colors = THEMES[self.theme_mode].copy()  # Активная палитра виджетов.
        self.status_color_key = "muted"  # Нужен, чтобы перекрасить статус при смене темы.
        self.preview_state = "placeholder"  # placeholder, camera, success или timeout.
        self.animation_id = None  # Идентификатор анимации успешной проверки.
        self.loading_id = None  # Идентификатор анимации подключения камеры.
        self.animation_step = 0
        self.loading_step = 0
        self.camera_badge_color_key = "muted"
        self.live_color_key = "muted"
        self.timer_color_key = "text"
        self.lockout = Lockout(LOCKOUT_PATH)  # Счётчик ошибок переживает перезапуск программы.
        self.wrong = WrongGestureFilter()  # Отсеивает мимолётные чужие жесты.
        # Шаги задания: ("gesture", имя жеста), ("flex", "flex") или ("motion", вид движения).
        self.steps = []
        self.step_index = 0
        self.motion = None  # Проверка текущего жеста в движении.
        self.flex = None  # Проверка «сжать и разжать кулак».
        self.notice_until = 0.0  # До этого момента сообщение об ошибке не перезаписывается.
        self.lockout_id = None  # Обратный отсчёт паузы.
        self.difficulty = DEFAULT_DIFFICULTY  # Уровень из выпадающего списка.
        self.time_limit = DIFFICULTY[self.difficulty]["time"]
        self.hold_seconds = DIFFICULTY[self.difficulty]["hold"]
        self.task_image = None  # Картинка текущего шага (держим ссылку, чтобы Tk её не потерял).

        root.title(f"{APP_NAME} — проверка жестом")
        root.configure(fg_color=self.colors["background"])
        # Учитываем масштаб Windows, чтобы окно помещалось и на небольшом экране.
        scale = root._get_window_scaling()
        width = min(1080, max(760, int(root.winfo_screenwidth() / scale) - 60))
        height = min(740, max(520, int(root.winfo_screenheight() / scale) - 80))
        root.geometry(f"{width}x{height}")
        root.minsize(min(900, width), min(600, height))
        root.resizable(True, True)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)  # При увеличении окна растёт область камеры.

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 20))
        header.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(header, text=APP_NAME, font=("Arial", 26, "bold"),
                                        text_color=self.colors["text"], anchor="w")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ctk.CTkLabel(header, text="Проверка доступа с помощью жеста",
                                           font=("Arial", 12), text_color=self.colors["muted"])
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        # Переключатель темы находится в шапке и не мешает выбору камеры.
        self.theme_switch = ctk.CTkSwitch(
            header, text="Тёмная тема", command=self._on_theme_switch,
            width=124, font=("Arial", 10),
            fg_color=self.colors["border"], progress_color=self.colors["accent"],
            button_color=self.colors["text"], button_hover_color=self.colors["secondary_text"],
            text_color=self.colors["muted"])
        self.theme_switch.grid(row=0, column=1, rowspan=2, sticky="e", padx=(14, 14))
        self.theme_switch.select()
        self.camera_badge = ctk.CTkLabel(
            header, text="●  Подготовка", font=("Arial", 12),
            text_color=self.colors["muted"], fg_color=self.colors["panel"], corner_radius=12,
            width=204, height=36)
        self.camera_badge.grid(row=0, column=2, rowspan=2, sticky="e")

        content = ctk.CTkFrame(root, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=24)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, minsize=340)
        content.grid_rowconfigure(0, weight=1)

        # bg_color совпадает с фоном родителя: квадратов за скруглением нет.
        self.video_card = ctk.CTkFrame(content, fg_color=self.colors["panel"],
                                       bg_color=self.colors["background"], corner_radius=CARD_RADIUS,
                                       border_width=1, border_color=self.colors["border"])
        video_card = self.video_card
        video_card.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        video_card.grid_columnconfigure(0, weight=1)
        video_card.grid_rowconfigure(1, weight=1)
        camera_header = ctk.CTkFrame(video_card, fg_color="transparent")
        camera_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 12))
        self.preview_caption = ctk.CTkLabel(camera_header, text="ПРЕДПРОСМОТР", font=("Arial", 11, "bold"),
                                            text_color=self.colors["muted"])
        self.preview_caption.pack(side="left")
        # Выбор камеры переехал в правую панель, к остальным настройкам.
        self.live_label = ctk.CTkLabel(camera_header, text="●  ОЖИДАНИЕ",
                                       text_color=self.colors["muted"], font=(MONO_FONT, 11, "bold"))
        self.live_label.pack(side="right")

        self.video_box = ctk.CTkFrame(video_card, fg_color=self.colors["camera"], corner_radius=14)
        self.video_box.grid(row=1, column=0, sticky="nsew", padx=12)
        self.video_box.grid_columnconfigure(0, weight=1)
        self.video_box.grid_rowconfigure(0, weight=1)
        self.video_box.grid_propagate(False)  # Кадр не меняет размеры окружающих карточек.
        # Пустой пиксель позволяет убрать кадр без ошибки удалённого изображения в Tk.
        empty = Image.new("RGB", (1, 1), self.colors["camera"])
        self.empty_image = ctk.CTkImage(light_image=empty, dark_image=empty, size=(1, 1))
        self.video = ctk.CTkLabel(self.video_box, text="", width=1, height=1)
        self.video.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.video.grid_forget()

        # Заглушка — отдельный виджет: старый кадр не остаётся под текстом ошибки.
        self.placeholder = ctk.CTkFrame(self.video_box, fg_color="transparent")
        self.placeholder.grid(row=0, column=0, padx=20, pady=20)
        self.placeholder_icon = ctk.CTkLabel(
            self.placeholder, text="◉", font=("Arial", 42, "bold"),
            text_color=self.colors["accent"], width=88, height=88, corner_radius=44)
        self.placeholder_icon.pack(pady=(0, 18))
        # Рисуем один раз две небольшие картинки; CTkImage сам выбирает тему.
        self.timeout_image = ctk.CTkImage(
            light_image=draw_timeout_picture(THEMES["light"]),
            dark_image=draw_timeout_picture(THEMES["dark"]), size=(144, 144))
        self.timeout_illustration = ctk.CTkLabel(
            self.placeholder, text="", image=self.timeout_image)
        self.placeholder_title = ctk.CTkLabel(
            self.placeholder, text="Подключение камеры", text_color=self.colors["text"],
            font=("Arial", 20, "bold"), wraplength=360)
        self.placeholder_title.pack()
        self.placeholder_hint = ctk.CTkLabel(
            self.placeholder, text="Изображение появится здесь", wraplength=360,
            justify="center", font=("Arial", 12), text_color=self.colors["muted"])
        self.placeholder_hint.pack(pady=(10, 0))
        self.video_box.bind("<Configure>", self.resize_preview)
        # Под видео — что видит камера прямо сейчас: «Распознано: кулак», «Рука далеко»…
        self.detected = ctk.CTkLabel(
            video_card, text="Ожидание камеры", text_color=self.colors["text"], font=("Arial", 13))
        self.detected.grid(row=2, column=0, pady=(8, 12))

        self.panel = ctk.CTkFrame(content, width=340, fg_color=self.colors["panel"],
                                  bg_color=self.colors["background"], corner_radius=CARD_RADIUS,
                                  border_width=1, border_color=self.colors["border"])
        self.panel.grid(row=0, column=1, sticky="nsew")
        self.panel.grid_propagate(False)
        self.panel.grid_columnconfigure(0, weight=1)
        self.panel.grid_rowconfigure(0, weight=1)
        # Панель из четырёх частей сверху вниз:
        # 0 — задание (прокручивается в низком окне), 1 — результат проверки,
        # 2 — сложность и камера, 3 — кнопки. Части 1–3 не прокручиваются и всегда видны.
        self.details = ctk.CTkScrollableFrame(
            self.panel, fg_color=self.colors["panel"], corner_radius=0,
            scrollbar_button_color=self.colors["border"], scrollbar_button_hover_color=self.colors["muted"])
        details = self.details
        details.grid(row=0, column=0, sticky="nsew", padx=(18, 10), pady=(18, 0))
        task_header = ctk.CTkFrame(details, fg_color="transparent")
        task_header.pack(fill="x", pady=(0, 12))
        self.task_section_label = ctk.CTkLabel(task_header, text="ВАШЕ ЗАДАНИЕ", font=("Arial", 11, "bold"),
                                               text_color=self.colors["accent"])
        self.task_section_label.pack(side="left")
        self.timer = ctk.CTkLabel(task_header, text="—", width=68, height=28,
                                  fg_color=self.colors["panel_light"], corner_radius=8,
                                  text_color=self.colors["text"], font=(MONO_FONT, 13, "bold"))
        self.timer.pack(side="right")
        # Картинка жеста слева от названия: не нужно угадывать жест по тексту.
        task_row = ctk.CTkFrame(details, fg_color="transparent")
        task_row.pack(fill="x", pady=(0, 10))
        self.picture_label = ctk.CTkLabel(task_row, text="", width=88, height=88)
        self.picture_label.pack(side="left", padx=(0, 12))
        self.task_label = ctk.CTkLabel(
            task_row, text="Подготовка задания", wraplength=180, justify="left",
            anchor="w", text_color=self.colors["text"], font=("Arial", 21, "bold"))
        self.task_label.pack(side="left", fill="x", expand=True)
        self.hint = ctk.CTkLabel(
            details, text="", wraplength=282, justify="left", anchor="w",
            text_color=self.colors["secondary_text"], font=("Arial", 13))
        self.hint.pack(fill="x")

        self.guide = ctk.CTkFrame(details, fg_color="transparent")  # Без рамки: при прокрутке не выглядит обрезанным.
        self.guide.pack(fill="x", pady=(14, 4))
        self.guide_title = ctk.CTkLabel(self.guide, text="КАК ПРОЙТИ ПРОВЕРКУ", font=("Arial", 10, "bold"),
                                        text_color=self.colors["accent"])
        self.guide_title.pack(anchor="w", pady=(0, 2))
        self.guide_text = ctk.CTkLabel(
            self.guide, text="Покажите кисть целиком, пальцами вверх.",
            wraplength=248, justify="left", anchor="w",
            text_color=self.colors["secondary_text"], font=("Arial", 12))
        self.guide_text.pack(fill="x", pady=(0, 8))

        # Часть 1: что видит камера и результат — всегда на виду.
        live_block = ctk.CTkFrame(self.panel, fg_color="transparent")
        live_block.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 0))
        progress_row = ctk.CTkFrame(live_block, fg_color="transparent")
        progress_row.pack(fill="x")
        self.progress_caption = ctk.CTkLabel(progress_row, text="Удержание жеста", text_color=self.colors["muted"],
                                              font=("Arial", 11))
        self.progress_caption.pack(side="left")
        self.hold_label = ctk.CTkLabel(progress_row, text="0.0 с",
                                       text_color=self.colors["muted"], font=(MONO_FONT, 11))
        self.hold_label.pack(side="right")
        self.progress = ctk.CTkProgressBar(live_block, height=8, corner_radius=4,
                                           fg_color=self.colors["border"], progress_color=self.colors["accent"])
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(4, 12))

        self.result_box = ctk.CTkFrame(live_block, fg_color=self.colors["result"], corner_radius=12)
        self.result_box.pack(fill="x")
        self.status = ctk.CTkLabel(
            self.result_box, text="Доступ закрыт", wraplength=270,
            justify="left", anchor="w", text_color=self.colors["muted"], font=(MONO_FONT, 19, "bold"))
        self.status.pack(fill="x", padx=14, pady=(10, 0))
        self.result_hint = ctk.CTkLabel(
            self.result_box, text="Подготавливаем проверку", wraplength=270,
            justify="left", anchor="w", text_color=self.colors["muted"], font=("Arial", 12))
        self.result_hint.pack(fill="x", padx=14, pady=(0, 10))

        # Часть 2: сложность и камера рядом, над кнопками.
        settings = ctk.CTkFrame(self.panel, fg_color="transparent")
        settings.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 0))
        settings.grid_columnconfigure((0, 1), weight=1)
        menu_style = dict(height=30, corner_radius=9, font=("Arial", 11), dynamic_resizing=False)
        self.difficulty_choice = ctk.CTkOptionMenu(
            settings, values=list(DIFFICULTY), command=self.change_difficulty, **menu_style)
        self.difficulty_choice.set(self.difficulty)
        self.difficulty_choice.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.camera_choice = ctk.CTkOptionMenu(
            settings, values=[f"Камера {i}" for i in range(3)], command=self.change_camera, **menu_style)
        self.camera_choice.set(f"Камера {CAMERA_INDEX}")
        self.camera_choice.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Часть 3: главная кнопка. «Выйти» переехала в шапку, чтобы заданию хватало места.
        self.new_button = ctk.CTkButton(
            self.panel, text="Новое задание", command=self.new_challenge,
            height=44, corner_radius=12, fg_color=self.colors["accent"],
            hover_color=self.colors["button_hover"], text_color=self.colors["button_text"],
            font=("Arial", 13, "bold"))
        self.new_button.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 18))
        self.exit_button = ctk.CTkButton(
            header, text="Выйти", command=self.close, width=76, height=36, corner_radius=12,
            fg_color="transparent", hover_color=self.colors["secondary_hover"], border_width=1,
            border_color=self.colors["border"], text_color=self.colors["muted"], font=("Arial", 12))
        self.exit_button.grid(row=0, column=3, rowspan=2, sticky="e", padx=(10, 0))
        self.footer_label = ctk.CTkLabel(
            root, text="R — новая попытка  ·  T — тема  ·  Space — старт  ·  Esc — выход",
            text_color=self.colors["muted"], font=("Arial", 11))
        self.footer_label.grid(row=2, column=0, pady=(12, 12))
        # bind_all работает даже тогда, когда фокус находится на кнопке или меню.
        root.bind_all("<KeyPress-r>", self._on_shortcut_retry)
        root.bind_all("<KeyPress-R>", self._on_shortcut_retry)
        root.bind_all("<KeyPress-t>", self._on_shortcut_theme)
        root.bind_all("<KeyPress-T>", self._on_shortcut_theme)
        root.bind_all("<KeyPress-space>", self._on_shortcut_space)
        root.bind_all("<Escape>", self._on_shortcut_close)
        self.apply_theme()  # Применяем палитру после создания всех виджетов.
        self.after_id = root.after(150, self.new_challenge)  # Сначала рисуем окно.

    def _on_theme_switch(self):
        """Применяет тему после клика по переключателю."""
        mode = "dark" if self.theme_switch.get() else "light"
        self.set_theme(mode)

    def _on_shortcut_retry(self, event=None):
        """Клавиша R запускает новую попытку, когда кнопка уже доступна."""
        try:
            if self.new_button.cget("state") == "disabled":
                return "break"
        except Exception:
            pass
        self.new_challenge()
        return "break"

    def _on_shortcut_theme(self, event=None):
        """Клавиша T переключает светлую и тёмную темы."""
        mode = "light" if self.theme_mode == "dark" else "dark"
        if mode == "dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.set_theme(mode)
        return "break"

    def _on_shortcut_space(self, event=None):
        """Пробел удобен для старта новой проверки после ошибки или успеха."""
        if not self.active:
            self.new_challenge()
        return "break"

    def _on_shortcut_close(self, event=None):
        """Esc закрывает окно так же, как кнопка «Выйти»."""
        self.close()
        return "break"

    def set_theme(self, mode):
        """Меняет палитру CustomTkinter без перезапуска камеры."""
        if mode not in THEMES:
            mode = "dark"  # Защита от случайного неизвестного значения.
        self.theme_mode = mode
        self.colors = THEMES[mode].copy()
        ctk.set_appearance_mode(mode)
        self.apply_theme()

    def apply_theme(self):
        """Перекрашивает уже созданные элементы по активной палитре."""
        c = self.colors
        self.root.configure(fg_color=c["background"])
        self.title_label.configure(text_color=c["text"])
        self.subtitle_label.configure(text_color=c["muted"])
        self.theme_switch.configure(
            text="Тёмная тема" if self.theme_mode == "dark" else "Светлая тема",
            fg_color=c["border"], progress_color=c["accent"],
            button_color=c["text"], button_hover_color=c["secondary_text"],
            text_color=c["muted"])
        self.camera_badge.configure(
            fg_color=c["panel"], text_color=c[self.camera_badge_color_key])
        self.video_card.configure(
            fg_color=c["panel"], bg_color=c["background"], border_color=c["border"])
        self.preview_caption.configure(text_color=c["muted"])
        for menu in (self.camera_choice, self.difficulty_choice):
            menu.configure(
                fg_color=c["panel_light"], button_color=c["panel_light"],
                button_hover_color=c["secondary_hover"], text_color=c["text"],
                dropdown_fg_color=c["panel"], dropdown_hover_color=c["secondary_hover"],
                dropdown_text_color=c["text"])
        self.live_label.configure(text_color=c[self.live_color_key])
        self.style_placeholder()
        self.placeholder_hint.configure(text_color=c["muted"])
        self.panel.configure(
            fg_color=c["panel"], bg_color=c["background"], border_color=c["border"])
        self.details.configure(
            fg_color=c["panel"], bg_color=c["panel"],
            scrollbar_button_color=c["border"], scrollbar_button_hover_color=c["muted"])
        self.task_section_label.configure(text_color=c["accent"])
        self.timer.configure(fg_color=c["panel_light"], text_color=c[self.timer_color_key])
        self.task_label.configure(text_color=c["text"])
        self.hint.configure(text_color=c["secondary_text"])
        self.guide.configure(fg_color="transparent")
        self.guide_title.configure(text_color=c["accent"])
        self.guide_text.configure(text_color=c["secondary_text"])
        self.detected.configure(text_color=c["text"])
        self.progress_caption.configure(text_color=c["muted"])
        self.hold_label.configure(text_color=c["muted"])
        self.progress.configure(fg_color=c["border"], progress_color=c["accent"])
        self.result_box.configure(
            fg_color=c["success_panel"] if self.status_color_key == "success"
            else c["timeout_panel"] if self.status_color_key == "warning" else c["result"])
        self.status.configure(text_color=c[self.status_color_key])
        self.result_hint.configure(text_color=c["muted"])
        self.set_main_button(self.new_button.cget("state"), self.new_button.cget("text"))
        self.exit_button.configure(hover_color=c["secondary_hover"], text_color=c["muted"],
                                   border_color=c["border"])
        self.footer_label.configure(text_color=c["muted"])

    def set_main_button(self, state, text):
        """Главная кнопка: яркая, когда нажимать можно, и приглушённая, когда нельзя."""
        c = self.colors
        enabled = state == "normal"
        self.new_button.configure(
            state=state, text=text,
            fg_color=c["accent"] if enabled else c["panel_light"],
            hover_color=c["button_hover"], text_color=c["button_text"],
            text_color_disabled=c["muted"])

    def change_difficulty(self, choice):
        """Новый уровень сразу даёт новое задание с его шагами и временем."""
        self.difficulty = choice
        self.difficulty_choice.set(choice)  # Список всегда показывает текущий уровень.
        self.new_challenge()

    def stop_animations(self):
        """Отменяет запланированные callbacks, чтобы они не работали после смены экрана."""
        for attribute in ("animation_id", "loading_id", "lockout_id"):
            callback_id = getattr(self, attribute, None)
            if callback_id is not None:
                try:
                    self.root.after_cancel(callback_id)
                except Exception:
                    pass
                setattr(self, attribute, None)

    def start_loading_animation(self):
        """Запускает мягкую анимацию ожидания камеры."""
        self.stop_animations()
        self.loading_step = 0
        self.animate_loading()

    def animate_loading(self):
        """Меняет символ заглушки через after, не блокируя окно."""
        if self.active or self.access_granted or self.preview_state != "placeholder":
            self.loading_id = None
            return
        frames = ("◉", "◌", "○", "◌")
        self.placeholder_icon.configure(text=frames[self.loading_step % len(frames)])
        self.loading_step += 1
        self.loading_id = self.root.after(220, self.animate_loading)

    def start_success_animation(self):
        """Запускает небольшую пульсацию галочки после успешной проверки."""
        self.stop_animations()
        self.animation_step = 0
        self.animate_success()

    def animate_success(self):
        """Пульсация размера галочки подчёркивает результат, но не грузит CPU."""
        if not self.access_granted or self.preview_state != "success":
            self.animation_id = None
            return
        sizes = (42, 46, 50, 46)
        self.placeholder_icon.configure(font=("Arial", sizes[self.animation_step % len(sizes)], "bold"))
        self.animation_step += 1
        self.animation_id = self.root.after(180, self.animate_success)

    def set_progress(self, held):
        """CTkProgressBar принимает долю от 0 до 1, а не число секунд."""
        held = min(max(held, 0), self.hold_seconds)
        self.progress.set(held / self.hold_seconds)
        self.hold_label.configure(text=f"{held:.1f} / {self.hold_seconds:g} с")

    def set_status(self, text, color, hint):
        """В CustomTkinter нужны configure и text_color; config и fg не подходят."""
        # Запоминаем смысл цвета, чтобы текущий статус правильно перекрашивался
        # при переключении темы даже посреди проверки.
        color_keys = {
            "success": (self.colors["success"], SUCCESS_COLOR),
            "warning": (self.colors["warning"],),
            "danger": (self.colors["danger"], DANGER_COLOR),
            "accent": (self.colors["accent"], ACCENT_COLOR),
            "muted": (self.colors["muted"], MUTED_COLOR),
        }
        self.status_color_key = next(
            (key for key, values in color_keys.items() if color in values), "muted")
        self.status.configure(text=text, text_color=color)
        self.result_hint.configure(text=hint)
        self.result_box.configure(
            fg_color=self.colors["success_panel"] if self.status_color_key == "success"
            else self.colors["timeout_panel"] if self.status_color_key == "warning" else self.colors["result"])

    def set_camera_badge(self, text, color):
        color_keys = {
            "success": (self.colors["success"], SUCCESS_COLOR),
            "danger": (self.colors["danger"], DANGER_COLOR),
            "accent": (self.colors["accent"], ACCENT_COLOR),
            "muted": (self.colors["muted"], MUTED_COLOR),
        }
        self.camera_badge_color_key = next(
            (key for key, values in color_keys.items() if color in values), "muted")
        self.camera_badge.configure(text="●  " + text, text_color=color)

    def style_placeholder(self):
        """Подбирает фон и цвет текста для текущего состояния и темы."""
        c = self.colors
        background, title_color = c["camera"], c["text"]
        if self.preview_state == "success":
            background, title_color = c["success_preview"], c["success"]
        elif self.preview_state == "timeout":
            background, title_color = c["timeout_preview"], c["warning"]
        self.video_box.configure(fg_color=background)
        self.placeholder_title.configure(text_color=title_color)
        self.placeholder_icon.configure(
            text_color=c["success"] if self.preview_state == "success" else c["accent"],
            fg_color=c["success_icon"] if self.preview_state == "success" else "transparent")

    def show_placeholder(self, title, hint, success=False, loading=False, timeout=False):
        """Полностью убирает кадр и показывает фон, галочку или картинку часов."""
        self.stop_animations()
        self.last_picture = None
        self.preview_state = "timeout" if timeout else "success" if success else "placeholder"
        # grid_forget также убирает сохранённое размещение CustomTkinter:
        # скрытый элемент не появится сам при изменении масштаба экрана.
        self.video.grid_forget()
        self.video.configure(image=self.empty_image)  # Заменяем кадр пустым пикселем.
        self.preview_image = None  # Освобождаем сохранённый кадр и его масштабированные копии.
        # При повторе прячем часы и возвращаем обычный значок на его место.
        self.timeout_illustration.pack_forget()
        self.placeholder_icon.pack_forget()
        if timeout:
            self.timeout_illustration.pack(before=self.placeholder_title, pady=(0, 14))
        else:
            self.placeholder_icon.pack(before=self.placeholder_title, pady=(0, 18))
        self.placeholder_icon.configure(
            text="✓" if success else "◉",
            font=("Arial", 42, "bold"))
        self.placeholder_title.configure(text=title)
        self.style_placeholder()
        self.placeholder_hint.configure(text=hint, text_color=self.colors["muted"])
        self.placeholder.grid(row=0, column=0, padx=20, pady=20)
        if success:
            self.start_success_animation()
        elif loading:
            self.start_loading_animation()

    def resize_preview(self, event=None):
        """Вписывает видео в доступное место и сохраняет его пропорции."""
        # CustomTkinter хранит логические размеры, а winfo возвращает пиксели экрана.
        scale = self.video_box._get_widget_scaling()
        width = max(1, int(self.video_box.winfo_width() / scale) - 16)
        height = max(1, int(self.video_box.winfo_height() / scale) - 16)
        self.placeholder_title.configure(wraplength=max(180, width - 40))
        self.placeholder_hint.configure(wraplength=max(180, width - 40))
        if self.last_picture is None:
            return
        picture = self.last_picture.copy()
        ratio = min(width / picture.width, height / picture.height)
        size = (max(1, int(picture.width * ratio)), max(1, int(picture.height * ratio)))
        # CTkImage учитывает масштаб экрана; ImageTk.PhotoImage здесь не требуется.
        if self.preview_image is None:
            self.preview_image = ctk.CTkImage(light_image=picture, dark_image=picture, size=size)
            self.video.configure(image=self.preview_image)
        else:
            self.preview_image.configure(light_image=picture, dark_image=picture, size=size)

    def change_camera(self, choice):
        self.new_challenge()  # Выбранный номер читается из меню при запуске.

    def new_challenge(self):
        """Закрывает прошлый доступ, сбрасывает таймер и подключает выбранную камеру."""
        self.stop_animations()
        self.stop_camera()
        self.access_granted = False
        self.match_since = None
        self.last_frame_at = None
        self.started_at = None
        self.first_frame = None
        if self.lockout.remaining() > 0:  # Во время паузы камера не включается.
            self.show_lockout()
            return
        self.set_main_button("disabled", "Подключение…")
        self.camera_choice.configure(state="disabled")
        self.difficulty_choice.configure(state="disabled")
        self.set_camera_badge("Подключение камеры", self.colors["accent"])
        # Шаги, время и удержание зависят от выбранного уровня сложности.
        level = DIFFICULTY[self.difficulty]
        self.time_limit, self.hold_seconds = level["time"], level["hold"]
        self.steps = build_steps(self.difficulty, secrets.choice, previous=self.target)
        self.target = self.steps[0][1]
        self.step_index = 0
        self.motion = None
        self.flex = None
        self.wrong.reset()
        self.notice_until = 0.0
        self.show_step()
        self.set_status("Доступ закрыт", self.colors["muted"], "Ожидаем изображение с камеры")
        self.detected.configure(text="Подключение камеры…")
        self.timer_color_key = "text"
        self.timer.configure(text="—", text_color=self.colors["text"])
        self.set_progress(0)
        self.show_placeholder("Подключение камеры", "Подождите несколько секунд", loading=True)
        self.root.update_idletasks()
        try:
            index = int(self.camera_choice.get().split()[-1])
            self.camera, self.first_frame = open_camera(index)
            self.detector = mp.solutions.hands.Hands(
                static_image_mode=False,  # Следим за кистью в потоке кадров.
                max_num_hands=2,  # Две руки обнаруживаем, но не засчитываем.
                model_complexity=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7,
            )
            self.active = True
            self.set_main_button("normal", "Новое задание")
            self.camera_choice.configure(state="normal")
            self.difficulty_choice.configure(state="normal")
            self.update_frame()
        except Exception as error:
            self.fail(str(error))

    def update_frame(self):
        """Получает кадр, распознаёт жест и планирует следующее обновление."""
        self.after_id = None
        if not self.active:
            return
        try:
            self.stop_animations()
            self.preview_state = "camera"
            self.video_box.configure(fg_color=self.colors["camera"])
            if self.first_frame is not None:
                frame = self.first_frame  # Проверенный кадр уже получен при подключении.
                self.first_frame = None
            else:
                ok, frame = self.camera.read()
                if not ok or frame is None or frame.size == 0:
                    raise RuntimeError("Камера перестала передавать изображение. Проверьте подключение и повторите попытку.")
            frame = cv2.flip(frame, 1)  # Зеркальный предпросмотр.
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.detector.process(rgb)
            hands = result.multi_hand_landmarks or []
            gesture = None
            points = None  # 21 точка кисти, если в кадре ровно одна рука.
            if len(hands) == 1:
                points = hands[0].landmark
                gesture = recognize_gesture(points)
                if gesture:
                    self.detected.configure(text="Распознано: " + GESTURES[gesture][0])
                else:  # Объясняем, что мешает: рука далеко, у края, наклонена…
                    self.detected.configure(text="Не распознано: " + gesture_problem(points).lower())
                # Скелет руки в цветах темы: линии — акцент, точки — цвет текста.
                drawing = mp.solutions.drawing_utils
                drawing.draw_landmarks(
                    rgb, hands[0], mp.solutions.hands.HAND_CONNECTIONS,
                    drawing.DrawingSpec(color=hex_to_rgb(self.colors["text"]), thickness=2, circle_radius=3),
                    drawing.DrawingSpec(color=hex_to_rgb(self.colors["accent"]), thickness=3))
            elif len(hands) > 1:
                self.detected.configure(text="Оставьте в кадре одну руку")
            else:
                self.detected.configure(text="Покажите руку в кадре")
            self.last_picture = Image.fromarray(rgb)
            self.resize_preview()
            self.placeholder.grid_forget()
            self.video.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            now = time.monotonic()
            if self.started_at is None:
                self.started_at = now  # Время подключения не отнимается от попытки.
                self.set_camera_badge("Камера подключена", self.colors["success"])
                self.live_color_key = "accent"
                self.live_label.configure(text="●  LIVE", text_color=self.colors["accent"])
            self.check_result(gesture, now, points)
        except Exception as error:
            self.fail(str(error))
            return
        if self.active:
            self.after_id = self.root.after(30, self.update_frame)

    def check_result(self, gesture, now, points=None):
        """Доступ открывается, когда все шаги задания выполнены до конца таймера."""
        if not self.active:
            return
        remaining = self.time_limit - (now - self.started_at)
        self.timer_color_key = "danger" if remaining <= 5 else "text"
        self.timer.configure(text=f"{max(0, remaining):.1f} с",
                             text_color=self.colors[self.timer_color_key])
        if remaining <= 0:
            self.access_granted = False
            self.match_since = None
            self.set_progress(0)
            self.stop_camera()
            self.show_placeholder(
                "Время вышло",
                "Камера выключена. Нажмите «Повторить попытку» или пробел.",
                timeout=True,
            )
            self.set_status("Время вышло", self.colors["warning"], "Доступ закрыт. Попробуйте ещё раз.")
            self.timer_color_key = "warning"
            self.timer.configure(text="0.0 с", text_color=self.colors["warning"])
            self.detected.configure(text="Проверка завершена")  # Убираем последний распознанный жест.
            self.set_main_button("normal", "Повторить попытку")
            if self.lockout.add_error():  # Истёкшее время — тоже неудачная попытка.
                self.show_lockout()
            return
        if self.last_frame_at is not None and now - self.last_frame_at > MAX_FRAME_GAP:
            self.match_since = None  # Пауза в кадрах не считается удержанием.
        self.last_frame_at = now
        kind = self.steps[self.step_index][0]
        if kind == "motion":
            self.check_motion(points, now)
            return
        if kind == "flex":
            self.check_flex(points, gesture, now)
            return
        if self.wrong.update(gesture, self.target, now) and self.register_error(now):
            return  # Пятая ошибка — началась пауза.
        if gesture != self.target:
            self.match_since = None
            self.set_progress(0)
            if now >= self.notice_until:
                self.set_status("Доступ закрыт", self.colors["muted"], "Покажите нужный жест и удерживайте его")
            return
        if self.match_since is None:
            self.match_since = now
        held = now - self.match_since
        self.set_progress(held)
        if held < self.hold_seconds:
            self.set_status("Жест совпадает", self.colors["accent"], "Не меняйте положение руки")
            return
        self.finish_step(now)

    def check_motion(self, points, now):
        """Шаг с движением: следим за центром ладони, а не за формой пальцев."""
        if points is not None and self.motion.add(points, now):
            self.set_step_progress(1.0)
            self.finish_step(now)
            return
        self.set_step_progress(self.motion.progress())
        if now >= self.notice_until:
            if points is None:
                self.set_status("Доступ закрыт", self.colors["muted"], "Покажите одну руку и выполните движение")
            else:
                self.set_status("Выполните движение", self.colors["accent"], "Двигайте рукой плавно, не убирая её из кадра")

    def check_flex(self, points, gesture, now):
        """Шаг «сжать и разжать кулак»: считаем смены формы руки без разрывов."""
        if self.flex.add(points, gesture, now):
            self.set_step_progress(1.0)  # Последнее сжатие: полоса доходит до конца.
            self.finish_step(now)
            return
        self.set_step_progress(self.flex.progress())
        if self.flex.just_reset:  # Рука пропала или прыгнула — показываем причину.
            self.set_status("Начните сначала", self.colors["danger"], self.flex.reset_reason)
            self.notice_until = now + 1.5
        elif now >= self.notice_until:
            done, need = self.flex.changes, self.flex.changes_needed
            self.set_status("Сжимайте и разжимайте", self.colors["accent"], f"Смен формы: {done} из {need}")

    def show_step(self):
        """Показывает в панели текущий шаг задания."""
        kind, name = self.steps[self.step_index]
        tasks = {"gesture": GESTURES, "motion": MOTIONS, "flex": {"flex": FLEX_TASK}}
        title, hint = tasks[kind][name]
        self.task_label.configure(text=title)
        self.hint.configure(text=hint)
        self.task_section_label.configure(
            text=f"ВАШЕ ЗАДАНИЕ · ШАГ {self.step_index + 1} ИЗ {len(self.steps)}")
        captions = {"gesture": "Удержание жеста", "motion": "Движение", "flex": "Сжатия кулака"}
        self.progress_caption.configure(text=captions[kind])
        # Картинка в двух вариантах: CustomTkinter сам покажет нужный для темы.
        self.task_image = ctk.CTkImage(
            light_image=draw_gesture_picture(kind, name, THEMES["light"]),
            dark_image=draw_gesture_picture(kind, name, THEMES["dark"]), size=(88, 88))
        self.picture_label.configure(image=self.task_image)
        guides = {
            "gesture": f"Покажите кисть целиком, пальцами вверх, и удерживайте жест {self.hold_seconds:g} с.",
            "flex": "Не убирайте руку из кадра. Если рука пропадёт или дёрнется, счёт начнётся заново.",
            "motion": "Двигайте рукой плавно, не убирая её из кадра.",
        }
        self.guide_text.configure(text=f"Уровень «{self.difficulty}». " + guides[kind])

    def set_step_progress(self, part):
        """Прогресс шага с движением или сжатиями — в процентах, а не в секундах."""
        self.progress.set(part)
        self.hold_label.configure(text=f"{part * 100:.0f} %")

    def finish_step(self, now):
        """Переходит к следующему шагу или открывает доступ после последнего."""
        self.step_index += 1
        if self.step_index >= len(self.steps):
            self.grant_access()
            return
        kind, name = self.steps[self.step_index]
        self.match_since = None
        self.wrong.reset()
        self.motion = MotionChallenge(name) if kind == "motion" else None
        self.flex = FlexChallenge() if kind == "flex" else None
        if kind == "gesture":
            self.target = name
            self.set_progress(0)
        else:
            self.set_step_progress(0)
        self.show_step()
        self.set_status("Шаг пройден", self.colors["success"], "Выполните следующее задание")
        self.notice_until = now + 1.2

    def register_error(self, now, title="Неверный жест", hint=""):
        """Засчитывает ошибку. Возвращает True, если началась пауза."""
        if self.lockout.add_error():
            self.show_lockout()
            return True
        left = self.lockout.errors_left()
        self.set_status(title, self.colors["danger"], f"{hint} До паузы осталось ошибок: {left}.".strip())
        self.notice_until = now + 1.5
        return False

    def show_lockout(self):
        """Пауза после серии ошибок: камера выключена, идёт обратный отсчёт."""
        self.stop_camera()
        self.access_granted = False
        self.match_since = None
        self.set_progress(0)
        self.show_placeholder("Слишком много ошибок", "", timeout=True)
        self.set_status("Пауза", self.colors["warning"],
                        f"Защита от перебора: после {LOCK_AFTER} ошибок нужно подождать.")
        self.detected.configure(text="Проверка остановлена")
        # Старое задание прячем: во время паузы выполнять его нельзя.
        self.task_section_label.configure(text="ЗАЩИТА ОТ ПЕРЕБОРА")
        self.task_label.configure(text="Подождите")
        self.picture_label.configure(image=self.empty_image)
        self.task_image = None
        self.guide_text.configure(text="Пока идёт пауза, можно выбрать другой уровень или камеру.")
        self.hint.configure(text="Новое задание появится после паузы.")
        self.set_main_button("disabled", "Пауза…")
        self.camera_choice.configure(state="normal")
        self.difficulty_choice.configure(state="normal")
        self.tick_lockout()

    def tick_lockout(self):
        """Обновляет обратный отсчёт; по окончании паузы снова разрешает попытку."""
        self.lockout_id = None
        left = self.lockout.remaining()
        if left <= 0:
            self.placeholder_title.configure(text="Пауза закончилась")
            self.placeholder_hint.configure(text="Нажмите «Новое задание» или пробел.")
            self.timer_color_key = "text"
            self.timer.configure(text="—", text_color=self.colors["text"])
            self.set_status("Доступ закрыт", self.colors["muted"], "Можно попробовать снова.")
            self.set_main_button("normal", "Новое задание")
            return
        self.placeholder_hint.configure(
            text=f"Следующая попытка через {math.ceil(left)} с.\nПерезапуск программы паузу не снимает.")
        self.timer_color_key = "warning"
        self.timer.configure(text=f"{math.ceil(left)} с", text_color=self.colors["warning"])
        self.lockout_id = self.root.after(250, self.tick_lockout)

    def grant_access(self):
        """Все шаги выполнены: доступ открыт, счётчик ошибок обнуляется."""
        self.lockout.success()
        # Дальше — блок успеха из версии 2.2 без изменений.
        self.access_granted = True
        self.set_status("Доступ открыт", self.colors["success"], "Проверка пройдена. Камера выключена.")
        self.stop_camera()
        self.show_placeholder(
            "Проверка пройдена",
            "Камера выключена. Для новой проверки нажмите «Пройти ещё раз».",
            success=True,
        )
        self.timer_color_key = "success"
        self.timer.configure(text="Готово", text_color=self.colors["success"])
        self.detected.configure(text="Проверка завершена")
        self.new_button.configure(text="Пройти ещё раз")

    def fail(self, message):
        """Ошибка остаётся в окне, а кнопка повтора снова становится доступной."""
        self.access_granted = False
        self.match_since = None
        self.set_progress(0)
        self.stop_camera()
        self.set_status("Доступ закрыт", self.colors["danger"], "Выберите камеру и повторите попытку")
        self.set_camera_badge("Ошибка подключения", self.colors["danger"])
        self.detected.configure(text="Проверка остановлена")
        self.timer.configure(text="—")
        self.show_placeholder("Не удалось запустить проверку", message)
        self.set_main_button("normal", "Повторить попытку")
        self.camera_choice.configure(state="normal")
        self.difficulty_choice.configure(state="normal")

    def stop_camera(self):
        """Отменяет обновление и освобождает камеру, в том числе после ошибки."""
        self.active = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        if self.detector is not None:
            self.detector.close()
            self.detector = None
        self.first_frame = None
        self.live_color_key = "muted"
        self.live_label.configure(text="●  ОСТАНОВЛЕНО", text_color=self.colors["muted"])
        self.set_camera_badge("Камера выключена", self.colors["muted"])

    def close(self):
        self.stop_animations()
        self.stop_camera()
        self.root.destroy()


if __name__ == "__main__":
    # При импорте файла для проверки логики камера не включается.
    try:
        import cv2  # Чтение камеры и преобразование кадров.
        import mediapipe as mp  # Нейросеть для поиска 21 точки кисти.
        import customtkinter as ctk  # Современный интерфейс поверх Tkinter.
        from PIL import Image  # Преобразование кадра в изображение для CTkImage.
    except ImportError as error:
        raise SystemExit(
            "Не удалось подключить библиотеки: " + str(error) + "\n"
            "Используйте Python 3.11/3.12 (64-bit) и выполните:\n"
            "python -m pip install mediapipe==0.10.21 opencv-contrib-python==4.11.0.86 "
            "numpy==1.26.4 pillow==11.3.0 customtkinter==5.2.2"
        ) from error
    if not hasattr(mp, "solutions"):
        raise SystemExit("Нужна версия mediapipe==0.10.21. Установите её по инструкции в начале файла.")
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    window = ctk.CTk()
    app = CaptchaApp(window)
    window.mainloop()  # Обработка кнопок и запланированных кадров.
