@echo off
cd /d "%~dp0"
git init
git add .
git commit -m "Initial commit — AquaPredict"
git branch -M main
git remote add origin https://github.com/canvanhung66-droid/aquapredict.git
git push -u origin main
pause
