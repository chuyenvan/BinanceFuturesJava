@echo off
REM CE button-press wrapper: chay nut mcp_tools-v3.py tren Oracle qua SSH, tra JSON.
REM Dung: ce bg_selftest | ce sys_health | ce wfo_status | ce wfo_run /path/ds ... | ce bg_list
REM Sync code moi: ce --sync  (scp mcp_tools-v3.py len Oracle truoc khi chay)
setlocal
set SSH="C:\Program Files\Git\usr\bin\ssh.exe"
set SCP="C:\Program Files\Git\usr\bin\scp.exe"
set KEY=C:\Users\pc\.ssh\id_rsa_chuyennd
set HOST=ubuntu@161.118.212.3
set TOOL=/home/ubuntu/claudedata/.run/mcp_tools-v3.py
set ENVS=CE_RUN_DIR=/home/ubuntu/claudedata/.run/mcp_ce CE_LOCKS_DIR=/home/ubuntu/claudedata/.run/mcp_ce/locks

REM NUT LOCAL: build jar corretto-17 -> scp Oracle -> verify md5. Args: [remote_jar] [host]
REM Goi qua :bd (subroutine) chu KHONG dat trong khoi if(...) — trong khoi, %BD% bi expand luc PARSE
REM truoc khi `set` chay => rong. Subroutine expand binh thuong, khong can enabledelayedexpansion
REM (tranh an dau `!` trong extra_env cua cac nut khac).
if "%1"=="build_deploy" (
  call :bd %2 %3
  exit /b
)

if "%1"=="--sync" (
  %SCP% -o StrictHostKeyChecking=no -i %KEY% "%~dp0mcp_tools-v3.py" %HOST%:%TOOL%
  echo SYNCED
  shift
)
if "%1"=="" (
  %SSH% -o StrictHostKeyChecking=no -i %KEY% %HOST% "%ENVS% python3 %TOOL%" 2>nul
  exit /b
)
%SSH% -o StrictHostKeyChecking=no -i %KEY% %HOST% "%ENVS% python3 %TOOL% %*" 2>nul
endlocal
exit /b

:bd
REM %~dp0 = thu muc chua ce.cmd (co dau \ cuoi). git-bash can dau / -> thay the.
set "BD=%~dp0build_deploy.sh"
set "BD=%BD:\=/%"
"C:\Program Files\Git\bin\bash.exe" -lc "bash '%BD%' %1 %2"
exit /b
