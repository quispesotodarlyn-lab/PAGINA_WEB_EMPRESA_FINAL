@echo off
chcp 65001 >nul
echo === Creaciones GMD ===
echo 1) Abre XAMPP y pulsa START en MySQL (debe ponerse verde)
echo 2) Instalando dependencias...
where python >nul 2>nul && (set PY=python) || (set PY=py)
%PY% -m pip install -r requirements.txt
echo 3) Iniciando sistema en http://localhost:5000
start "" http://localhost:5000
%PY% app.py
pause
