@echo off
title MCP Server Starter
cls
echo =======================================================================
echo          MCP SERVER ^& NGROK TUNNEL STARTER FOR NOTION
echo =======================================================================
echo.

:: 1. Check Node.js installation
echo [1/3] Checking Node.js installation...
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js from https://nodejs.org/ and try again.
    pause
    exit /b
)
echo Node.js is detected.
echo.

:: 2. Check ngrok installation
echo [2/3] Checking ngrok installation...
ngrok -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] ngrok is not detected in PATH.
    echo If ngrok is installed via winget, make sure to restart your terminal.
    echo We will still attempt to run it.
    echo.
) else (
    echo ngrok is detected.
    echo.
)

:: 3. Configure folder and port
:: By default, we use the folder where this batch file is located.
set "TARGET_DIR=%~dp0"
:: Strip trailing backslash from TARGET_DIR for cleaner path
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"

set PORT=3000
:: Set your static ngrok domain here (leave empty if you want a random one)
set NGROK_DOMAIN=onion-wildcard-overhang.ngrok-free.dev

echo [3/3] Configuration:
echo   - Target Folder: %TARGET_DIR%
echo   - Port: %PORT%
if not "%NGROK_DOMAIN%"=="" (
    echo   - ngrok Domain: %NGROK_DOMAIN%
) else (
    echo   - ngrok Domain: [Random]
)
echo.
echo Starting MCP Proxy and ngrok in separate windows...
echo.

:: Launch MCP Proxy
start "MCP Proxy Server (Port %PORT%)" cmd /k npx -y mcp-proxy --port %PORT% -- cmd.exe /c npx -y @modelcontextprotocol/server-filesystem "%TARGET_DIR%"

:: Wait a moment before starting ngrok
timeout /t 2 /nobreak >nul

:: Launch ngrok tunnel (with domain if specified)
if not "%NGROK_DOMAIN%"=="" (
    start "ngrok Tunnel (Port %PORT%)" cmd /k "ngrok http %PORT% --domain %NGROK_DOMAIN%"
) else (
    start "ngrok Tunnel (Port %PORT%)" cmd /k "ngrok http %PORT%"
)

echo =======================================================================
echo STATUS: Started!
echo =======================================================================
echo 1. Check the "MCP Proxy Server" window for logs.
echo 2. Check the "ngrok Tunnel" window for the Forwarding URL.
echo    Copy the URL (e.g., https://xxxx-xxxx.ngrok-free.app)
echo 3. In Notion, paste it into "MCP server URL" and append "/sse"
echo    Example: https://xxxx-xxxx.ngrok-free.app/sse
echo.
echo Press any key to exit this starter script (the servers will keep running).
pause >nul
