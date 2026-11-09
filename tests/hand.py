"""Синтетическая кисть для тестов: 21 точка в формате MediaPipe (x, y от 0 до 1).

Камера и нейросеть не нужны: мы сами задаём, какие пальцы подняты.
Кисть стоит пальцами вверх, координата y растёт вниз, как в MediaPipe.
"""

from types import SimpleNamespace

# Какие пальцы подняты: указательный, средний, безымянный, мизинец.
PATTERNS = {
    "palm": (True, True, True, True),
    "peace": (True, True, False, False),
    "index": (True, False, False, False),
    "three": (True, True, True, False),
    "rock": (True, False, False, True),
    "fist": (False, False, False, False),
    "thumbs_up": (False, False, False, False),
}


def make_points(fingers, thumb_up=False, cx=0.5, wrist_y=0.8, palm=0.2):
    """Возвращает 21 точку. fingers — четыре True/False, palm — высота ладони."""
    points = [SimpleNamespace(x=cx, y=wrist_y - palm) for _ in range(21)]
    points[0] = SimpleNamespace(x=cx, y=wrist_y)  # Запястье.
    points[9] = SimpleNamespace(x=cx, y=wrist_y - palm)  # Основание среднего пальца.
    joint_y = wrist_y - palm * 1.25  # Средние суставы пальцев (точки 6, 10, 14, 18).
    for number, (tip, up) in enumerate(zip((8, 12, 16, 20), fingers)):
        x = cx - palm * 0.3 + number * palm * 0.2
        points[tip - 2] = SimpleNamespace(x=x, y=joint_y)
        # Поднятый палец: кончик заметно выше сустава; согнутый — ниже.
        tip_y = joint_y - palm * 0.4 if up else joint_y + palm * 0.25
        points[tip] = SimpleNamespace(x=x, y=tip_y)
    # Большой палец: точка 3 — сустав, точка 4 — кончик.
    points[3] = SimpleNamespace(x=cx - palm * 0.5, y=wrist_y - palm * 0.6)
    thumb_tip_y = points[3].y - palm * 0.4 if thumb_up else points[3].y + palm * 0.05
    points[4] = SimpleNamespace(x=cx - palm * 0.55, y=thumb_tip_y)
    return points


def gesture_points(name, **kwargs):
    """Точки для жеста по его названию в коде (palm, fist, thumbs_up и т. д.)."""
    return make_points(PATTERNS[name], thumb_up=(name == "thumbs_up"), **kwargs)
