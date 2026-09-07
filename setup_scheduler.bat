@echo off
echo Creating scheduled tasks to run Naukri Bot 3 times daily (9:00 AM, 2:00 PM, 7:00 PM)...

schtasks /create /tn "NaukriJobBot_Morning" /tr "\"D:\PythonNokariapp\run_bot.bat\"" /sc daily /st 09:00 /f
schtasks /create /tn "NaukriJobBot_Afternoon" /tr "\"D:\PythonNokariapp\run_bot.bat\"" /sc daily /st 14:00 /f
schtasks /create /tn "NaukriJobBot_Evening" /tr "\"D:\PythonNokariapp\run_bot.bat\"" /sc daily /st 19:00 /f

echo.
echo All 3 tasks registered successfully in Windows Task Scheduler!
pause
