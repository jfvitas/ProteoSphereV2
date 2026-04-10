@echo off
setlocal
cd /d "%~dp0"
python download_all_sources.py --dest "D:/Documents/data" --extract
pause
