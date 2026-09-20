@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo   ComfyUI-TrucyNodes GitHub 自动推送脚本
echo ==========================================

set REMOTE_URL=https://github.com/gnrsbassoutlook/ComfyUI-TrucyNodes.git

:: 1. 检查是否初始化仓库
if not exist ".git" (
    echo [INFO] 正在初始化 Git 仓库...
    git init
    git branch -M main
    git remote add origin %REMOTE_URL%
)

:: 2. 确保 origin 地址正确
for /f "delims=" %%a in ('git remote get-url origin 2^>nul') do set CURRENT_URL=%%a
if "!CURRENT_URL!"=="" (
    git remote add origin %REMOTE_URL%
) else if not "!CURRENT_URL!"=="%REMOTE_URL%" (
    echo [INFO] 更新 origin 远程地址为: %REMOTE_URL%
    git remote set-url origin %REMOTE_URL%
)

:: 3. 检查是否有卡死的 rebase 状态
if exist ".git\rebase-merge" (
    echo [WARN] 检测到卡死的 Rebase 状态，正在自动恢复...
    git rebase --abort >nul 2>&1
    git checkout main >nul 2>&1
)

:: 4. 确保当前处于 main 分支
git checkout main >nul 2>&1

echo.
echo [STATUS] 当前文件改动状态：
git status -s
set "STATUS_OUT="
for /f "delims=" %%i in ('git status -s') do set STATUS_OUT=%%i

if "!STATUS_OUT!"=="" (
    echo.
    echo [OK] 工作区非常干净，没有文件被改动，无需重复提交。
    echo.
    pause
    exit /b
)

echo.
set "msg="
set /p msg=请输入 Commit 说明 (直接回车默认: Auto update): 
if "!msg!"=="" (
    for /f %%a in ('powershell Get-Date -Format "yyyy-MM-dd HH:mm:ss"') do set msg=Auto update: %%a
)

echo.
echo [INFO] 正在提交并尝试推送到 GitHub...
git add .
git commit -m "!msg!"

git push origin main
if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] 推送成功！代码已同步至 GitHub。
    goto END
)

echo.
echo [WARN] 直接推送被拒绝（远程有更新），正在尝试拉取合并...
git pull origin main --rebase
if %errorlevel% equ 0 (
    echo [INFO] 远程更新拉取成功，正在重新推送...
    git push origin main
    if !errorlevel! equ 0 (
        echo.
        echo [SUCCESS] 推送成功！代码已同步至 GitHub。
        goto END
    )
)

:: 如果 rebase 失败（产生冲突）
echo.
echo [ERROR] 拉取合并产生代码冲突，已自动撤销拉取，避免仓库卡死！
git rebase --abort >nul 2>&1
echo -------------------------------------------------------------
echo 提示：如果你确认本地调好的代码就是最新的，不需要保留远程差异，
echo 你可以直接在终端运行以下命令强制覆盖远程：
echo     git push -f origin main
echo -------------------------------------------------------------

:END
echo.
pause