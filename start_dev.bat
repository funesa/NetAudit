@echo off
echo Starting Backend...
start "NetAudit Backend" python app.py
echo Starting Frontend...
cd frontend
start "NetAudit Frontend" npm run dev
echo System Started!
