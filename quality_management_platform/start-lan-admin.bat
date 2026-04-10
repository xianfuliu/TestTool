@echo off
set SCRIPT_DIR=%~dp0
powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File ""%SCRIPT_DIR%start-lan.ps1""'"
