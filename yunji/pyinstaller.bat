@echo off
REM 设置变量
set SCRIPT=editor.py
set ICON=editor.ico
set ADD_DATA="images;images"

REM 执行 PyInstaller 命令
pyinstaller --onefile --noconsole --icon=%ICON% --add-data %ADD_DATA% %SCRIPT%

REM 暂停以便查看输出信息
pause
REM pyinstaller --onefile --noconsole --icon=editor.ico --add-data "images;images" editor.py
