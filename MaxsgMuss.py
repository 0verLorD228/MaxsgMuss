"""
MaxsgMuss — учебная капча с камерой на Python.

Запуск: Python 3.11 или 3.12 (64-bit).
Один раз установите библиотеки в терминале:
python -m pip install mediapipe==0.10.21 opencv-contrib-python==4.11.0.86 numpy==1.26.4 pillow==11.3.0 customtkinter==5.2.2
Затем: python MaxsgMuss.py

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
Окно на customtkinter, выбор задания, таймер и логика доступа написаны для этого проекта.

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

import secrets  # Выбирает случайное задание.
import sys  # Позволяет узнать операционную систему.
import time  # Измеряет длительность удержания жеста.


# Эти настройки можно менять, не переписывая остальную программу.
APP_NAME = "MaxsgMuss"  # Название в шапке приложения и заголовке окна.
CAMERA_INDEX = 0  # Номер камеры: обычно 0; для другой камеры попробуйте 1.
HOLD_SECONDS = 1.5  # Сколько секунд подряд нужно показывать нужный жест.
TIME_LIMIT = 30  # Сколько секунд даётся на выполнение задания.
MAX_FRAME_GAP = 0.5  # При большой паузе между кадрами удержание сбрасывается.
BACKGROUND = "#0b1220"  # Цвет фона окна.
TEXT_COLOR = "#e6edf7"  # Цвет основного текста.
PANEL_COLOR = "#141f33"  # Цвет карточек интерфейса.
PANEL_LIGHT = "#1d2b44"  # Цвет кнопок и вторичных элементов.
CAMERA_COLOR = "#070c15"  # Почти чёрный цвет области камеры.
MUTED_COLOR = "#94a3b8"  # Приглушённый цвет поясняющего текста.
ACCENT_COLOR = "#38bdf8"  # Голубой цвет активного состояния.
SUCCESS_COLOR = "#4ade80"  # Зелёный цвет успешной проверки.
DANGER_COLOR = "#fb7185"  # Красный цвет закрытого доступа и ошибки.
CARD_RADIUS = 20  # Радиус скругления карточек customtkinter.

# Две палитры интерфейса. Все цвета собраны здесь, поэтому переключение темы
# меняет оформление сразу и не требует переписывать логику камеры.
THEMES = {
    "dark": {
        "background": "#0b1220",
        "text": "#e6edf7",
        "panel": "#141f33",
        "panel_light": "#1d2b44",
        "camera": "#070c15",
        "muted": "#94a3b8",
        "secondary_text": "#c3cede",
        "accent": "#38bdf8",
        "success": "#4ade80",
        "danger": "#fb7185",
        "border": "#26344c",
        "result": "#1a2940",
        "success_panel": "#12352e",
        "success_preview": "#0b211e",
        "success_icon": "#164337",
        "button_hover": "#67d3fa",
        "secondary_hover": "#2a3c5b",
        "button_text": "#07111f",
    },
    "light": {
        "background": "#eef3f8",
        "text": "#152338",
        "panel": "#ffffff",
        "panel_light": "#e2ebf7",
        "camera": "#d9e3ee",
        "muted": "#5f7087",
        "secondary_text": "#3e526b",
        "accent": "#078bc8",
        "success": "#17804b",
        "danger": "#cf3f58",
        "border": "#cbd8e8",
        "result": "#e6edf7",
        "success_panel": "#dff5e9",
        "success_preview": "#e7f8ee",
        "success_icon": "#c4ecd4",
        "button_hover": "#31afe3",
        "secondary_hover": "#cfdaea",
        "button_text": "#ffffff",
    },
}

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
        self.preview_state = "placeholder"  # placeholder, camera или success.
        self.animation_id = None  # Идентификатор анимации успешной проверки.
        self.loading_id = None  # Идентификатор анимации подключения камеры.
        self.animation_step = 0
        self.loading_step = 0
        self.camera_badge_color_key = "muted"
        self.live_color_key = "muted"
        self.timer_color_key = "text"

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
        self.camera_choice = ctk.CTkOptionMenu(
            camera_header, values=[f"Камера {i}" for i in range(3)],
            command=self.change_camera, width=112, height=30,
            fg_color=self.colors["panel_light"], button_color=self.colors["panel_light"],
            button_hover_color=self.colors["secondary_hover"], text_color=self.colors["text"],
            font=("Arial", 11), corner_radius=9)
        self.camera_choice.set(f"Камера {CAMERA_INDEX}")
        self.camera_choice.pack(side="right")
        self.live_label = ctk.CTkLabel(camera_header, text="●  ОЖИДАНИЕ",
                                       text_color=self.colors["muted"], font=("Arial", 10, "bold"))
        self.live_label.pack(side="right", padx=14)

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
        self.placeholder_title = ctk.CTkLabel(
            self.placeholder, text="Подключение камеры", text_color=self.colors["text"],
            font=("Arial", 20, "bold"), wraplength=360)
        self.placeholder_title.pack()
        self.placeholder_hint = ctk.CTkLabel(
            self.placeholder, text="Изображение появится здесь", wraplength=360,
            justify="center", font=("Arial", 12), text_color=self.colors["muted"])
        self.placeholder_hint.pack(pady=(10, 0))
        self.video_box.bind("<Configure>", self.resize_preview)
        self.video_hint = ctk.CTkLabel(video_card, text="Одна рука в кадре  ·  Хорошее освещение",
                                       text_color=self.colors["muted"], font=("Arial", 11))
        self.video_hint.grid(row=2, column=0, pady=(8, 12))

        self.panel = ctk.CTkFrame(content, width=340, fg_color=self.colors["panel"],
                                  bg_color=self.colors["background"], corner_radius=CARD_RADIUS,
                                  border_width=1, border_color=self.colors["border"])
        self.panel.grid(row=0, column=1, sticky="nsew")
        self.panel.grid_propagate(False)
        self.panel.grid_columnconfigure(0, weight=1)
        self.panel.grid_rowconfigure(0, weight=1)
        # При низком окне прокручивается задание. Кнопки вынесены ниже и не исчезают.
        self.details = ctk.CTkScrollableFrame(
            self.panel, fg_color=self.colors["panel"], corner_radius=0,
            scrollbar_button_color=self.colors["panel"], scrollbar_button_hover_color=self.colors["panel_light"])
        details = self.details
        details.grid(row=0, column=0, sticky="nsew", padx=(18, 10), pady=(18, 0))
        task_header = ctk.CTkFrame(details, fg_color="transparent")
        task_header.pack(fill="x", pady=(0, 12))
        self.task_section_label = ctk.CTkLabel(task_header, text="ВАШЕ ЗАДАНИЕ", font=("Arial", 11, "bold"),
                                               text_color=self.colors["accent"])
        self.task_section_label.pack(side="left")
        self.timer = ctk.CTkLabel(task_header, text="—", width=62, height=28,
                                  fg_color=self.colors["panel_light"], corner_radius=8,
                                  text_color=self.colors["text"], font=("Arial", 12, "bold"))
        self.timer.pack(side="right")
        self.task_label = ctk.CTkLabel(
            details, text="Подготовка задания", wraplength=282, justify="left",
            anchor="w", text_color=self.colors["text"], font=("Arial", 25, "bold"))
        self.task_label.pack(fill="x", pady=(0, 10))
        self.hint = ctk.CTkLabel(
            details, text="", wraplength=282, justify="left", anchor="w",
            text_color=self.colors["secondary_text"], font=("Arial", 13))
        self.hint.pack(fill="x")

        self.guide = ctk.CTkFrame(details, fg_color=self.colors["panel_light"], corner_radius=12)
        self.guide.pack(fill="x", pady=(18, 18))
        self.guide_title = ctk.CTkLabel(self.guide, text="КАК ПРОЙТИ ПРОВЕРКУ", font=("Arial", 10, "bold"),
                                        text_color=self.colors["accent"])
        self.guide_title.pack(anchor="w", padx=14, pady=(10, 2))
        self.guide_text = ctk.CTkLabel(
            self.guide, text=f"Покажите кисть целиком, пальцами вверх. Удерживайте жест {HOLD_SECONDS:g} с.",
            wraplength=248, justify="left", anchor="w",
            text_color=self.colors["secondary_text"], font=("Arial", 12))
        self.guide_text.pack(fill="x", padx=14, pady=(0, 12))
        self.detected = ctk.CTkLabel(
            details, text="Ожидание камеры", wraplength=282, anchor="w",
            text_color=self.colors["text"], font=("Arial", 12))
        self.detected.pack(fill="x", pady=(0, 8))
        progress_row = ctk.CTkFrame(details, fg_color="transparent")
        progress_row.pack(fill="x")
        self.progress_caption = ctk.CTkLabel(progress_row, text="Удержание жеста", text_color=self.colors["muted"],
                                              font=("Arial", 11))
        self.progress_caption.pack(side="left")
        self.hold_label = ctk.CTkLabel(progress_row, text=f"0.0 / {HOLD_SECONDS:g} с",
                                       text_color=self.colors["muted"], font=("Arial", 11))
        self.hold_label.pack(side="right")
        self.progress = ctk.CTkProgressBar(details, height=8, corner_radius=4,
                                           fg_color=self.colors["border"], progress_color=self.colors["accent"])
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(4, 18))

        self.result_box = ctk.CTkFrame(details, fg_color=self.colors["result"], corner_radius=12)
        self.result_box.pack(fill="x", pady=(0, 4))
        self.status = ctk.CTkLabel(
            self.result_box, text="Доступ закрыт", wraplength=248,
            justify="left", anchor="w", text_color=self.colors["muted"], font=("Arial", 21, "bold"))
        self.status.pack(fill="x", padx=14, pady=(12, 2))
        self.result_hint = ctk.CTkLabel(
            self.result_box, text="Подготавливаем проверку", wraplength=248,
            justify="left", anchor="w", text_color=self.colors["muted"], font=("Arial", 12))
        self.result_hint.pack(fill="x", padx=14, pady=(0, 14))

        buttons = ctk.CTkFrame(self.panel, fg_color="transparent")
        buttons.grid(row=1, column=0, sticky="ew", padx=20, pady=(14, 16))
        self.new_button = ctk.CTkButton(
            buttons, text="Новое задание", command=self.new_challenge,
            height=44, corner_radius=12, fg_color=self.colors["accent"],
            hover_color=self.colors["button_hover"], text_color=self.colors["button_text"],
            font=("Arial", 13, "bold"))
        self.new_button.pack(fill="x")
        self.exit_button = ctk.CTkButton(
            buttons, text="Выйти", command=self.close, height=32, corner_radius=10,
            fg_color="transparent", hover_color=self.colors["secondary_hover"],
            text_color=self.colors["muted"], font=("Arial", 12))
        self.exit_button.pack(fill="x", pady=(6, 0))
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
        self.video_hint.configure(text_color=c["muted"])
        self.camera_choice.configure(
            fg_color=c["panel_light"], button_color=c["panel_light"],
            button_hover_color=c["secondary_hover"], text_color=c["text"])
        self.live_label.configure(text_color=c[self.live_color_key])
        self.video_box.configure(
            fg_color=c["success_preview"] if self.preview_state == "success" else c["camera"])
        self.placeholder_icon.configure(
            text_color=c["success"] if self.preview_state == "success" else c["accent"],
            fg_color=c["success_icon"] if self.preview_state == "success" else "transparent")
        self.placeholder_title.configure(
            text_color=c["success"] if self.preview_state == "success" else c["text"])
        self.placeholder_hint.configure(text_color=c["muted"])
        self.panel.configure(
            fg_color=c["panel"], bg_color=c["background"], border_color=c["border"])
        self.details.configure(
            fg_color=c["panel"], bg_color=c["panel"],
            scrollbar_button_color=c["panel"], scrollbar_button_hover_color=c["panel_light"])
        self.task_section_label.configure(text_color=c["accent"])
        self.timer.configure(fg_color=c["panel_light"], text_color=c[self.timer_color_key])
        self.task_label.configure(text_color=c["text"])
        self.hint.configure(text_color=c["secondary_text"])
        self.guide.configure(fg_color=c["panel_light"])
        self.guide_title.configure(text_color=c["accent"])
        self.guide_text.configure(text_color=c["secondary_text"])
        self.detected.configure(text_color=c["text"])
        self.progress_caption.configure(text_color=c["muted"])
        self.hold_label.configure(text_color=c["muted"])
        self.progress.configure(fg_color=c["border"], progress_color=c["accent"])
        self.result_box.configure(
            fg_color=c["success_panel"] if self.status_color_key == "success" else c["result"])
        self.status.configure(text_color=c[self.status_color_key])
        self.result_hint.configure(text_color=c["muted"])
        self.new_button.configure(
            fg_color=c["accent"], hover_color=c["button_hover"], text_color=c["button_text"])
        self.exit_button.configure(hover_color=c["secondary_hover"], text_color=c["muted"])
        self.footer_label.configure(text_color=c["muted"])

    def stop_animations(self):
        """Отменяет запланированные callbacks, чтобы они не работали после смены экрана."""
        for attribute in ("animation_id", "loading_id"):
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
        held = min(max(held, 0), HOLD_SECONDS)
        self.progress.set(held / HOLD_SECONDS)
        self.hold_label.configure(text=f"{held:.1f} / {HOLD_SECONDS:g} с")

    def set_status(self, text, color, hint):
        """В CustomTkinter нужны configure и text_color; config и fg не подходят."""
        # Запоминаем смысл цвета, чтобы текущий статус правильно перекрашивался
        # при переключении темы даже посреди проверки.
        color_keys = {
            "success": (self.colors["success"], SUCCESS_COLOR),
            "danger": (self.colors["danger"], DANGER_COLOR),
            "accent": (self.colors["accent"], ACCENT_COLOR),
            "muted": (self.colors["muted"], MUTED_COLOR),
        }
        self.status_color_key = next(
            (key for key, values in color_keys.items() if color in values), "muted")
        self.status.configure(text=text, text_color=color)
        self.result_hint.configure(text=hint)
        self.result_box.configure(
            fg_color=self.colors["success_panel"] if self.status_color_key == "success" else self.colors["result"])

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

    def show_placeholder(self, title, hint, success=False, loading=False):
        """Заменяет кадр фоном: после успеха показывает зелёную галочку."""
        self.stop_animations()
        self.last_picture = None
        self.preview_state = "success" if success else "placeholder"
        # grid_forget также убирает сохранённое размещение CustomTkinter:
        # скрытый элемент не появится сам при изменении масштаба экрана.
        self.video.grid_forget()
        self.video.configure(image=self.empty_image)  # Заменяем кадр пустым пикселем.
        self.preview_image = None  # Освобождаем сохранённый кадр и его масштабированные копии.
        # Фон рисуется обычными виджетами: отдельная картинка для запуска не нужна.
        self.video_box.configure(
            fg_color=self.colors["success_preview"] if success else self.colors["camera"])
        self.placeholder_icon.configure(
            text="✓" if success else "◉",
            text_color=self.colors["success"] if success else self.colors["accent"],
            fg_color=self.colors["success_icon"] if success else "transparent")
        self.placeholder_title.configure(
            text=title, text_color=self.colors["success"] if success else self.colors["text"])
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
        self.new_button.configure(state="disabled", text="Подключение…")
        self.camera_choice.configure(state="disabled")
        self.set_camera_badge("Подключение камеры", self.colors["accent"])
        choices = [name for name in GESTURES if name != self.target]
        self.target = secrets.choice(choices)
        self.task_label.configure(text=GESTURES[self.target][0])
        self.hint.configure(text=GESTURES[self.target][1])
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
            self.new_button.configure(state="normal", text="Новое задание")
            self.camera_choice.configure(state="normal")
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
            if len(hands) == 1:
                gesture = recognize_gesture(hands[0].landmark)
                name = GESTURES[gesture][0] if gesture else "Жест не определён"
                self.detected.configure(text="Распознано: " + name)
                mp.solutions.drawing_utils.draw_landmarks(
                    rgb, hands[0], mp.solutions.hands.HAND_CONNECTIONS)
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
            self.check_result(gesture, now)
        except Exception as error:
            self.fail(str(error))
            return
        if self.active:
            self.after_id = self.root.after(30, self.update_frame)

    def check_result(self, gesture, now):
        """Доступ открывается только при непрерывном совпадении до конца таймера."""
        if not self.active:
            return
        remaining = TIME_LIMIT - (now - self.started_at)
        self.timer_color_key = "danger" if remaining <= 5 else "text"
        self.timer.configure(text=f"{max(0, remaining):.1f} с",
                             text_color=self.colors[self.timer_color_key])
        if remaining <= 0:
            self.access_granted = False
            self.match_since = None
            self.set_progress(0)
            self.set_status("Время истекло", self.colors["danger"], "Доступ закрыт. Можно попробовать ещё раз.")
            self.stop_camera()
            self.new_button.configure(text="Повторить попытку")
            return
        if self.last_frame_at is not None and now - self.last_frame_at > MAX_FRAME_GAP:
            self.match_since = None  # Пауза в кадрах не считается удержанием.
        self.last_frame_at = now
        if gesture != self.target:
            self.match_since = None
            self.set_progress(0)
            self.set_status("Доступ закрыт", self.colors["muted"], "Покажите нужный жест и удерживайте его")
            return
        if self.match_since is None:
            self.match_since = now
        held = now - self.match_since
        self.set_progress(held)
        self.set_status("Жест совпадает", self.colors["accent"], "Не меняйте положение руки")
        if held >= HOLD_SECONDS:
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
        self.new_button.configure(state="normal", text="Повторить попытку")
        self.camera_choice.configure(state="normal")

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
