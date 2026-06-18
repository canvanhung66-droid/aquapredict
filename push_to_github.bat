@echo off
cd /d "%~dp0"

REM Khởi tạo git nếu chưa có
if not exist ".git" (
  git init
  git remote add origin https://github.com/canvanhung66-droid/aquapredict.git
)

git add aqua_predict.html
git commit -m "feat: redesign dashboard as main screen"

git add aqua_predict.html
git commit -m "feat: refactor AI prediction as module"

git add aqua_predict.html
git commit -m "feat: improve navigation sidebar and bottom nav"

git add aqua_predict.html
git commit -m "feat: add history page and monitor page"

git add .
git commit -m "feat: complete UI redesign v2"

git branch -M main
git push -u origin main

echo.
echo ✅ Da push len GitHub thanh cong!
echo 🔗 https://github.com/canvanhung66-droid/aquapredict
pause
