@echo off
title SR Enterprise Server
echo ========================================================
echo Starting SR Enterprise Server (http://localhost:8000)...
echo ========================================================
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
