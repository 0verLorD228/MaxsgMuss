@echo off
setlocal
rem Переходим в папку, где лежит этот bat-файл.
cd /d "%~dp0"

rem Используем уже созданное окружение .venv312 или .venv.
if exist ".venv312\Scripts\python.exe" set "PYTHON=.venv312\Scripts\python.exe"
if not defined PYTHON if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

rem Если окружения нет, создаём его через Python Launcher.
if not defined PYTHON (
    echo Создаю виртуальное окружение .venv312...
    py -3.12 -m venv .venv312
    if errorlevel 1 goto error
    set "PYTHON=.venv312\Scripts\python.exe"
)

rem Устанавливаем зависимости без запуска Activate.ps1.
echo Проверяю библиотеки...
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto error

rem Запускаем новую или совместимую старую версию файла.
if exist "MaxsgMuss.py" (
    "%PYTHON%" MaxsgMuss.py
) else (
    "%PYTHON%" camera_captcha.py
)
if errorlevel 1 goto error
goto end

:error
echo.
echo Не удалось запустить программу. Прочитайте сообщение выше.
pause

:end
endlocal
