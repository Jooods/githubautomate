@echo off
title GitHub Repository Manager
echo Launching GitHub Repository Manager...
python main.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
