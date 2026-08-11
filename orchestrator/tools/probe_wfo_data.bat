@echo off
REM Probe trang thai du lieu WFO tren Oracle qua nut CE (khong raw ssh).
cd /d "%~dp0.."
call ce.cmd bg_run inv_cfg "cat /home/ubuntu/java/simulator/config.properties" 1.0
call ce.cmd bg_run inv_ls "ls -la /home/ubuntu/java/simulator/kaggle_data_hpo" 1.0
call ce.cmd bg_run inv_wfo1m "ls -la /home/ubuntu/claudedata/wfo1m" 1.0
timeout /t 12 /nobreak >nul
echo ===CFG===
call ce.cmd bg_report inv_cfg
echo ===LS_KAGGLEDATA===
call ce.cmd bg_report inv_ls
echo ===LS_WFO1M===
call ce.cmd bg_report inv_wfo1m
