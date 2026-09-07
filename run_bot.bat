@echo off
cd /d "D:\PythonNokariapp"
echo [%date% %time%] Starting Naukri Job Application Bot... >> "D:\PythonNokariapp\bot_run.log"
python Jobapply.py >> "D:\PythonNokariapp\bot_run.log" 2>&1
echo [%date% %time%] Bot execution finished. >> "D:\PythonNokariapp\bot_run.log"
