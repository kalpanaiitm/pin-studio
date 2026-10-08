@echo off
REM Double-click to start Pin Studio
cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run app.py
