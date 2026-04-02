@echo off

echo Installing dependencies...
pip install -r requirements.txt

echo Running app...
python app.py

pause