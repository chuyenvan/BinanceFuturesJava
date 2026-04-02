@echo off
set GEMINI_API_KEY=AIzaSyBJOoehhIAoADGdEaXZHMqXIDWsCabDyBw
python -m aider --model gemini/gemini-2.5-flash --chat-language vietnamese --no-pretty %*
pause