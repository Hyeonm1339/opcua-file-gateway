@echo off
REM NSSM을 통해 윈도우 서비스로 실행하기 위한 배치 파일입니다.

REM 스크립트가 있는 디렉토리로 이동합니다.
cd /d "%~dp0"

echo Starting lmfilerecv_new.py...

REM python.exe가 환경변수에 잡혀있지 않은 경우를 대비해 py 런처를 사용합니다.
REM 시스템에 맞게 'python' 또는 파이썬 실행파일의 전체 경로를 사용해도 됩니다.

REM python 스크립트를 실행합니다. Flask 웹서버가 실행됩니다.
py -3 lmfilerecv_new.py
